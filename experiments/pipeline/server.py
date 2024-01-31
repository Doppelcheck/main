import asyncio
import dataclasses
import json
import secrets
import string
from dataclasses import dataclass
from typing import Generator, Callable, Sequence, AsyncGenerator
from urllib.parse import urlparse

import httpx
from fastapi import WebSocket, WebSocketDisconnect, Body
from fastapi.staticfiles import StaticFiles
from loguru import logger
from nicegui import ui, app, Client

from fastapi.middleware.cors import CORSMiddleware
from nicegui.observables import ObservableDict
from openai.types.chat import ChatCompletionChunk
from playwright.async_api import async_playwright, BrowserContext
from playwright._impl._errors import Error as PlaywrightError
from pydantic import BaseModel

from experiments.pipeline.prompts.agent_patterns import extraction, google
from experiments.pipeline.tools.prompt_openai_chunks import PromptOpenAI
from experiments.pipeline.tools.text_processing import (
    text_node_generator, get_text_lines, pipe_codeblock_content, CodeBlockSegment, get_range
)
from src.agents.retrieval import AgentRetrieval
from src.tools.bookmarklet import compile_bookmarklet
from src.tools.misc import extract_code_block

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


class ReceiveGoogleResultsException(Exception):
    pass


class RetrieveDocumentException(Exception):
    pass


class User(BaseModel):
    user_id: str


@dataclass
class MessageSegment:
    segment: str
    last_segment: bool
    last_message: bool


@dataclass
class ClaimSegment(MessageSegment):
    claim_id: int
    purpose: str = "extract"
    highlight: str | None = None


@dataclass
class DocumentSegment(MessageSegment):
    claim_id: int
    document_id: int
    document_uri: str
    purpose: str = "retrieve"


@dataclass
class ComparisonSegment(MessageSegment):
    purpose: str = "compare"


@dataclass
class Doc:
    claim_id: int
    uri: str
    content: str | None


class Server:
    @staticmethod
    async def _retrieve_text(claim_id: int, context: BrowserContext, url: str) -> Doc:
        page = await context.new_page()
        try:
            await page.goto(url)
        except PlaywrightError as e:
            return Doc(claim_id=claim_id, uri=url, content=None)

        html = await page.content()
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_load_state("networkidle")
        full_text_lines = "".join(text_node_generator(html))
        return Doc(claim_id=claim_id, uri=url, content=full_text_lines)

    @staticmethod
    async def _get_address(client: Client) -> str:
        await client.connected()
        js_url = await ui.run_javascript('window.location.href')
        parsed_url = urlparse(js_url)
        return parsed_url.netloc

    @staticmethod
    async def _stream_claims_to_browser(
            response: AsyncGenerator[ChatCompletionChunk, None], text_lines: Sequence[str], num_claims: int
    ) -> Generator[ClaimSegment, None, None]:

        claim_count = 0
        last_message_segment: CodeBlockSegment | None = None
        in_num_range = True
        num_range_str = ""
        async for each_segment in pipe_codeblock_content(response, lambda chunk: chunk.choices[0].delta.content):
            if in_num_range:
                if each_segment.segment in string.digits + "-" + ":":
                    num_range_str += each_segment.segment
                else:
                    try:
                        line_range = get_range(num_range_str)
                    except ValueError as e:
                        logger.warning(f"failed to parse {num_range_str}: {e}")
                        in_num_range = False
                        continue

                    highlight_text = "".join(text_lines[line_range[0] - 1:line_range[1] - 1])
                    yield ClaimSegment("", False, False, claim_count, highlight=highlight_text)
                    in_num_range = False

                continue

            last_segment = each_segment.segment == "\n"
            last_claim = claim_count >= num_claims
            if last_message_segment is not None:
                if last_segment:
                    yield ClaimSegment(last_message_segment.segment, True, last_claim, claim_count)
                    num_range_str = ""
                    in_num_range = True
                else:
                    yield ClaimSegment(last_message_segment.segment, False, last_claim, claim_count)

            claim_count += int(last_segment)

            last_message_segment = each_segment
        # last_message_segment contains only \n, can be ignored

    def __init__(self, agent_config: dict[str, any], google_config: dict[str, any]) -> None:
        self.llm_interface = PromptOpenAI(agent_config)
        self.google_config = google_config

    async def get_claims_from_selection(self, text: str) -> Generator[ClaimSegment, None, None]:
        pass

    async def reference_stream_from_llm(self, websocket: WebSocket, data: str, purpose: str) -> None:
        response = self.llm_interface.stream_reply_to_prompt(data)
        async for each_chunk_dict in response:
            each_dict = {'purpose': purpose, 'data': each_chunk_dict}
            json_str = json.dumps(each_dict)
            await websocket.send_text(json_str)

    async def get_claims_dummy(self, body_html: str) -> Generator[ClaimSegment, None, None]:
        for i in range(5):
            text = f"Claim {i}, ({len(body_html)})"
            last_claim = i >= 4
            for j, each_character in enumerate(text):
                await asyncio.sleep(.1)
                last_segment = j >= len(text) - 1
                message_segment = ClaimSegment(each_character, last_segment, last_claim, i)
                yield message_segment

    async def get_claims_from_html(self, body_html: str) -> Generator[ClaimSegment, None, None]:
        node_generator = text_node_generator(body_html)
        text_lines = list(get_text_lines(node_generator, line_length=20))
        num_claims = 3
        prompt = extraction(text_lines, num_claims=num_claims)
        response = self.llm_interface.stream_reply_to_prompt(prompt)

        async for each_segment in Server._stream_claims_to_browser(response, text_lines, num_claims):
            yield each_segment

    async def _get_urls_from_google_query(self, search_query: str) -> tuple[str, ...]:
        url = "https://www.googleapis.com/customsearch/v1"
        # https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list#response
        params = {
            "q": search_query,
            "key": self.google_config["custom_search_api_key"],
            "cx": self.google_config["custom_search_engine_id"],
        }

        #async with httpx.AsyncClient() as httpx_session:
        #    response = await httpx_session.get(url, params=params)

        response = httpx.get(url, params=params)

        if response.status_code != 200:
            raise ReceiveGoogleResultsException(
                f"Request failed with status code {response.status_code}: {response.text}"
            )

        # https://developers.google.com/custom-search/v1/reference/rest/v1/Search
        result = response.json()

        items = result.get("items")
        if items is None:
            raise ReceiveGoogleResultsException(
                f"Google did not return results for {search_query}"
            )

        # https://developers.google.com/custom-search/v1/reference/rest/v1/Search#Result
        return tuple(each_item['link'] for each_item in items)

    async def get_documents_dummy(self, claim_id: int, claim_text: str) -> Generator[DocumentSegment, None, None]:
        # retrieve documents from claim_text
        for i in range(5):
            text = f"Document {i}, (id {claim_id})"
            last_document = i >= 4
            await asyncio.sleep(.1)
            yield DocumentSegment(text, True, last_document, claim_id, i, f"url {i}")

    async def get_documents(self, claim_id: int, claim_text: str) -> Generator[DocumentSegment, None, None]:
        prompt = google(claim_text)
        response = await self.llm_interface.reply_to_prompt(prompt)
        query = extract_code_block(response, "query")
        uris = await self._get_urls_from_google_query(query)
        logger.info(uris)
        if len(uris) < 1:
            raise logger.warning(f"no uris found for {query}")

        async with async_playwright() as driver:
            browser = await driver.firefox.launch(headless=False)
            context = await browser.new_context()
            tasks = [asyncio.create_task(Server._retrieve_text(claim_id, context, each_url)) for each_url in uris]
            for document_id, task in enumerate(asyncio.as_completed(tasks)):
                each_doc: Doc = await task
                last_document = document_id >= len(uris) - 1
                document = DocumentSegment(each_doc.content, True, last_document, claim_id, document_id, each_doc.uri)
                yield document

            await asyncio.sleep(1)
            await context.close()
            await browser.close()

    async def get_comparisons_dummy(self, claim_id: int, claim: str, document_uri: str) -> Generator[ComparisonSegment, None, None]:
        for i in range(5):
            text = f"Comparison {i}, ({document_uri} vs {claim_id})"
            last_comparison = i >= 4
            for j, each_character in enumerate(text):
                await asyncio.sleep(.1)
                last_segment = j >= len(text) - 1
                message_segment = ComparisonSegment(each_character, last_segment, last_comparison)
                yield message_segment

    def setup_routes(self) -> None:
        claims = list[str]()

        @app.post("/get_config/")
        async def get_config(user_data: User = Body(...)) -> dict:
            settings: ObservableDict = app.storage.general.get(user_data.user_id)
            if settings is None:
                print(f"getting settings for {user_data.user_id}: No settings")
                return dict()

            print(f"getting settings for {user_data.user_id}: {settings}")
            return {key: value for key, value in settings.items()}

        @ui.page("/config/{userid}")
        async def config(userid: str):
            timer: ui.timer | None = None

            def update_timer(callback: Callable[..., any]) -> None:
                nonlocal timer
                if timer is not None:
                    timer.cancel()
                    del timer
                timer = ui.timer(interval=1.0, active=True, once=True, callback=callback)

            def delayed_set_storage(key: str, value: any) -> None:
                text_input.classes(add="bg-warning ")

                async def set_storage() -> None:
                    settings = app.storage.general.get(userid)
                    if settings is None:
                        settings = {key: value}
                        app.storage.general[userid] = settings
                    else:
                        settings[key] = value
                    print(f"setting settings for {userid}: {app.storage.general.get(userid)}")
                    text_input.classes(remove="bg-warning ")

                update_timer(set_storage)

            # interfaces
            #   agents
            #   data sources
            # function
            #   language
            #   extraction
            #       which agent interface?
            #       how many claims?
            #   retrieval
            #       which data source?
            #       how many documents?
            #       score explanation
            #   comparison
            #       which agent interface?
            #       range of match

            # individual setting
            key_name = "testkey"
            label = "label"
            placeholder = "placeholder"
            # last_value = await Server.get_iframe_message(client, key_name)
            last_value = ""
            with ui.input(
                    label=label,
                    placeholder=placeholder,
                    value=last_value,
                    on_change=lambda event: delayed_set_storage(key_name, event.value),
            ) as text_input:
                text_input.classes(add="transition ease-out duration-500 ")
                text_input.classes(remove="bg-warning ")

        @ui.page("/")
        async def bookmarklet(client: Client) -> None:
            address = await Server._get_address(client)

            with open("static/bookmarklet.js") as file:
                bookmarklet_js = file.read()

            bookmarklet_js = bookmarklet_js.replace("localhost:8000", address)

            secret = secrets.token_urlsafe(32)
            bookmarklet_js = bookmarklet_js.replace("[unique user identification]", secret)

            compiled_bookmarklet = compile_bookmarklet(bookmarklet_js)
            ui.link("test bookmarklet", target=compiled_bookmarklet)

        @app.websocket("/talk")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            try:
                message_str = await websocket.receive_text()
                message = json.loads(message_str)
                purpose = message['purpose']
                data = message['data']

                match purpose:
                    case "ping":
                        answer = {"purpose": "pong", "data": "pong"}
                        json_str = json.dumps(answer)
                        await websocket.send_text(json_str)

                    case "extract":
                        async for segment in self.get_claims_from_html(data):
                        # async for segment in self.get_claims_dummy(data):
                            each_dict = dataclasses.asdict(segment)
                            json_str = json.dumps(each_dict)
                            await websocket.send_text(json_str)

                    case "retrieve":
                        claim_id = data['id']
                        claim_text = data['text']
                        # async for segment in self.get_documents_dummy(claim_id, claim_text):
                        async for segment in self.get_documents(claim_id, claim_text):
                            each_dict = dataclasses.asdict(segment)
                            json_str = json.dumps(each_dict)
                            await websocket.send_text(json_str)

                    case "compare":
                        claim_id = data['claim_id']
                        claim_text = data['claim_text']
                        document_uri = data['document_id']
                        async for segment in self.get_comparisons_dummy(claim_id, claim_text, document_uri):
                            each_dict = dataclasses.asdict(segment)
                            json_str = json.dumps(each_dict)
                            await websocket.send_text(json_str)

                    case _:
                        message_segment = MessageSegment(f"unknown purpose {purpose}, len {len(data)}", True, True)
                        each_dict = dataclasses.asdict(message_segment)
                        json_str = json.dumps(each_dict)
                        await websocket.send_text(json_str)

                # await self.stream_from_llm(websocket, data, purpose)

            except WebSocketDisconnect as e:
                print(e)


app.mount("/static", StaticFiles(directory="static"), name="static")


def main() -> None:
    with open("config.json") as file:
        config = json.load(file)

    nicegui_config = config.pop("nicegui")

    server = Server(config["agent_interface"], config["google"])
    server.setup_routes()

    ui.run(**nicegui_config)


if __name__ in {"__main__", "__mp_main__"}:
    main()

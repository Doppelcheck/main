import asyncio
import dataclasses
import json
import secrets
import string
from dataclasses import dataclass
from typing import Generator, Sequence, AsyncGenerator
from urllib.parse import urlparse

import httpx
from fastapi import WebSocket, WebSocketDisconnect, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from loguru import logger
from nicegui import ui, app, Client

from fastapi.middleware.cors import CORSMiddleware
from nicegui.element import Element
from openai.types.chat import ChatCompletionChunk
from playwright.async_api import async_playwright, BrowserContext
from playwright._impl._errors import TimeoutError, Error as PlaywrightError
from pydantic import BaseModel

from prompts.agent_patterns import extraction, google
from tools import bypass
from tools.prompt_openai_chunks import PromptOpenAI
from tools.text_processing import text_node_generator, CodeBlockSegment, pipe_codeblock_content, get_range, \
    get_text_lines, extract_code_block, compile_bookmarklet
from tools.configuration import delayed_storage, get_config_dict, update_llm_config, update_data_config

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
    success: bool = True
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

        claim_count = 1
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
            logger.info(f"claims: {claim_count} >= {num_claims}, last_claim {last_claim}, last_segment {last_segment}, claim_count {claim_count}")
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

    @staticmethod
    def _install_section(userid: str, address: str, video: bool = True) -> None:
        with open("static/bookmarklet.js") as file:
            bookmarklet_js = file.read()

        bookmarklet_js = bookmarklet_js.replace("[localhost:8000]", address)
        bookmarklet_js = bookmarklet_js.replace("[unique user identification]", userid)

        compiled_bookmarklet = compile_bookmarklet(bookmarklet_js)
        # todo:
        #   see max width here: https://tailwindcss.com/docs/max-width

        logo = ui.image("static/images/logo_big.svg")
        logo.classes(add="w-full")
        with ui.element("div") as spacer:
            spacer.classes(add="h-16")
        link_html = (
            f'Drag this <a href="{compiled_bookmarklet}" class="bg-blue-500 hover:bg-blue-700 text-white '
            f'font-bold py-2 px-4 mx-2 rounded inline-block" onclick="return false;">Doppelcheck</a> to your '
            f'bookmarks to use it on any website.'
        )
        with ui.html(link_html) as bookmarklet_text:
            bookmarklet_text.classes(add="text-center")

        if video:
            with ui.element("div") as spacer:
                spacer.classes(add="h-8")

            with ui.video(
                    "static/videos/installation.webm",
                    autoplay=True, loop=True, muted=True, controls=False) as video:
                video.classes(add="w-full max-w-2xl m-auto")

    def __init__(self, agent_config: dict[str, any], google_config: dict[str, any]) -> None:
        self.llm_interface = PromptOpenAI(agent_config)
        self.google_config = google_config
        self.browser = None
        self.playwright = None
        self.httpx_session = httpx.AsyncClient()

    async def start_browser(self) -> None:
        if self.playwright is None:
            self.playwright = await async_playwright().start()
        if self.browser is None:
            self.browser = await self.playwright.firefox.launch(headless=True)
            # self.browser = await self.playwright.firefox.launch(headless=False)

    async def stop_browser(self) -> None:
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

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

    async def get_claims_from_html(self, body_html: str, user_id: str) -> Generator[ClaimSegment, None, None]:
        settings = get_config_dict(user_id)
        claim_count = settings["claim_count"]

        node_generator = text_node_generator(body_html)
        text_lines = list(get_text_lines(node_generator, line_length=20))
        prompt = extraction(text_lines, num_claims=claim_count)
        response = self.llm_interface.stream_reply_to_prompt(prompt)

        async for each_segment in Server._stream_claims_to_browser(response, text_lines, claim_count):
            yield each_segment

    async def _get_urls_from_google_query(self, search_query: str) -> tuple[str, ...]:
        url = "https://www.googleapis.com/customsearch/v1"
        # https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list#response
        # todo: use llm to craft parameter dict
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
            return tuple()
            # raise ReceiveGoogleResultsException(f"Google did not return results for {search_query}")

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
            yield DocumentSegment("No documents found", True, True, claim_id, 0, "No documents found", success=False)
            return

        for document_id, each_uri in enumerate(uris):
            last_document = document_id >= len(uris) - 1
            try:
                content = await bypass.bypass_paywall_session(each_uri, self.httpx_session)
                yield DocumentSegment(content, True, last_document, claim_id, document_id, each_uri)
            except httpx.HTTPError as e:
                yield DocumentSegment(str(e), True, last_document, claim_id, document_id, each_uri, success=False)

    async def get_documents_old(self, claim_id: int, claim_text: str) -> Generator[DocumentSegment, None, None]:
        prompt = google(claim_text)
        response = await self.llm_interface.reply_to_prompt(prompt)
        query = extract_code_block(response, "query")
        uris = await self._get_urls_from_google_query(query)
        logger.info(uris)

        if len(uris) < 1:
            yield DocumentSegment("No documents found", True, True, claim_id, 0, "[no document found]", success=False)
            return

        await self.start_browser()
        context = await self.browser.new_context()
        tasks = [asyncio.create_task(self._retrieve_text(claim_id, context, each_url)) for each_url in uris]

        for document_id, task in enumerate(asyncio.as_completed(tasks)):
            last_document = document_id >= len(uris) - 1

            try:
                each_doc: Doc = await task
                document = DocumentSegment(each_doc.content, True, last_document, claim_id, document_id, each_doc.uri)
                yield document

            except TimeoutError as e:
                logger.warning(f"timeout for {uris[document_id]}: {e}")
                yield DocumentSegment("[timeout]", True, last_document, claim_id, document_id, uris[document_id], success=False)

        # await asyncio.sleep(1)
        # await context.close()

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
        @app.get("/get_content/")
        async def get_content(url: str) -> HTMLResponse:
            html_content = bypass.bypass_paywall_session(url, self.httpx_session)
            return HTMLResponse(html_content)

        @app.post("/get_config/")
        async def get_config(user_data: User = Body(...)) -> dict:
            logger.info(f"getting settings for {user_data.user_id}")
            settings = get_config_dict(user_data.user_id)
            return settings

        @ui.page("/config/{userid}")
        async def config(userid: str, client: Client) -> None:
            settings = get_config_dict(userid)
            address = await Server._get_address(client)

            with ui.element("div") as container:
                container.classes(add="w-full max-w-2xl m-auto")

                Server._install_section(userid, address, video=False)

                with ui.label("Configuration") as heading:
                    heading.classes(add="text-2xl font-bold mt-16")

                with delayed_storage(
                    userid, ui.input, "name_instance",
                    label="Name", placeholder="name for instance"
                ) as text_input:
                    pass

                with delayed_storage(
                    userid, ui.number, "claim_count",
                    label="Claim Count", placeholder="number of claims",
                    min=1, max=5, step=1, precision=0, format="%d"
                ) as number_input:
                    pass

                with ui.label("LLM Interface") as heading:
                    heading.classes(add="text-2xl font-bold mt-16")
                with ui.select(
                    options=["OpenAI", "Mistral", "Anthropic", "ollama"],
                    on_change=lambda event: update_llm_config(userid, llm_config, event.value)
                ) as llm_select:
                    pass
                with ui.element("div") as llm_config:
                    pass
                llm_select.set_value("OpenAI")
                llm_select.disable()

                with ui.label("Data Source") as heading:
                    heading.classes(add="text-2xl font-bold mt-16")
                with ui.select(
                    options=["Google", "Bing", "DuckDuckGo"],
                    on_change=lambda event: update_data_config(userid, data_source_config, event.value)
                ) as data_source_select:
                    pass
                with ui.element("div") as data_source_config:
                    pass
                data_source_select.set_value("Google")
                data_source_select.disable()

        @ui.page("/", dark=True)
        async def main_page(client: Client) -> None:
            address = await Server._get_address(client)

            with ui.element("div") as container:
                container.classes(add="w-full max-w-4xl m-auto")

                logo = ui.image("static/images/logo_big.svg")
                logo.classes(add="w-full")

                ui.element("div").classes(add="h-16")

                ui.label(f"Coming soon to {address}.").classes(add="text-2xl font-bold text-center")

                ui.element("div").classes(add="h-16")

                with ui.video("static/videos/usage.webm", autoplay=True, loop=True, muted=True) as video:
                    video.classes(add="w-full max-w-2xl m-auto")

                ui.element("div").classes(add="h-8")

                ui.link(
                    text="Funded by the Media Tech Lab",
                    target="https://www.media-lab.de/de/media-tech-lab/Doppelcheck",
                    new_tab=True).classes(add="text-center block ")

        @ui.page("/_test")
        async def bookmarklet(client: Client) -> None:
            address = await Server._get_address(client)
            secret = secrets.token_urlsafe(32)

            with ui.element("div") as container:
                container.classes(add="w-full max-w-2xl m-auto")

                Server._install_section(secret, address)

        @app.websocket("/talk")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            try:
                message_str = await websocket.receive_text()
                message = json.loads(message_str)
                purpose = message['purpose']
                data = message['data']
                user_id = message['user_id']

                match purpose:
                    case "ping":
                        answer = {"purpose": "pong", "data": "pong"}
                        json_str = json.dumps(answer)
                        await websocket.send_text(json_str)

                    case "extract":
                        async for segment in self.get_claims_from_html(data, user_id):
                            each_dict = dataclasses.asdict(segment)
                            json_str = json.dumps(each_dict)
                            await websocket.send_text(json_str)

                    case "retrieve":
                        claim_id = data['id']
                        claim_text = data['text']
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

    # asyncio.run(server.stop_browser())


if __name__ in {"__main__", "__mp_main__"}:
    main()

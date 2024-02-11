import asyncio
import dataclasses
import json
import pathlib
import random
import secrets
import string
from dataclasses import dataclass
from typing import Generator, Sequence, AsyncGenerator
from urllib.parse import urlparse, unquote

from playwright._impl._errors import Error as PlaywrightError

import httpx
import lingua
import nltk
from fastapi import WebSocket, WebSocketDisconnect, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from loguru import logger
from nicegui import ui, app, Client

from fastapi.middleware.cors import CORSMiddleware
from openai.types.chat import ChatCompletionChunk
from playwright.async_api import async_playwright, BrowserContext
from pydantic import BaseModel

from _experiments.pw import PlaywrightBrowser
from tools.content_retrieval import bypass_paywall_session, get_context, get_html_content_from_playwright
from prompts.agent_patterns import extraction, google, compare
from tools.data_objects import GoogleCustomSearch, UserConfig
from tools.prompt_openai_chunks import PromptOpenAI
from tools.text_processing import text_node_generator, CodeBlockSegment, pipe_codeblock_content, get_range, \
    get_text_lines, extract_code_block, compile_bookmarklet, shorten_url
from tools.configuration import delayed_storage, update_llm_config, update_data_config, \
    asdict_recusive
from tools.data_access import get_user_config, set_data_value, get_data_value
import uvicorn


VERSION = "0.0.1"


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
    version: str


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
    claim_id: int
    document_id: int
    match_value: int
    purpose: str = "compare"


@dataclass
class Doc:
    claim_id: int
    uri: str
    content: str | None


class Server:
    @staticmethod
    async def _retrieve_text_deprecated(claim_id: int, context: BrowserContext, url: str) -> Doc:
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
            if last_message_segment is not None:
                if last_segment:
                    yield ClaimSegment(last_message_segment.segment, True, last_claim, claim_count)
                    num_range_str = ""
                    in_num_range = True
                else:
                    yield ClaimSegment(last_message_segment.segment, False, last_claim, claim_count)

            claim_count += int(last_segment)
            last_message_segment = each_segment        # last_message_segment contains only \n, can be ignored

    @staticmethod
    async def _stream_matches_to_browser(
            response: AsyncGenerator[ChatCompletionChunk, None], claim_id: int, document_id: int
    ) -> Generator[ComparisonSegment, None, None]:

        last_segment = None

        match_value = 0
        match_value_str = ""
        match_found = False
        async for each_segment in pipe_codeblock_content(response, lambda chunk: chunk.choices[0].delta.content):
            for each_char in each_segment.segment:
                if each_char == "\n":
                    match_found = True
                    match_value = int(match_value_str.strip())

                elif not match_found:
                    match_value_str += each_char

                elif last_segment is not None:
                    yield last_segment

                last_segment = ComparisonSegment(each_char, False, True, claim_id, document_id, match_value)

        last_segment.last_segment = True
        yield last_segment

    @staticmethod
    def _install_section(userid: str, address: str, video: bool = True) -> None:
        with open("static/bookmarklet.js") as file:
            bookmarklet_js = file.read()

        bookmarklet_js = bookmarklet_js.replace("[localhost:8000]", address)
        bookmarklet_js = bookmarklet_js.replace("[unique user identification]", userid)
        bookmarklet_js = bookmarklet_js.replace("[version number]", VERSION)

        compiled_bookmarklet = compile_bookmarklet(bookmarklet_js)
        # todo:
        #   see max width here: https://tailwindcss.com/docs/max-width

        logo = ui.image("static/images/logo_big.svg")
        logo.classes(add="w-full")
        with ui.element("div") as spacer:
            spacer.classes(add="h-16")
        link_html = (
            f'Drag this <a href="{compiled_bookmarklet}" id="doppelcheck-bookmarklet-name" class="bg-blue-500 '
            f'hover:bg-blue-700 text-white font-bold py-2 px-4 mx-2 rounded inline-block" onclick="return false;">'
            f'Doppelcheck</a> to your bookmarks to use it on any website.'
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

    def __init__(self) -> None:
        self.default_openai_key = None
        default_openai_key_file = pathlib.Path("default_openai.json")
        if default_openai_key_file.exists():
            with open(default_openai_key_file) as file:
                default_openai_key = json.load(file)
                self.default_openai_key = default_openai_key.get("openai_key")

        self.default_google_key = None
        self.default_google_id = None
        default_google_key_file = pathlib.Path("default_google.json")
        if default_google_key_file.exists():
            with open(default_google_key_file) as file:
                default_google_key = json.load(file)
                self.default_google_key = default_google_key.get("custom_search_api_key")
                self.default_google_id = default_google_key.get("custom_search_engine_id")

        nltk.download('punkt')
        detector = lingua.LanguageDetectorBuilder.from_all_languages()
        self._detector_built = detector.build()
        self.browser = PlaywrightBrowser()

        # self.httpx_session = httpx.AsyncClient()

    def _get_llm(self, settings: UserConfig) -> PromptOpenAI:
        openai_key = settings.openai_api_key
        if openai_key is None or len(openai_key) < 1:
            openai_key = self.default_openai_key
        parameters = settings.openai_parameters
        llm_interface = PromptOpenAI(openai_key, parameters)
        return llm_interface

    async def _get_uris(self, query: str, settings: UserConfig) -> tuple[str, ...]:
        custom_search = settings.google_custom_search
        if custom_search is None:
            custom_search = GoogleCustomSearch(api_key=self.default_google_key, engine_id=self.default_google_id)
        uris = await self._get_urls_from_google_query(query, custom_search)
        return uris

    def _detect_language(self, text: str) -> str:
        language = self._detector_built.detect_language_of(text)
        if language is None:
            return "en"

        return language.iso_code_639_1.name.lower()

    async def get_claims_from_selection(self, text: str) -> Generator[ClaimSegment, None, None]:
        pass

    async def get_claims_from_html(self, body_html: str, user_id: str) -> Generator[ClaimSegment, None, None]:
        settings = get_user_config(user_id)
        llm_interface = self._get_llm(settings)

        claim_count = settings.claim_count
        language = settings.language

        node_generator = text_node_generator(body_html)
        text_lines = list(get_text_lines(node_generator, line_length=20))
        prompt = extraction(text_lines, num_claims=claim_count, language=language)
        response = llm_interface.stream_reply_to_prompt(prompt)

        async for each_segment in Server._stream_claims_to_browser(response, text_lines, claim_count):
            yield each_segment

    async def _get_urls_from_google_query(
            self, search_query: str, custom_search: GoogleCustomSearch) -> tuple[str, ...]:

        url = "https://www.googleapis.com/customsearch/v1"
        # https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list#response
        # todo: use llm to craft parameter dict

        params = {
            "q": search_query,
            "key": custom_search.api_key,
            "cx": custom_search.engine_id,
        }

        # async with httpx.AsyncClient() as httpx_session:
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

    async def get_documents_deprecated(
            self, user_id: str, claim_id: int, claim_text: str, original_url: str
    ) -> Generator[DocumentSegment, None, None]:
        settings = get_user_config(user_id)
        llm_interface = self._get_llm(settings)

        prompt = google(claim_text)
        response = await llm_interface.reply_to_prompt(prompt)
        query = extract_code_block(response, "query")

        uris = await self._get_uris(query, settings)
        uris = tuple(each_uri for each_uri in uris if each_uri != original_url)

        logger.info(uris)
        if len(uris) < 1:
            raise logger.warning(f"no uris found for {query}")

        async with async_playwright() as driver:
            # browser = await driver.firefox.launch(headless=False)
            browser = await driver.firefox.launch(headless=True)
            context = await browser.new_context()
            tasks = [asyncio.create_task(Server._retrieve_text_deprecated(claim_id, context, each_url)) for each_url in uris]
            for document_id, task in enumerate(asyncio.as_completed(tasks)):
                each_doc: Doc = await task
                last_document = document_id >= len(uris) - 1
                document = DocumentSegment(each_doc.content, True, last_document, claim_id, document_id, each_doc.uri)
                yield document

            await asyncio.sleep(1)
            await context.close()
            await browser.close()

    async def get_documents(
            self, claim_id: int, claim_text: str, user_id: str, original_url: str
    ) -> Generator[DocumentSegment, None, None]:

        settings = get_user_config(user_id)
        llm_interface = self._get_llm(settings)

        context = get_data_value(user_id, ("context", original_url))
        language = settings.language
        prompt = google(claim_text, context=context, language=language)
        response = await llm_interface.reply_to_prompt(prompt)
        query = extract_code_block(response)

        uris = await self._get_uris(query, settings)
        uris = tuple(each_uri for each_uri in uris if each_uri != original_url)
        logger.info(uris)

        if len(uris) < 1:
            yield DocumentSegment("No documents found", True, True, claim_id, 0, "No documents found", success=False)
            return

        for document_id, each_uri in enumerate(uris):
            last_document = document_id >= len(uris) - 1
            content = shorten_url(each_uri)
            yield DocumentSegment(content, True, last_document, claim_id, document_id, each_uri)

    async def get_matches_dummy(
            self, user_id: str, claim_id: int, claim: str, document_id: int, document_uri: str
    ) -> Generator[ComparisonSegment, None, None]:
        """
        ```
        +1
        <explanation>
        ```
        """

        text = f"Comparison: [{document_uri}] vs [{claim_id}]"
        each_match = random.randint(-2, 2)

        for j, each_character in enumerate(text):
            await asyncio.sleep(.1)
            last_segment = j >= len(text) - 1
            message_segment = ComparisonSegment(
                each_character, last_segment, True, claim_id, document_id, each_match
            )
            yield message_segment

    async def get_matches(
            self, user_id: str, claim_id: int, claim: str, document_id: int, document_uri: str
    ) -> Generator[ComparisonSegment, None, None]:
        settings = get_user_config(user_id)
        language = settings.language

        document_html = await get_html_content_from_playwright(document_uri)

        node_generator = text_node_generator(document_html)
        document_text = "".join(node_generator)

        prompt = compare(claim, document_text, language=language)
        llm_interface = self._get_llm(settings)
        response = llm_interface.stream_reply_to_prompt(prompt)

        async for each_segment in Server._stream_matches_to_browser(response, claim_id, document_id):
            yield each_segment

    def setup_routes(self) -> None:
        @app.get("/get_content/")
        async def get_content(url: str) -> HTMLResponse:
            """
            const urlEncoded = encodeURIComponent(originalUrl);
            return `https://${address}/get_content/?url=${urlEncoded}`;
            """
            url_parsed = unquote(url)
            html_content = await bypass_paywall_session(url_parsed)
            return HTMLResponse(html_content)

        @app.post("/get_config/")
        async def get_config(user_data: User = Body(...)) -> dict:
            """
            const configUrl = `https://${address}/get_config/`;
            const userData = { user_id: userId, version: versionClient };
            """
            print(user_data)
            logger.info(f"getting settings for {user_data.user_id}")
            settings = get_user_config(user_data.user_id)
            if user_data.version is None:
                logger.warning(f"client version {user_data.version} does not match server version {VERSION}")
                return {
                    "errorVersionMismatch": "client version does not match server version",
                    "versionServer": VERSION,
                }

            # todo: check if settings are complete, get from system settings if not
            if (
                    settings.google_custom_search is None and
                    self.default_google_key is not None and
                    self.default_google_id is not None):
                settings.google_custom_search = GoogleCustomSearch(
                    api_key=self.default_google_key, engine_id=self.default_google_id)

            if settings.openai_api_key is None and self.default_openai_key is not None:
                settings.openai_api_key = self.default_openai_key

            settings_dict = asdict_recusive(settings)
            settings_dict["versionServer"] = VERSION
            return settings_dict

        @ui.page("/config/{userid}")
        async def config(userid: str, client: Client) -> None:
            """
            configure.href = `https://${address}/config/${userID}`;
            """
            address = await Server._get_address(client)

            default_config = UserConfig()

            with ui.element("div") as container:
                container.classes(add="w-full max-w-2xl m-auto")

                Server._install_section(userid, address, video=False)

                with ui.label("Configuration") as heading:
                    heading.classes(add="text-2xl font-bold mt-16")

                with delayed_storage(
                        userid, ui.input, ("config", "name_instance"),
                        label="Name", placeholder="name for instance", default=default_config.name_instance
                ) as text_input:
                    pass

                with delayed_storage(
                        userid, ui.number, ("config", "claim_count"),
                        label="Claim Count", placeholder="number of claims",
                        min=1, max=5, step=1, precision=0, format="%d", default=default_config.claim_count
                ) as number_input:
                    pass

                with delayed_storage(
                        userid, ui.select, ("config", "language"),
                        label="Language", options=["default", "English", "German", "French", "Spanish"],
                        default=default_config.language
                ) as language_select:
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

            with ui.header() as header:
                header.classes(add="bg-transparent text-white flex justify-end")
                with ui.button("Admin Login") as login_button:
                    # connect to login
                    # https://github.com/zauberzeug/nicegui/blob/main/examples/authentication/main.py
                    pass

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
                user_id = message['user_id']
                original_url = message['url']
                data = message['data']

                match purpose:
                    case "ping":
                        answer = {"purpose": "pong", "data": "pong"}
                        json_str = json.dumps(answer)
                        await websocket.send_text(json_str)

                    case "extract":
                        context = await get_context(original_url, self._detect_language)
                        if context is None:
                            logger.warning(f"no context for {original_url}")
                        else:
                            logger.info(f"context for {original_url}: {context}")
                            set_data_value(user_id, ("context", original_url), context)

                        async for segment in self.get_claims_from_html(data, user_id):
                            each_dict = dataclasses.asdict(segment)
                            json_str = json.dumps(each_dict)
                            await websocket.send_text(json_str)

                    case "retrieve":
                        claim_id = data['id']
                        claim_text = data['text']

                        async for segment in self.get_documents(claim_id, claim_text, user_id, original_url):
                            each_dict = dataclasses.asdict(segment)
                            json_str = json.dumps(each_dict)
                            await websocket.send_text(json_str)

                    case "compare":
                        claim_id = data['claim_id']
                        claim_text = data['claim_text']
                        document_id = data['document_id']
                        document_uri = data['document_uri']
                        async for segment in self.get_matches(
                                user_id, claim_id, claim_text, document_id, document_uri):
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

    server = Server()

    server.setup_routes()
    ui.run(**nicegui_config)

    # todo: use gunicorn or uvicorn instead


if __name__ in {"__main__", "__mp_main__"}:
    main()

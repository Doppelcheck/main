import dataclasses
import json
import secrets
import string
from typing import Generator, Sequence, AsyncGenerator, Coroutine, Iterable
from urllib.parse import urlparse, unquote

import lingua
import nltk
from fastapi import WebSocket, WebSocketDisconnect, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from nicegui import ui, app, Client
from pydantic import BaseModel

from prompts.agent_patterns import extraction, google, compare
from tools.configuration.data.config_objects import ConfigModel
from tools.new_configuration.full import full_configuration
from tools.new_configuration.config_install import get_section
from tools.content_retrieval import get_context
from tools.global_instances import BROWSER_INSTANCE
from tools.data_access import set_data_value, get_data_value
from tools.data_objects import MessageSegment, ClaimSegment, DocumentSegment, ComparisonSegment
from tools.plugins.abstract import InterfaceData, InterfaceLLM
from tools.text_processing import text_node_generator, CodeBlockSegment, pipe_codeblock_content, get_range, \
    get_text_lines, extract_code_block, shorten_url

from starlette.middleware.base import BaseHTTPMiddleware


VERSION = "0.0.9"
PASSWORDS = {'user': 'doppelcheck'}
UNRESTRICTED = {"/", "/config", "/login"}


class AuthMiddleware(BaseHTTPMiddleware):
    """This middleware restricts access to all NiceGUI pages.

    It redirects the user to the login page if they are not authenticated.
    """

    async def dispatch(self, request: Request, call_next):
        if not app.storage.user.get('authenticated', False):
            if request.url.path in Client.page_routes.values() and request.url.path not in UNRESTRICTED:
                app.storage.user['referrer_path'] = request.url.path  # remember where the user wanted to go
                return RedirectResponse('/login')
        return await call_next(request)


app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


class RetrieveDocumentException(Exception):
    pass


class User(BaseModel):
    user_id: str | None
    version: str | None


class Server:
    @staticmethod
    async def _get_address(client: Client) -> str:
        await client.connected()
        js_url = await ui.run_javascript('window.location.href')
        parsed_url = urlparse(js_url)
        return parsed_url.netloc

    @staticmethod
    async def _stream_claims_to_browser(
            response: Coroutine[any, any, AsyncGenerator[str, None]],
            text_lines: Sequence[str],
            num_claims: int
    ) -> Generator[ClaimSegment, None, None]:

        claim_count = 1
        last_message_segment: CodeBlockSegment | None = None
        in_num_range = True
        num_range_str = ""

        async for each_segment in pipe_codeblock_content(response):
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
            response: AsyncGenerator[str, None], claim_id: int, document_id: int
    ) -> Generator[ComparisonSegment, None, None]:

        last_segment = None

        match_value = 0
        match_value_str = ""
        match_found = False
        async for each_segment in pipe_codeblock_content(response):
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
    def get_match_llm_interface(user_id: str) -> InterfaceLLM:
        llm_interface_config = ConfigModel.get_comparison_llm(user_id)
        if llm_interface_config is None:
            logger.error(f"ConfigModel.get_comparison_llm({user_id})")
            raise RetrieveDocumentException(f"ConfigModel.get_comparison_llm({user_id})")
        keywords = llm_interface_config.object_to_state()
        class_ = llm_interface_config.get_interface_class()
        llm_interface: InterfaceLLM = class_.from_state(keywords)
        return llm_interface

    @staticmethod
    def get_match_data_interface(user_id: str) -> InterfaceData:
        data_interface_config = ConfigModel.get_comparison_data(user_id)
        if data_interface_config is None:
            logger.error(f"ConfigModel.get_comparison_data({user_id})")
            raise RetrieveDocumentException(f"ConfigModel.get_comparison_data({user_id})")
        keywords = data_interface_config.object_to_state()
        class_ = data_interface_config.get_interface_class()
        data_interface: InterfaceData = class_.from_state(keywords)
        return data_interface

    @staticmethod
    def get_retrieval_llm_interface(user_id: str) -> InterfaceLLM:
        llm_interface_config = ConfigModel.get_retrieval_llm(user_id)
        if llm_interface_config is None:
            logger.error(f"ConfigModel.get_retrieval_llm({user_id})")
            raise RetrieveDocumentException(f"ConfigModel.get_retrieval_llm({user_id})")
        keywords = llm_interface_config.object_to_state()
        class_ = llm_interface_config.get_interface_class()
        llm_interface: InterfaceLLM = class_.from_state(keywords)
        return llm_interface

    @staticmethod
    def get_retrieval_data_interface(user_id: str) -> InterfaceData:
        data_interface_config = ConfigModel.get_retrieval_data(user_id)
        if data_interface_config is None:
            logger.error(f"ConfigModel.get_retrieval_data({user_id})")
            raise RetrieveDocumentException(f"ConfigModel.get_retrieval_data({user_id})")
        keywords = data_interface_config.object_to_state()
        class_ = data_interface_config.get_interface_class()
        data_interface: InterfaceData = class_.from_state(keywords)
        return data_interface

    def __init__(self) -> None:
        nltk.download('punkt')
        detector = lingua.LanguageDetectorBuilder.from_all_languages()
        self._detector_built = detector.build()

    def _detect_language(self, text: str) -> str:
        language = self._detector_built.detect_language_of(text)
        if language is None:
            return "en"

        return language.iso_code_639_1.name.lower()

    async def get_claims_from_str(self, string_sequence: Iterable[str], user_id: str) -> Generator[ClaimSegment, None, None]:
        llm_interface = await self.get_extraction_llm_interface(user_id)

        claim_count = ConfigModel.get_extraction_claims(user_id)
        language = ConfigModel.get_general_language(user_id)

        text_lines = list(get_text_lines(string_sequence, line_length=20))
        prompt = extraction(text_lines, num_claims=claim_count, language=language)

        response = llm_interface.stream_reply_to_prompt(prompt)
        async for each_segment in Server._stream_claims_to_browser(response, text_lines, claim_count):
            yield each_segment

    async def get_extraction_llm_interface(self, user_id: str) -> InterfaceLLM:
        llm_interface_config = ConfigModel.get_extraction_llm(user_id)
        if llm_interface_config is None:
            logger.error(f"ConfigModel.get_extraction_llm({user_id})")
            raise RetrieveDocumentException(f"ConfigModel.get_extraction_llm({user_id})")
        keywords = llm_interface_config.object_to_state()
        class_ = llm_interface_config.get_interface_class()
        llm_interface: InterfaceLLM = class_.from_state(keywords)
        return llm_interface

    async def get_document_uris(
            self, claim_id: int, claim_text: str, user_id: str, original_url: str
    ) -> AsyncGenerator[DocumentSegment, None]:

        llm_interface = Server.get_retrieval_llm_interface(user_id)
        data_interface = Server.get_retrieval_data_interface(user_id)

        language = ConfigModel.get_general_language(user_id)

        context = get_data_value(user_id, ("context", original_url))
        prompt = google(claim_text, context=context, language=language)

        response = await llm_interface.reply_to_prompt(prompt)
        query = extract_code_block(response)

        doc_count = ConfigModel.get_retrieval_max_documents(user_id)

        # xxx here
        uris = data_interface.get_uris(query, doc_count)
        doc_id = 0
        async for each_uri in uris:
            last_document = doc_id >= doc_count - 1
            content = shorten_url(each_uri.uri_string)
            yield DocumentSegment(content, True, last_document, claim_id, doc_id, each_uri.uri_string)
            doc_id += 1

        # todo: last message does not work
        # todo: google did not find anything does not work

        if doc_id < 1:
            yield DocumentSegment("No documents found", True, True, claim_id, 0, "No documents found", success=False)
            return

    async def get_matches(
            self, user_id: str, claim_id: int, claim: str, document_id: int, original_url: str, document_uri: str
    ) -> Generator[ComparisonSegment, None, None]:

        llm_interface = Server.get_match_llm_interface(user_id)
        data_interface = Server.get_match_data_interface(user_id)

        language = ConfigModel.get_general_language(user_id)

        source = await data_interface.get_document_content(document_uri)
        document_html = source.content

        node_generator = text_node_generator(document_html)
        document_text = "".join(node_generator)

        context = get_data_value(user_id, ("context", original_url))
        prompt = compare(claim, document_text, context=context, language=language)

        response = await llm_interface.stream_reply_to_prompt(prompt)

        async for each_segment in Server._stream_matches_to_browser(response, claim_id, document_id):
            yield each_segment

    async def set_context(self, original_url: str, user_id: str, html_document: str | None = None) -> None:
        context = await get_context(original_url, self._detect_language, html_document)
        if context is None:
            logger.warning(f"no context for {original_url}")
        else:
            logger.info(f"context for {original_url}: {context}")
            set_data_value(user_id, ("context", original_url), context)

    def setup_api_endpoints(self) -> None:
        @app.get("/get_content/")
        async def get_content(url: str) -> HTMLResponse:
            """
            const urlEncoded = encodeURIComponent(originalUrl);
            return `https://${address}/get_content/?url=${urlEncoded}`;
            """
            url_parsed = unquote(url)

            source = await BROWSER_INSTANCE.get_html_content(url_parsed)
            html_content = source.content

            return HTMLResponse(html_content)

        @app.post("/get_config/")
        async def get_config(user_data: User = Body(...)) -> dict:
            """
            const configUrl = `https://${address}/get_config/`;
            const userData = { user_id: userId, version: versionClient };
            """
            logger.info(f"getting settings for {user_data.user_id}")

            # todo: check if config is set up

            if user_data.version != VERSION:
                logger.error(f"client version {user_data.version} does not match server version {VERSION}")
                return {
                    "error": "client version does not match server version",
                    "versionServer": VERSION,
                }

            if user_data.user_id is None:
                logger.error(f"no user_id in {user_data}")
                return {"error": "no user id provided"}

            if (
                    (ConfigModel.get_extraction_llm(user_data.user_id) is None) or
                    (ConfigModel.get_retrieval_llm(user_data.user_id) is None) or
                    (ConfigModel.get_retrieval_data(user_data.user_id) is None) or
                    (ConfigModel.get_comparison_llm(user_data.user_id) is None) or
                    (ConfigModel.get_comparison_data(user_data.user_id) is None)
            ):
                logger.error(f"no interface for {user_data.user_id}")
                return {"error": "missing interfaces"}

            return {
                "versionServer": VERSION,
                "name_instance": ConfigModel.get_general_name(user_data.user_id)
            }

    def setup_website(self) -> None:
        @ui.page("/")
        async def coming_soon_page(client: Client) -> None:
            address = await Server._get_address(client)
            secret = secrets.token_urlsafe(32)

            with ui.header() as header:
                header.classes(add="bg-transparent text-white flex justify-between")

                ui.label(f"{address}").classes()

                with ui.button("Admin Login", on_click=lambda: ui.open("/admin")) as login_button:
                    pass

            with ui.element("div") as container:
                container.classes(add="w-full max-w-4xl m-auto")

                logo = ui.image("static/images/logo_big.svg")
                logo.classes(add="w-full")

                ui.element("div").classes(add="h-16")
                ui.label("Installation").classes(add="text-xl font-bold text-center m-8 ")
                get_section(secret, address, VERSION, title=False)

                ui.element("div").classes(add="h-16")
                ui.label("Claim extraction").classes(add="text-xl font-bold text-center m-8 ")
                with ui.video("static/videos/extract.webm", autoplay=False, loop=False, muted=True) as video:
                    video.classes(add="w-full max-w-2xl m-auto")

                ui.element("div").classes(add="h-16")
                ui.label("Document retrieval and claim checking").classes(add="text-xl font-bold text-center m-8 ")
                with ui.video("static/videos/retrieval.webm", autoplay=False, loop=False, muted=True) as video:
                    video.classes(add="w-full max-w-2xl m-auto")

                ui.element("div").classes(add="h-8")

                ui.link(
                    text="Funded by the Media Tech Lab",
                    target="https://www.media-lab.de/de/media-tech-lab/DoppelCheck",
                    new_tab=True).classes(add="text-center block ")

        @ui.page('/login')
        def login() -> RedirectResponse | None:
            def try_login() -> None:
                if PASSWORDS.get(username.value) == password.value:
                    app.storage.user.update({'username': username.value, 'authenticated': True})
                    ui.open(app.storage.user.get('referrer_path', '/'))  # go back to where the user wanted to go
                else:
                    ui.notify('Wrong username or password', color='negative')

            if app.storage.user.get('authenticated', False):
                return RedirectResponse('/')

            with ui.card().classes('absolute-center'):
                username = ui.input('Username')
                username.on('keydown.enter', try_login)

                password = ui.input('Password', password=True, password_toggle_button=True)
                password.on('keydown.enter', try_login)

                ui.button('Log in', on_click=try_login)

            return None

        @ui.page("/admin")
        async def configuration_layout(client: Client) -> None:
            address = await Server._get_address(client)

            def reset_context() -> None:
                app.storage.user.clear()
                ui.open('/')

            with ui.header() as header:
                header.classes(add="bg-transparent text-white flex justify-end")
                user_name = app.storage.user['username']
                with ui.button(f"Logout {user_name}", on_click=reset_context) as logout_button:
                    pass

            await full_configuration("ADMIN", address, VERSION)

        @ui.page("/config/{userid}")
        async def config(userid: str, client: Client) -> None:
            address = await Server._get_address(client)
            await full_configuration(userid, address, VERSION)

    def setup_websocket(self) -> None:
        @app.websocket("/talk")
        async def websocket_endpoint(websocket: WebSocket):
            # todo:
            #  check out alternative implementation:
            #  https://github.com/zauberzeug/nicegui/blob/main/examples/websockets/main.py
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

                    case "extract" | "extract_selection":
                        # Keypoint Assistant
                        base_text = data if purpose == "extract" else text_node_generator(data)
                        await self.set_context(original_url, user_id, html_document=data)
                        async for segment in self.get_claims_from_str(base_text, user_id):
                            each_dict = dataclasses.asdict(segment)
                            json_str = json.dumps(each_dict)
                            await websocket.send_text(json_str)

                    case "retrieve":
                        # Sourcefinder Assistant
                        claim_id = data['id']
                        claim_text = data['text']

                        async for segment in self.get_document_uris(claim_id, claim_text, user_id, original_url):
                            each_dict = dataclasses.asdict(segment)
                            json_str = json.dumps(each_dict)
                            await websocket.send_text(json_str)

                    case "compare":
                        # Crosschecker Assistant
                        claim_id = data['claim_id']
                        claim_text = data['claim_text']
                        document_id = data['document_id']
                        document_uri = data['document_uri']
                        async for segment in self.get_matches(
                                user_id, claim_id, claim_text, document_id, original_url, document_uri):
                            each_dict = dataclasses.asdict(segment)
                            json_str = json.dumps(each_dict)
                            await websocket.send_text(json_str)

                    case "log":
                        raise NotImplementedError("log purpose not implemented")

                    case _:
                        message_segment = MessageSegment(f"unknown purpose {purpose}, len {len(data)}", True, True)
                        each_dict = dataclasses.asdict(message_segment)
                        json_str = json.dumps(each_dict)
                        await websocket.send_text(json_str)

            except WebSocketDisconnect as e:
                print(e)


app.mount("/static", StaticFiles(directory="static"), name="static")


def main() -> None:
    with open("config.json") as file:
        config = json.load(file)

    nicegui_config = config.pop("nicegui")

    server = Server()

    server.setup_api_endpoints()
    server.setup_website()
    server.setup_websocket()

    ui.run(**nicegui_config)

    # todo: use gunicorn or uvicorn instead


if __name__ in {"__main__", "__mp_main__"}:
    main()


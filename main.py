import asyncio
import dataclasses
import json
import secrets
import string
from typing import Generator, Sequence, AsyncGenerator, Iterable
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
from starlette.responses import Response

from configuration.config_02_extraction import DEFAULT_CUSTOM_EXTRACTION_PROMPT
from configuration.config_04_comparison import DEFAULT_CUSTOM_COMPARISON_PROMPT
from configuration.config_install import get_section_install
from configuration.full import full_configuration
from model.data_access import get_data_value, set_data_value
from model.storages import ConfigModel, PasswordsModel
from plugins.abstract import InterfaceLLM, InterfaceData, InterfaceDataConfig
from prompts.agent_patterns import instruction_keypoint_extraction, instruction_crosschecking
from tools.content_retrieval import get_context
from tools.global_instances import BROWSER_INSTANCE
from tools.data_objects import (
    Pong, KeypointMessage, QuoteMessage, Message, SourcesMessage, ErrorMessage, RatingMessage, ExplanationMessage)
from tools.text_processing import (
    text_node_generator, pipe_codeblock_content, get_range, get_text_lines)

from starlette.middleware.base import BaseHTTPMiddleware


VERSION = "0.1.6"
UNRESTRICTED = {"/", "/config", "/login"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
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
            response: AsyncGenerator[str, None],
            text_lines: Sequence[str]
    ) -> Generator[Message, None, None]:

        claim_index = 0
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

                    start_line, end_line = line_range
                    highlight_text = "".join(text_lines[start_line - 1:end_line - 1])
                    yield QuoteMessage(keypoint_index=claim_index, content=highlight_text)
                    in_num_range = False

                continue

            last_segment = each_segment.segment == "\n"
            if not last_segment:
                yield KeypointMessage(keypoint_index=claim_index, content=each_segment.segment)

            else:
                yield KeypointMessage(keypoint_index=claim_index, stop=True)
                num_range_str = ""
                in_num_range = True
                claim_index += 1

    @staticmethod
    async def _stream_crosscheck_to_browser(
            response: AsyncGenerator[str, None], keypoint_index: int, source_index: int
    ) -> Generator[RatingMessage | ExplanationMessage, None, None]:

        in_rating = True

        async for each_segment in pipe_codeblock_content(response):
            for each_char in each_segment.segment:
                if each_char == "\n":
                    in_rating = False
                    continue

                if in_rating:
                    yield RatingMessage(keypoint_index=keypoint_index, source_index=source_index, content=each_char)
                else:
                    yield ExplanationMessage(
                        keypoint_index=keypoint_index, source_index=source_index, content=each_char)

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
    def get_data_interfaces(user_id: str) -> list[InterfaceData]:
        data_interface_configs = ConfigModel.get_selected_data_interfaces(user_id)
        if data_interface_configs is None:
            logger.error(f"ConfigModel.get_data({user_id})")
            raise RetrieveDocumentException(f"ConfigModel.get_data({user_id})")

        selected_interfaces = list()
        for each_data_interface_config in data_interface_configs:
            data_interface = Server._data_interface_from_config(each_data_interface_config)
            selected_interfaces.append(data_interface)

        return selected_interfaces

    @staticmethod
    def _data_interface_from_config(each_data_interface_config: InterfaceDataConfig) -> InterfaceData:
        keywords = each_data_interface_config.object_to_state()
        class_ = each_data_interface_config.get_interface_class()
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

    def __init__(self) -> None:
        nltk.download('punkt')
        detector = lingua.LanguageDetectorBuilder.from_all_languages()
        self._detector_built = detector.build()

    def _detect_language(self, text: str) -> str:
        language = self._detector_built.detect_language_of(text)
        if language is None:
            return "en"

        return language.iso_code_639_1.name.lower()

    async def get_claims_from_str(
            self, string_sequence: Iterable[str],
            user_id: str) -> Generator[Message, None, None]:
        llm_interface = await self.get_extraction_llm_interface(user_id)

        claim_count = ConfigModel.get_extraction_claims(user_id)
        language = ConfigModel.get_general_language(user_id)

        text_lines = list(get_text_lines(string_sequence, line_length=20))
        customized_instruction = ConfigModel.get_extraction_prompt(user_id) or DEFAULT_CUSTOM_EXTRACTION_PROMPT
        prompt = instruction_keypoint_extraction(
            text_lines, customized_instruction, num_keypoints=claim_count, language=language
        )

        response = llm_interface.stream_reply_to_prompt(prompt)
        async for each_segment in Server._stream_claims_to_browser(response, text_lines):
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
        self, keypoint_index: int, keypoint_text: str, user_id: str, original_url: str
    ) -> AsyncGenerator[SourcesMessage, None]:

        data_interfaces = Server.get_data_interfaces(user_id)

        llm_interface = Server.get_retrieval_llm_interface(user_id)
        language = ConfigModel.get_general_language(user_id)
        context = get_data_value(user_id, ("context", original_url))

        for each_interface in data_interfaces:
            query = await each_interface.get_search_query(
                llm_interface, keypoint_text, context=context, language=language
            )

            doc_count = ConfigModel.get_retrieval_max_documents(user_id)
            async for each_uri in each_interface.get_uris(query, doc_count):
                yield SourcesMessage(
                    keypoint_index=keypoint_index, data_source=each_interface.name,
                    query=query, content=each_uri.uri_string, title=each_uri.title
                )

    async def get_matches(
            self,
            user_id: str, keypoint_index: int, keypoint_text: str,
            source_index: int, original_url: str, source_uri: str,
            data_interface_name: str
    ) -> Generator[RatingMessage | ExplanationMessage, None, None]:

        llm_interface = Server.get_match_llm_interface(user_id)
        data_interface_config = ConfigModel.get_data_interface(user_id, data_interface_name)
        data_interface = Server._data_interface_from_config(data_interface_config)

        language = ConfigModel.get_general_language(user_id)

        source = await data_interface.get_document_content(source_uri)
        document_html = source.content

        node_generator = text_node_generator(document_html)
        document_text = "".join(node_generator)

        context = get_data_value(user_id, ("context", original_url))
        customized_instruction = ConfigModel.get_comparison_prompt(user_id) or DEFAULT_CUSTOM_COMPARISON_PROMPT
        prompt = instruction_crosschecking(
            keypoint_text, document_text, customized_instruction, context=context, language=language
        )

        response = llm_interface.stream_reply_to_prompt(prompt)

        async for each_segment in Server._stream_crosscheck_to_browser(response, keypoint_index, source_index):
            yield each_segment

    async def set_context(self, original_url: str, user_id: str, html_document: str | None = None) -> None:
        context = await get_context(original_url, self._detect_language, input_html=html_document)
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

            data_interfaces = ConfigModel.get_selected_data_interfaces(user_data.user_id)

            if (
                    (ConfigModel.get_extraction_llm(user_data.user_id) is None) or
                    (ConfigModel.get_retrieval_llm(user_data.user_id) is None) or
                    (len(data_interfaces) < 1) or
                    (ConfigModel.get_comparison_llm(user_data.user_id) is None)
            ):
                logger.error(f"no interface for {user_data.user_id}")
                return {"error": "missing interfaces"}

            return {
                "versionServer": VERSION,
                "nameInstance": ConfigModel.get_general_name(user_data.user_id),
                "dataSources": [each.name for each in data_interfaces],
            }

    def setup_website(self) -> None:
        @ui.page("/")
        async def start_page(client: Client) -> None:
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
                get_section_install(secret, address, VERSION, title=False)

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

        @app.get("/doc/")
        def documentation() -> RedirectResponse:
            return RedirectResponse("https://github.com/Doppelcheck/main/wiki")

        @ui.page('/login')
        def login() -> RedirectResponse | None:
            async def try_login() -> None:
                if not PasswordsModel.admin_registered():
                    PasswordsModel.add_password(username.value, password.value)
                    ui.notify(f"Admin user '{username.value}' created", color='positive')
                    await asyncio.sleep(3)
                    app.storage.user.update({'username': username.value, 'authenticated': True})
                    ui.open(app.storage.user.get('referrer_path', '/'))

                elif PasswordsModel.check_password(username.value, password.value):
                    app.storage.user.update({'username': username.value, 'authenticated': True})
                    ui.open(app.storage.user.get('referrer_path', '/'))  # go back to where the user wanted to go

                else:
                    ui.notify('Wrong username or password', color='negative')

            if app.storage.user.get('authenticated', False):
                return RedirectResponse('/')

            with ui.card().classes('absolute-center'):
                if not PasswordsModel.admin_registered():
                    ui.label("Attention! You are creating the admin user!").classes("text-center")

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

            await full_configuration(None, address, VERSION)

        @ui.page("/config/{userid}")
        async def config(userid: str, client: Client) -> None:
            if userid is None or len(userid) < 1:
                ui.open("/")
                return

            address = await Server._get_address(client)
            await full_configuration(userid, address, VERSION)

    def setup_websocket(self) -> None:

        def to_json(message: dataclasses.dataclass, user_id: str) -> dict:
            dc_dict = dataclasses.asdict(message)
            dc_dict["user_id"] = user_id
            return dc_dict

        @app.websocket("/talk")
        async def websocket_endpoint(websocket: WebSocket):
            # todo:
            #  check out alternative implementation:
            #  https://github.com/zauberzeug/nicegui/blob/main/examples/websockets/main.py
            #  streaming response is for files.
            #  https://stackoverflow.com/questions/75740652/fastapi-streamingresponse-not-streaming-with-generator-function
            #  server sent events?
            await websocket.accept()
            try:
                message = await websocket.receive_json()
                message_type = message['message_type']
                user_id = message['user_id']
                original_url = message['original_url']
                content = message['content']

                match message_type:
                    case "ping":
                        answer = Pong()
                        json_dict = to_json(answer, user_id)
                        await websocket.send_json(json_dict)

                    case "keypoint" | "keypoint_selection":
                        # [x] Keypoint Assistant
                        if message_type == "keypoint":
                            base_text = text_node_generator(content)
                        else:
                            base_text = content
                            content = None

                        await self.set_context(original_url, user_id, html_document=content)
                        async for segment in self.get_claims_from_str(base_text, user_id):
                            each_dict = to_json(segment, user_id)
                            await websocket.send_json(each_dict)

                        stop_message = KeypointMessage(stop_all=True, keypoint_index=-1)
                        stop_dict = to_json(stop_message, user_id)
                        await websocket.send_json(stop_dict)

                    case "sourcefinder":
                        # [x] Sourcefinder Assistant
                        keypoint_index = content['keypoint_index']
                        keypoint_text = content['keypoint_text']

                        uri_generator = self.get_document_uris(keypoint_index, keypoint_text, user_id, original_url)
                        async for segment in uri_generator:
                            each_dict = dataclasses.asdict(segment)
                            await websocket.send_json(each_dict)

                        stop_message = SourcesMessage(
                            stop=True, keypoint_index=keypoint_index, data_source="", query=""
                        )
                        stop_dict = dataclasses.asdict(stop_message)
                        await websocket.send_json(stop_dict)

                    case "crosschecker":
                        # [x] Crosschecker Assistant
                        keypoint_index = content['keypoint_index']
                        keypoint_text = content['keypoint_text']
                        source_index = content['source_index']
                        source_uri = content['source_uri']
                        data_source = content['data_source']
                        async for segment in self.get_matches(
                            user_id, keypoint_index, keypoint_text, source_index, original_url, source_uri, data_source
                        ):
                            each_dict = dataclasses.asdict(segment)
                            await websocket.send_json(each_dict)

                        stop_message = ExplanationMessage(
                            stop=True, keypoint_index=keypoint_index, source_index=source_index)
                        stop_dict = dataclasses.asdict(stop_message)
                        await websocket.send_json(stop_dict)

                    case "log":
                        raise NotImplementedError("log not implemented")

                    case _:
                        message_segment = ErrorMessage(
                            content=f"unknown message type {message_type}, len {len(content)}")
                        each_dict = dataclasses.asdict(message_segment)
                        await websocket.send_json(each_dict)

            except WebSocketDisconnect as e:
                logger.error(f"websocket disconnected: {e}")

            except Exception as e:
                error_message = ErrorMessage(content=str(e))
                error_dict = dataclasses.asdict(error_message)
                await websocket.send_json(error_dict)
                raise e


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


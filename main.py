import asyncio
import dataclasses
import json
import secrets
import string
import uuid
from typing import Generator, Sequence, AsyncGenerator, Iterable
from urllib.parse import urlparse, unquote

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
from model.storages import ConfigModel, PasswordsModel
from plugins.abstract import InterfaceLLM, InterfaceData, InterfaceDataConfig, Uri
from prompts.agent_patterns import instruction_keypoint_extraction, instruction_crosschecking
from tools.content_retrieval import parse_url
from tools.global_instances import BROWSER_INSTANCE
from tools.data_objects import (
    Pong, KeypointMessage, QuoteMessage, Message, SourcesMessage, ErrorMessage, RatingMessage, ExplanationMessage)
from tools.text_processing import (
    text_node_generator, pipe_codeblock_content, get_range, get_text_lines)

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from starlette.middleware.base import BaseHTTPMiddleware


VERSION = "0.3.1"
UNRESTRICTED = {"/", "/config", "/login", "/doc"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not app.storage.user.get('authenticated', False):
            if request.url.path in Client.page_routes.values() and request.url.path not in UNRESTRICTED:
                app.storage.user['referrer_path'] = request.url.path  # remember where the user wanted to go
                return RedirectResponse('/login')
        return await call_next(request)


limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


class RetrieveSourceException(Exception):
    pass


class Instance(BaseModel):
    instance_id: str | None
    version: str | None


class Server:
    @staticmethod
    async def _get_address(client: Client) -> str:
        await client.connected()
        js_url = await ui.run_javascript('window.location.href')
        parsed_url = urlparse(js_url)
        return parsed_url.netloc

    @staticmethod
    async def _stream_keypoints_to_browser(
            instance_id: str,
            response: AsyncGenerator[str, None],
            text_lines: Sequence[str]
    ) -> Generator[Message, None, None]:

        keypoint_id = ConfigModel.increment_keypoint_index(instance_id)
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
                    yield QuoteMessage(keypoint_id=keypoint_id, content=highlight_text)
                    in_num_range = False

                continue

            last_segment = each_segment.segment == "\n"
            if not last_segment:
                yield KeypointMessage(keypoint_id=keypoint_id, content=each_segment.segment)

            else:
                yield KeypointMessage(keypoint_id=keypoint_id, stop=True)
                num_range_str = ""
                in_num_range = True
                keypoint_id = ConfigModel.increment_keypoint_index(instance_id)

    @staticmethod
    async def _stream_crosscheck_to_browser(
            response: AsyncGenerator[str, None], keypoint_id: int, source_id: str
    ) -> Generator[RatingMessage | ExplanationMessage, None, None]:

        in_rating = True

        async for each_segment in pipe_codeblock_content(response):
            for each_char in each_segment.segment:
                if each_char == "\n":
                    in_rating = False
                    continue

                if in_rating:
                    yield RatingMessage(keypoint_id=keypoint_id, source_id=source_id, content=each_char)
                else:
                    yield ExplanationMessage(
                        keypoint_id=keypoint_id, source_id=source_id, content=each_char)

    @staticmethod
    def get_match_llm_interface(instance_id: str) -> InterfaceLLM:
        llm_interface_config = ConfigModel.get_comparison_llm(instance_id)
        if llm_interface_config is None:
            logger.error(f"ConfigModel.get_comparison_llm({instance_id})")
            raise RetrieveSourceException(f"ConfigModel.get_comparison_llm({instance_id})")
        keywords = llm_interface_config.object_to_state()
        class_ = llm_interface_config.get_interface_class()
        llm_interface: InterfaceLLM = class_.from_state(keywords)
        return llm_interface

    @staticmethod
    def get_data_interfaces(instance_id: str) -> list[InterfaceData]:
        data_interface_configs = ConfigModel.get_selected_data_interfaces(instance_id)
        if data_interface_configs is None:
            logger.error(f"ConfigModel.get_data({instance_id})")
            raise RetrieveSourceException(f"ConfigModel.get_data({instance_id})")

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
    def get_retrieval_llm_interface(instance_id: str) -> InterfaceLLM:
        llm_interface_config = ConfigModel.get_retrieval_llm(instance_id)
        if llm_interface_config is None:
            logger.error(f"ConfigModel.get_retrieval_llm({instance_id})")
            raise RetrieveSourceException(f"ConfigModel.get_retrieval_llm({instance_id})")
        keywords = llm_interface_config.object_to_state()
        class_ = llm_interface_config.get_interface_class()
        llm_interface: InterfaceLLM = class_.from_state(keywords)
        return llm_interface

    def __init__(self) -> None:
        nltk.download('punkt')

    async def get_keypoints_from_str(
            self, string_sequence: Iterable[str], keypoint_count: int,
            instance_id: str) -> Generator[Message, None, None]:
        llm_interface = await self.get_extraction_llm_interface(instance_id)

        language = ConfigModel.get_general_language(instance_id)

        text_lines = list(get_text_lines(string_sequence, line_length=20))
        customized_instruction = ConfigModel.get_extraction_prompt(instance_id) or DEFAULT_CUSTOM_EXTRACTION_PROMPT
        prompt = instruction_keypoint_extraction(
            text_lines, customized_instruction, num_keypoints=keypoint_count, language=language
        )

        # noinspection PyTypeChecker
        response: AsyncGenerator[str, None] = llm_interface.stream_reply_to_prompt(prompt)
        async for each_segment in Server._stream_keypoints_to_browser(instance_id, response, text_lines):
            yield each_segment

    async def get_extraction_llm_interface(self, instance_id: str) -> InterfaceLLM:
        llm_interface_config = ConfigModel.get_extraction_llm(instance_id)
        if llm_interface_config is None:
            logger.error(f"ConfigModel.get_extraction_llm({instance_id})")
            raise RetrieveSourceException(f"ConfigModel.get_extraction_llm({instance_id})")
        keywords = llm_interface_config.object_to_state()
        class_ = llm_interface_config.get_interface_class()
        llm_interface: InterfaceLLM = class_.from_state(keywords)
        return llm_interface

    async def get_source_uris(
        self, keypoint_id: int, keypoint_text: str, instance_id: str, original_url: str
    ) -> AsyncGenerator[SourcesMessage, None]:

        data_interfaces = Server.get_data_interfaces(instance_id)
        llm_interface = Server.get_retrieval_llm_interface(instance_id)
        language = ConfigModel.get_general_language(instance_id)

        content = await BROWSER_INSTANCE.get_html_content(original_url)
        article = await parse_url(original_url, input_html=content.content)
        context = f"{article.title.upper()}\n\n{article.summary}"

        if len(context.strip()) < 20:
            context = None

        elif article.publish_date is not None:
            context += f"\n\npublished on {article.publish_date}"

        async def get_uris(data_interface: InterfaceData) -> tuple[InterfaceData, str, list[Uri]]:
            _query = await data_interface.get_search_query(
                llm_interface, keypoint_text, context=context, language=language
            )

            # noinspection PyTypeChecker
            interface_uris: AsyncGenerator[Uri, None] = data_interface.get_uris(_query)
            return data_interface, _query, [_each_uri async for _each_uri in interface_uris]

        tasks = [get_uris(each_interface) for each_interface in data_interfaces]

        for future in asyncio.as_completed(tasks):
            each_interface, query, uris = await future
            for each_uri in uris:
                each_id = uuid.uuid4().hex
                yield SourcesMessage(
                    keypoint_id=keypoint_id, source_id=each_id, data_source=each_interface.name,
                    query=query, content=each_uri.uri_string, title=each_uri.title
                )

    async def get_matches(
            self, instance_id: str, keypoint_id: int, keypoint_text: str,
            source_id: str, source_uri: str, data_interface_name: str
    ) -> Generator[RatingMessage | ExplanationMessage, None, None]:

        llm_interface = Server.get_match_llm_interface(instance_id)
        data_interface_config = ConfigModel.get_data_interface(instance_id, data_interface_name)
        data_interface = Server._data_interface_from_config(data_interface_config)

        language = ConfigModel.get_general_language(instance_id)

        source = await data_interface.get_source_content(source_uri)
        source_content = source.content

        node_generator = text_node_generator(source_content)
        source_text = "".join(node_generator)

        customized_instruction = ConfigModel.get_comparison_prompt(instance_id) or DEFAULT_CUSTOM_COMPARISON_PROMPT
        prompt = instruction_crosschecking(
            keypoint_text, source_text, customized_instruction, language=language
        )

        # noinspection PyTypeChecker
        response: AsyncGenerator[str, None] = llm_interface.stream_reply_to_prompt(prompt)
        async for each_segment in Server._stream_crosscheck_to_browser(response, keypoint_id, source_id):
            yield each_segment

    @staticmethod
    def _to_json(message: dataclasses.dataclass, instance_id: str) -> dict:
        dc_dict = dataclasses.asdict(message)
        dc_dict["instance_id"] = instance_id
        return dc_dict

    def setup_api_endpoints(self) -> None:
        @app.get("/get_content/")
        @limiter.limit("5/minute")
        async def get_content(request: Request, url: str, response: Response) -> HTMLResponse:
            """
            const urlEncoded = encodeURIComponent(originalUrl);
            return `https://${address}/get_content/?url=${urlEncoded}`;
            """
            url_parsed = unquote(url)

            source = await BROWSER_INSTANCE.get_html_content(url_parsed)
            html_content = source.content

            return HTMLResponse(html_content)

        @app.post("/get_config/")
        @limiter.limit("5/minute")
        async def get_config(request: Request, response: Response, instance_data: Instance = Body(...)) -> dict:
            """
            const configUrl = `https://${address}/get_config/`;
            const userData = { instance_id: instanceId, version: versionClient };
            """
            logger.info(f"getting settings for {instance_data.instance_id}")

            # todo: check if config is set up

            if instance_data.version != VERSION:
                logger.error(f"client version {instance_data.version} does not match server version {VERSION}")
                return {
                    "error": "client version does not match server version",
                    "versionServer": VERSION,
                }

            if instance_data.instance_id is None:
                logger.error(f"no instance_id in {instance_data}")
                return {"error": "no instance id provided"}

            data_interfaces = ConfigModel.get_selected_data_interfaces(instance_data.instance_id)

            if (
                    (ConfigModel.get_extraction_llm(instance_data.instance_id) is None) or
                    (ConfigModel.get_retrieval_llm(instance_data.instance_id) is None) or
                    (len(data_interfaces) < 1) or
                    (ConfigModel.get_comparison_llm(instance_data.instance_id) is None)
            ):
                logger.error(f"no interface for {instance_data.instance_id}")
                return {"error": "missing interfaces"}

            return {
                "versionServer": VERSION,
                "nameInstance": ConfigModel.get_general_name(instance_data.instance_id),
                "dataSources": [each.name for each in data_interfaces],
            }

    def setup_website(self) -> None:
        @ui.page("/")
        @limiter.limit("5/minute")
        async def start_page(request: Request, client: Client, response: Response) -> None:
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
                ui.label(f"Installation v{VERSION}").classes(add="text-xl font-bold text-center m-8 ")
                get_section_install(secret, address, VERSION, title=False)

                ui.element("div").classes(add="h-16")
                ui.label("Keypoint extraction").classes(add="text-xl font-bold text-center m-8 ")
                with ui.video("static/videos/extract.webm", autoplay=False, loop=False, muted=True) as video:
                    video.classes(add="w-full max-w-2xl m-auto")

                ui.element("div").classes(add="h-16")
                ui.label("Source retrieval and keypoint comparison").classes(add="text-xl font-bold text-center m-8 ")
                with ui.video("static/videos/retrieval.webm", autoplay=False, loop=False, muted=True) as video:
                    video.classes(add="w-full max-w-2xl m-auto")

                ui.element("div").classes(add="h-16")
                ui.label("Video retrieval and comparison").classes(add="text-xl font-bold text-center m-8 ")
                with ui.video("static/videos/youtube.webm", autoplay=False, loop=False, muted=False) as video:
                    video.classes(add="w-full max-w-2xl m-auto")

                ui.element("div").classes(add="h-8")

                ui.link(
                    text="Funded by the Media Tech Lab",
                    target="https://www.media-lab.de/de/media-tech-lab/DoppelCheck",
                    new_tab=True).classes(add="text-center block ")

        @app.get("/doc")
        @limiter.limit("5/minute")
        def documentation(request: Request, response: Response) -> RedirectResponse:
            return RedirectResponse("https://github.com/Doppelcheck/main/wiki")

        @ui.page('/login')
        @limiter.limit("5/minute")
        def login(request: Request, response: Response) -> RedirectResponse | None:
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
        @limiter.limit("5/minute")
        async def configuration_layout(request: Request, client: Client, response: Response) -> None:
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

        @ui.page("/config/{instance_id}")
        @limiter.limit("5/minute")
        async def config(request: Request, instance_id: str, client: Client, response: Response) -> None:
            if instance_id is None or len(instance_id) < 1:
                ui.open("/")
                return

            address = await Server._get_address(client)
            await full_configuration(instance_id, address, VERSION)

    def setup_websocket(self) -> None:
        @app.websocket("/talk")
        async def websocket_endpoint(websocket: WebSocket) -> None:
            # todo:
            #  add rate limiting
            #  check out alternative implementation:
            #  https://github.com/zauberzeug/nicegui/blob/main/examples/websockets/main.py
            #  streaming response is for files.
            #  https://stackoverflow.com/questions/75740652/fastapi-streamingresponse-not-streaming-with-generator-function
            #  server sent events?
            # websocket.client.host
            await websocket.accept()

            try:
                message = await websocket.receive_json()
                instance_id = message['instance_id']
                message_type = message['message_type']
                original_url = message['original_url']
                content = message['content']

                match message_type:
                    case "ping":
                        answer = Pong()
                        json_dict = Server._to_json(answer, instance_id)
                        await websocket.send_json(json_dict)

                    case "keypoint" | "keypoint_selection":
                        # [x] Keypoint Assistant
                        if message_type == "keypoint":
                            base_text = text_node_generator(content)
                            keypoint_count = ConfigModel.get_number_of_keypoints(instance_id)

                        else:
                            base_text = content
                            keypoint_count = 1

                        async for segment in self.get_keypoints_from_str(base_text, keypoint_count, instance_id):
                            each_dict = Server._to_json(segment, instance_id)
                            await websocket.send_json(each_dict)
                            continue

                        # stop_message = KeypointMessage(stop_all=True, keypoint_id=-1)
                        # stop_dict = to_json(stop_message, instance_id)
                        # await websocket.send_json(stop_dict)

                    case "sourcefinder":
                        # [x] Sourcefinder Assistant
                        keypoint_id = content['keypoint_id']
                        keypoint_text = content['keypoint_text']

                        uri_generator = self.get_source_uris(keypoint_id, keypoint_text, instance_id, original_url)
                        async for segment in uri_generator:
                            each_dict = dataclasses.asdict(segment)
                            await websocket.send_json(each_dict)

                        stop_message = SourcesMessage(
                            stop=True, source_id="", keypoint_id=keypoint_id, data_source="", query=""
                        )
                        stop_dict = dataclasses.asdict(stop_message)
                        await websocket.send_json(stop_dict)

                    case "crosschecker":
                        # [x] Crosschecker Assistant
                        keypoint_id = content['keypoint_id']
                        keypoint_text = content['keypoint_text']
                        source_id = content['source_id']
                        source_uri = content['source_uri']
                        data_source = content['data_source']
                        async for segment in self.get_matches(
                            instance_id, keypoint_id, keypoint_text, source_id, source_uri, data_source
                        ):
                            each_dict = dataclasses.asdict(segment)
                            await websocket.send_json(each_dict)

                        stop_message = ExplanationMessage(stop=True, keypoint_id=keypoint_id, source_id=source_id)
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

            except RateLimitExceeded as e:
                logger.error(f"rate limit exceeded: {e}")
                error_message = ErrorMessage(content="rate limit exceeded")
                error_dict = dataclasses.asdict(error_message)
                await websocket.send_json(error_dict)

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


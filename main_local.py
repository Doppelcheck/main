import os
import dataclasses
import json
import secrets
import string
import uuid
from typing import Generator, Sequence, AsyncGenerator, Iterable
from urllib.parse import urlparse, unquote

import markdownify
import nltk
from fastapi import WebSocket, WebSocketDisconnect, Body, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from nicegui import ui, app, Client
from pydantic import BaseModel
from starlette.responses import Response

from configuration.config_02_extraction import DEFAULT_CUSTOM_EXTRACTION_PROMPT
from configuration.config_install import get_section_install
from configuration.full import full_configuration
from model.storages import ConfigModel
from plugins.abstract import InterfaceLLM
from prompts.agent_patterns import instruction_keypoint_extraction
from tools.content_retrieval import get_relevant_chunks, markdown_to_plain_text, \
    get_google_results, get_wiki_results
from tools.global_instances import BROWSER_INSTANCE
from tools.data_objects import (
    Pong, KeypointMessage, QuoteMessage, Message, SourcesMessage, ErrorMessage, RatingMessage, ExplanationMessage)
from tools.local_llm import summarize_ollama, search_query_google_ollama, search_query_wikipedia_ollama, prompt_ollama
from tools.text_processing import (pipe_codeblock_content, get_range, get_text_lines)
import trafilatura


VERSION = "0.4.0"


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


    def __init__(self) -> None:
        nltk.download('punkt')

    async def get_keypoints_from_str(
            self, string_sequence: Iterable[str], keypoint_count: int,
            instance_id: str) -> Generator[Message, None, None]:
        llm_interface = await self.get_extraction_llm_interface(instance_id)

        language = ConfigModel.get_general_language(instance_id)

        full_string = "".join(string_sequence)
        logger.info(f"summarizing original text ({len(full_string)} characters)")
        summarized = await llm_interface.summarize(full_string)

        text_lines = list(get_text_lines(summarized, line_length=20))
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

    async def get_matches(
            self, instance_id: str, keypoint_id: int, keypoint_text: str,
            source_id: str, source_uri: str
    ) -> Generator[RatingMessage | ExplanationMessage, None, None]:

        """
        cleaned up source text (trafilatura or readabilipy)
        """

        file_content = await BROWSER_INSTANCE.get_html_content(source_uri)
        source_content = trafilatura.extract(file_content, url=source_uri, output_format="markdown")

        prompt = (
            f"```source\n"
            f"{source_content}\n"
            f"```\n"
            f"\n"
            f"```claim\n"
            f"{keypoint_text}\n"
            f"```\n"
            f"\n"
            f"Determine the semantic similarity between the `claim` and the `source` above. Respond with a rating "
            f"from -2 to +2, where -2 indicates strong contradiction and +2 indicates strong support. Also provide a "
            f"short, one-sentence explanation for the rating. If the source text is not relevant to the claim, respond "
            f"with a rating of 0.\n"
            f"\n"
            f"Answer in the following format, without the code fence:\n"
            f"```\n"
            f"1\n"
            f"The claim is partially supported by the source text.\n"
            f"```\n"
            f"\n"
        )

        # noinspection PyTypeChecker
        response: AsyncGenerator[str, None] = prompt_ollama(prompt)
        async for each_segment in Server._stream_crosscheck_to_browser(response, keypoint_id, source_id):
            yield each_segment

    @staticmethod
    def _to_json(message: dataclasses.dataclass, instance_id: str) -> dict:
        dc_dict = dataclasses.asdict(message)
        dc_dict["instance_id"] = instance_id
        return dc_dict

    def setup_api_endpoints(self) -> None:
        @app.get("/get_content/")
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

                ui.label("Funded by").classes(add="text-xl font-bold text-center m-8 ")
                ui.link(
                    text="The Media Tech Lab",
                    target="https://www.media-lab.de/",
                    new_tab=True).classes(add="text-center block ")
                ui.link(
                    text="WPK Innovationsfonds",
                    target="https://innovationsfonds.wpk.org/",
                    new_tab=True).classes(add="text-center block ")


        @app.get("/doc")
        def documentation(request: Request, response: Response) -> RedirectResponse:
            return RedirectResponse("https://github.com/Doppelcheck/main/wiki")


        @ui.page("/config")
        async def config(request: Request, client: Client, response: Response) -> None:
            address = await Server._get_address(client)
            instance_id = ""
            await full_configuration(instance_id, address, VERSION)

    def setup_websocket(self) -> None:
        @app.websocket("/talk")
        async def websocket_endpoint(websocket: WebSocket) -> None:
            await websocket.accept()

            try:
                message = await websocket.receive_json()
                instance_id = message['instance_id']
                message_type = message['message_type']
                original_url = message['original_url']
                html_content = message['content']

                match message_type:
                    case "ping":
                        answer = Pong()
                        json_dict = Server._to_json(answer, instance_id)
                        await websocket.send_json(json_dict)

                    case "keypoint_new":
                        markdown_text = markdownify.markdownify(html_content)
                        relevant_chunks = get_relevant_chunks(markdown_text)
                        for chunk_index, md_chunk in enumerate(relevant_chunks):
                            print(f"\nChunk {chunk_index + 1}:\n", end='')
                            print(md_chunk)

                            plain_chunk = markdown_to_plain_text(md_chunk)
                            quote_message = QuoteMessage(keypoint_id=chunk_index, content=plain_chunk)
                            quote_dict = Server._to_json(quote_message, instance_id)
                            await websocket.send_json(quote_dict)

                            print(f"\nSummary of chunk {chunk_index + 1}:\n", end='')
                            # stream = summarize_ollama(md_chunk, context=markdown_text)
                            stream = summarize_ollama(md_chunk)
                            each_statements = ""
                            async for each_response in stream:
                                each_statements += each_response
                                print(each_response, end='', flush=True)
                                keypoint_message = KeypointMessage(keypoint_id=chunk_index, content=each_response)
                                keypoint_dict = Server._to_json(keypoint_message, instance_id)
                                await websocket.send_json(keypoint_dict)

                            last_keypoint = chunk_index >= len(relevant_chunks) - 1
                            keypoint_message = KeypointMessage(keypoint_id=chunk_index, stop=True, stop_all=last_keypoint)
                            keypoint_dict = Server._to_json(keypoint_message, instance_id)
                            await websocket.send_json(keypoint_dict)

                            print()

                        """
                        summaries need context
                            + add metadata
                                + stuff from article.get_metadata() ?
                        """

                    case "sourcefinder":
                        # [x] Sourcefinder Assistant
                        keypoint_id = html_content['keypoint_id']
                        keypoint_text = html_content['keypoint_text']

                        query_google = search_query_google_ollama(keypoint_text)
                        query_google_str = ""
                        async for each_query in query_google:
                            query_google_str += each_query
                        print(f"Google query: {query_google_str}")

                        urls_google = get_google_results(query_google_str)
                        async for each_url in urls_google:
                            each_id = uuid.uuid4().hex
                            message =  SourcesMessage(
                                keypoint_id=keypoint_id, source_id=each_id, data_source="Google",
                                query=query_google_str, content=each_url.url, title=each_url.title
                            )

                            each_dict = dataclasses.asdict(message)
                            await websocket.send_json(each_dict)

                        query_wiki = search_query_wikipedia_ollama(keypoint_text)
                        query_wiki_str = ""
                        async for each_query in query_wiki:
                            query_wiki_str += each_query
                        print(f"Wikipedia query: {query_wiki_str}")

                        urls_wiki = get_wiki_results(query_wiki_str)
                        async for each_url in urls_wiki:
                            each_id = uuid.uuid4().hex
                            message = SourcesMessage(
                                keypoint_id=keypoint_id, source_id=each_id, data_source="Wikipedia",
                                query=query_wiki_str, content=each_url.url, title=each_url.title
                            )

                            each_dict = dataclasses.asdict(message)
                            await websocket.send_json(each_dict)

                        stop_message = SourcesMessage(
                            stop=True, source_id="", keypoint_id=keypoint_id, data_source="", query=""
                        )
                        stop_dict = dataclasses.asdict(stop_message)
                        await websocket.send_json(stop_dict)

                    case "crosschecker":
                        # [x] Crosschecker Assistant
                        keypoint_id = html_content['keypoint_id']
                        keypoint_text = html_content['keypoint_text']
                        source_id = html_content['source_id']
                        source_uri = html_content['source_uri']
                        data_source = html_content['data_source']
                        async for segment in self.get_matches(
                            instance_id, keypoint_id, keypoint_text, source_id, source_uri
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
                            content=f"unknown message type {message_type}, len {len(html_content)}")
                        each_dict = dataclasses.asdict(message_segment)
                        await websocket.send_json(each_dict)

            except WebSocketDisconnect as e:
                logger.error(f"websocket disconnected: {e}")


app.mount("/static", StaticFiles(directory="static"), name="static")

def upgrade_pip() -> None:
    os.system("pip install --upgrade pip")

def install_pip_requirements() -> None:
    os.system("pip install -r requirements.txt")

def install_playwright() -> None:
    # os.system("sudo apt-get install libxcursor1 libxdamage1 libgtk-3-0 libpangocairo-1.0-0 libpango-1.0-0 libatk1.0-0 libcairo-gobject2 libcairo2 libgdk-pixbuf-2.0-0 libasound2 libdbus-glib-1-2")
    os.system("playwright install")


def main() -> None:
    # run `curl -fsSL https://ollama.com/install.sh | sh`
    #os.system("curl -fsSL https://ollama.com/install.sh | sh")

    # run `python -m spacy download de_core_news_lg`  # 568 MB model
    #os.system("python -m spacy download de_core_news_lg")

    upgrade_pip()
    install_pip_requirements()
    install_playwright()

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


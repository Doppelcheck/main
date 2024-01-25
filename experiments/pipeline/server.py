import asyncio
import dataclasses
import json
from dataclasses import dataclass
from typing import Generator, Callable
from urllib.parse import urlparse

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from nicegui import ui, app, Client

from fastapi.middleware.cors import CORSMiddleware

from experiments.pipeline.tools.prompt_openai_chunks import PromptOpenAI
from src.tools.bookmarklet import compile_bookmarklet

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@dataclass
class MessageSegment:
    segment: str
    last_segment: bool
    last_message: bool


@dataclass
class ClaimSegment(MessageSegment):
    purpose: str = "extract"


@dataclass
class DocumentSegment(MessageSegment):
    claim_id: int
    purpose: str = "retrieve"


@dataclass
class ComparisonSegment(MessageSegment):
    purpose: str = "compare"


class Server:
    @staticmethod
    async def get_address(client: Client) -> str:
        await client.connected()
        js_url = await ui.run_javascript('window.location.href')
        parsed_url = urlparse(js_url)
        return parsed_url.netloc

    @staticmethod
    async def set_local_storage(client: Client, key: str, value: any) -> None:
        await client.connected()
        _ = ui.run_javascript(f'localStorage.setItem("{key}", "{value}")')

    @staticmethod
    async def send_iframe_message(client: Client, settings: str) -> None:
        await client.connected()
        _ = ui.run_javascript(f'IFrameCommunication.sendSettings("{settings}");')

    @staticmethod
    async def get_iframe_message(client: Client) -> str:
        await client.connected()
        settings = await ui.run_javascript('IFrameCommunication.getSettings();')
        return settings

    @staticmethod
    async def get_local_storage(client: Client, key: str, default: any = None) -> any:
        await client.connected()
        value = await ui.run_javascript(f'localStorage.getItem("{key}")')
        if value is None:
            return default
        return value

    def __init__(self, agent_interface: dict[str, any]) -> None:
        self.llm_interface = PromptOpenAI(agent_interface)

    async def get_claims(self, body_html: str) -> Generator[ClaimSegment, None, None]:
        for i in range(5):
            text = f"Claim {i}, ({len(body_html)})"
            last_claim = i >= 4
            for j, each_character in enumerate(text):
                await asyncio.sleep(.1)
                last_segment = j >= len(text) - 1
                message_segment = ClaimSegment(each_character, last_segment, last_claim)
                yield message_segment

    async def get_documents(self, claim_id: int, claim_text: str) -> Generator[DocumentSegment, None, None]:
        # retrieve documents from claim_text

        for i in range(5):
            text = f"Document {i}, (id {claim_id})"
            last_document = i >= 4
            for j, each_character in enumerate(text):
                await asyncio.sleep(.1)
                last_segment = j >= len(text) - 1
                message_segment = DocumentSegment(each_character, last_segment, last_document, claim_id)
                yield message_segment

    async def get_comparisons(self, claim_id: int, claim: str, document_uri: str) -> Generator[ComparisonSegment, None, None]:
        for i in range(5):
            text = f"Comparison {i}, ({document_uri} vs {claim_id})"
            last_comparison = i >= 4
            for j, each_character in enumerate(text):
                await asyncio.sleep(.1)
                last_segment = j >= len(text) - 1
                message_segment = ComparisonSegment(each_character, last_segment, last_comparison)
                yield message_segment

    async def stream_from_llm(self, websocket: WebSocket, data: str, purpose: str) -> None:
        response = self.llm_interface.stream_reply_to_prompt(data)
        async for each_chunk_dict in response:
            each_dict = {'purpose': purpose, 'data': each_chunk_dict}
            json_str = json.dumps(each_dict)
            await websocket.send_text(json_str)

    def setup_routes(self) -> None:
        claims = list[str]()

        # Serve 'index.html' at the root
        @ui.page("/websocket_test")
        def get():
            return FileResponse('static/index.html')

        @app.get("/htmx_test")
        async def htmx_test():
            # create div element and return html code
            return HTMLResponse("<div>Hello!</div>")

        @app.get("/helper")
        async def helper():
            return FileResponse('static/helper.html')

        @app.get("/dist")
        async def dist():
            return FileResponse('static/dist.html')

        @ui.page("/config")
        async def config(client: Client) -> None:
            ui.add_head_html(f"<script defer src='static/iframecommunication.js'></script>")
            await client.connected()

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
                    # await Server.set_local_storage(client, key, value)
                    await Server.send_iframe_message(client, value)
                    print(f"set {key} to {value}")
                    text_input.classes(remove="bg-warning ")

                update_timer(set_storage)

            # individual setting
            key_name = "name"
            label = "label"
            placeholder = "placeholder"
            last_value = await Server.get_local_storage(client, key_name)
            with ui.input(
                    label=label,
                    placeholder=placeholder,
                    value=f"{last_value}",
                    on_change=lambda event: delayed_set_storage(key_name, event.value),
            ) as text_input:
                text_input.classes(add="transition ease-out duration-500 ")
                text_input.classes(remove="bg-warning ")

        @ui.page("/")
        async def bookmarklet(client: Client) -> None:
            address = await Server.get_address(client)

            with open("static/bookmarklet.js") as file:
                bookmarklet_js = file.read()

            bookmarklet_js = bookmarklet_js.replace("localhost:8000", address)
            compiled_bookmarklet = compile_bookmarklet(bookmarklet_js)
            ui.link("test bookmarklet", target=compiled_bookmarklet)


        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            try:
                while True:
                    json_data = await websocket.receive_text()
                    data = json.loads(json_data)
                    message_id = data['id']
                    message_content = data['data']

                    response = self.llm_interface.stream_reply_to_prompt(message_content)
                    async for each_chunk_dict in response:
                        each_dict = {'id': message_id, 'data': each_chunk_dict}
                        json_str = json.dumps(each_dict)
                        await websocket.send_text(json_str)

                    break

            except WebSocketDisconnect as e:
                print(e)

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
                        async for segment in self.get_claims(data):
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
                        async for segment in self.get_comparisons(claim_id, claim_text, document_uri):
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

    server = Server(config["agent_interface"])
    server.setup_routes()

    ui.run(**nicegui_config)


if __name__ in {"__main__", "__mp_main__"}:
    main()

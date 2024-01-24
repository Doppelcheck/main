import asyncio
import dataclasses
import json
from dataclasses import dataclass
from typing import Generator
from urllib.parse import urlparse

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from nicegui import ui, app, Client

from experiments.pipeline.prompt_openai_chunks import PromptOpenAI
from fastapi.middleware.cors import CORSMiddleware

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
    async def get_address() -> str:
        js_url = await ui.run_javascript('window.location.href')
        parsed_url = urlparse(js_url)
        return parsed_url.netloc

    def __init__(self, agent_interface: dict[str, any]) -> None:
        self.llm_interface = PromptOpenAI(agent_interface)

    async def get_claims(self, body_html: str) -> Generator[ClaimSegment, None, None]:
        for i in range(10):
            text = f"Claim {i}, ({len(body_html)})"
            last_claim = i >= 9
            for j, each_character in enumerate(text):
                await asyncio.sleep(.1)
                last_segment = j >= len(text) - 1
                message_segment = ClaimSegment(each_character, last_segment, last_claim)
                yield message_segment

    async def get_documents(self, claim_id: int, claim_text: str) -> Generator[DocumentSegment, None, None]:
        # retrieve documents from claim_text

        for i in range(10):
            text = f"Document {i}, (id {claim_id})"
            last_document = i >= 9
            for j, each_character in enumerate(text):
                await asyncio.sleep(.1)
                last_segment = j >= len(text) - 1
                message_segment = DocumentSegment(each_character, last_segment, last_document, claim_id)
                yield message_segment

    async def get_comparisons(self, claim_id: int, claim: str, document_uri: str) -> Generator[ComparisonSegment, None, None]:
        for i in range(10):
            text = f"Comparison {i}, ({document_uri} vs {claim_id})"
            last_comparison = i >= 9
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
        @ui.page("/")
        def get():
            return FileResponse('static/index.html')

        @ui.page("/bookmarklet")
        async def bookmarklet(client: Client) -> None:
            await client.connected()
            address = await Server.get_address()

            with open("static/bookmarklet.js") as file:
                bookmarklet_js = file.read()

            bookmarklet_js = bookmarklet_js.replace("localhost:8000", address)
            compiled_bookmarklet = compile_bookmarklet(bookmarklet_js)
            ui.link("test bookmarklet", target=compiled_bookmarklet)

        @app.get("/htmx_test")
        async def htmx_test():
            # create div element and return html code
            return HTMLResponse("<div>Hello!</div>")

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

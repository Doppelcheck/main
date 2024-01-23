import json
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


class Server:
    def __init__(self, agent_interface: dict[str, any]) -> None:
        self.llm_interface = PromptOpenAI(agent_interface)

    @staticmethod
    async def get_address() -> str:
        js_url = await ui.run_javascript('window.location.href')
        parsed_url = urlparse(js_url)
        return parsed_url.netloc

    def setup_routes(self) -> None:
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

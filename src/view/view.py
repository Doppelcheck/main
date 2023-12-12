# coding=utf-8
from nicegui import ui, Client, app
from pydantic import BaseModel

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from src.dataobjects import ViewCallbacks
from src.tools.bookmarklet import insert_server_address, compile_bookmarklet
from src.view.dummies import DummyContent


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


class Source(BaseModel):
    url: str
    text: str | None = None


class View:
    def __init__(self, bookmarklet_template: str) -> None:
        self.bookmarklet_template = bookmarklet_template
        self.callbacks: ViewCallbacks | None = None
        app.add_static_files(url_path="/assets", local_directory="assets")

        self._source = None

    def set_callbacks(self, callback: ViewCallbacks) -> None:
        self.callbacks = callback

    def setup_routes(self) -> None:
        @ui.page("/")
        async def index_page(client: Client) -> None:
            server_ips = list(app.urls)
            bookmarklet_js = insert_server_address(self.bookmarklet_template, server_ips[0])
            compiled_bookmarklet = compile_bookmarklet(bookmarklet_js)

            with ui.element("div") as container:
                container.style(
                    "width: 800px;"
                    "margin: 0 auto;"
                )

                logo = ui.image("assets/images/logo_big.svg")
                logo.style(
                    "width: 100%;"
                )

                ui.element("div").style("height: 100px;")

                with ui.element("div") as non_local:
                    ui.markdown("Zieh diesen Link in deine Lesezeichenleiste:")
                    # 🧐 👁️‍🗨️ 👁 ⚆
                    local_bookmarklet = ui.link("🧐 Doppelcheck", target=compiled_bookmarklet)
                    local_bookmarklet.style(
                        "font-size: 1.5em; "
                    )

                # dummy_content = DummyContent(client, self.callbacks)
                # await dummy_content.create_content()

        @app.post("/pass_source/")
        async def pass_source(source: Source) -> Response:
            self._source = source
            target_url = "process"
            return JSONResponse(content={"redirect_to": target_url})

        @ui.page("/process")
        async def test_page(client: Client) -> None:
            ui.label("Test")
            ui.label(self._source.url)
            ui.label(self._source.text)

            # https://chat.openai.com/share/10ef04b0-d709-4edf-b918-57ba1fbc28f3
            """
            with ui.html(
                    f"<iframe src=\"{value}\"></iframe>"
            ) as iframe:
                pass

            with ui.element("iframe") as iframe:
                # iframe.style("width: 100%; height: 100%;")
                iframe.props(f"src = \"{value}\"")
            """
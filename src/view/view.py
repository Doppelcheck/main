# coding=utf-8
from nicegui import ui, Client, app
from pydantic import BaseModel

from fastapi.middleware.cors import CORSMiddleware

from src.dataobjects import ViewCallbacks
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
    def __init__(self, bookmarklet_target: str) -> None:
        self.bookmarklet_target = bookmarklet_target
        self.callbacks: ViewCallbacks | None = None
        app.add_static_files(url_path="/assets", local_directory="assets")

    def set_callbacks(self, callback: ViewCallbacks) -> None:
        self.callbacks = callback

    def setup_routes(self) -> None:
        @ui.page("/")
        async def index_page(client: Client) -> None:
            with ui.element("div") as container:
                container.style(
                    "width: 800px;"
                    "margin: 0 auto;"
                )

                logo = ui.image("assets/images/logo_big.svg")

                ui.element("div").style("height: 100px;")

                with ui.row() as row:
                    row.style(
                        "display: flex;"
                        "flex-direction: row;"
                        "justify-content: space-between;"
                    )
                    with ui.element("div") as non_local:
                        ui.markdown("**Kein** lokaler *Doppelcheck* Server:")
                        ui.markdown("Zieh diesen Link in deine Lesezeichenleiste:")
                        local_bookmarklet = ui.link("🧐 Doppelcheck", target=self.bookmarklet_target)
                        local_bookmarklet.style("font-size: 1.5em;")

                    # ui.element("div").style("height: 100px;")

                    with ui.element("div") as local:
                        ui.markdown("Lokaler *Doppelcheck* Server:")
                        local_server_input = ui.input("http://localhost/")
                        ui.markdown("Zieh diesen Link in deine Lesezeichenleiste:")
                        local_bookmarklet = ui.link("🧐 Doppelcheck", target="")
                        local_bookmarklet.style("font-size: 1.5em;")
                        local_bookmarklet.props("disabled")

                # dummy_content = DummyContent(client, self.callbacks)
                # await dummy_content.create_content()

        @ui.page("/api/{source}")
        async def process(source: str, value: str = "") -> None:
            if source == "selection":
                ui.label("Selection")
                ui.label(value)
            else:
                ui.label("URL")
                ui.label(value)
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
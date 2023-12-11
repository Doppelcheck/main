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
            ui.link("🧐 Doppelcheck", target=self.bookmarklet_target)
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

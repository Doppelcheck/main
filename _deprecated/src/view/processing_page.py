from nicegui import Client, ui

from _deprecated.src.dataobjects import ViewCallbacks
from _deprecated.src.view.content_class import ContentPage


class ProcessingPage(ContentPage):
    def __init__(self, client: Client, callbacks: ViewCallbacks):
        super().__init__(client, callbacks)

    async def _create_content(self) -> None:
        ui.label("test")


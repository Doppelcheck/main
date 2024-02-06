from nicegui import ui, Client

from _deprecated.src.dataobjects import ViewCallbacks
from _deprecated.src.view.content_class import ContentPage


class DummyContent(ContentPage):
    def __init__(self, client: Client, callbacks: ViewCallbacks) -> None:
        super().__init__(client, callbacks)

    async def create_content(self) -> None:
        ui.label("Dummy content")

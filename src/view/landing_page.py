from nicegui import ui, app, Client

from src.dataobjects import ViewCallbacks
from src.tools.bookmarklet import insert_server_address, compile_bookmarklet
from src.view.content_class import ContentPage


class LandingPage(ContentPage):
    def __init__(self, client: Client, callbacks: ViewCallbacks):
        super().__init__(client, callbacks)

    async def _create_content(self):
        await self.client.connected()

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

            with ui.element("div") as main:
                ui.markdown("Coming soon...")

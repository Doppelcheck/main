from nicegui import ui, app, Client

from src.dataobjects import ViewCallbacks
from src.tools.bookmarklet import insert_server_address, compile_bookmarklet
from src.view.content_class import ContentPage


class ProcessingPage(ContentPage):
    def __init__(self, client: Client, callbacks: ViewCallbacks):
        super().__init__(client, callbacks)
        self.source = None

    async def _create_content(self):
        ui.label("Test")
        ui.label(str(self.source))

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


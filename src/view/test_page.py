from typing import Callable
from urllib.parse import urlparse

from nicegui import ui, app, Client

from src.dataobjects import ViewCallbacks, Source
from src.tools.bookmarklet import insert_server_address, compile_bookmarklet
from src.view.content_class import ContentPage


class TestPage(ContentPage):
    def __init__(self, client: Client, callbacks: ViewCallbacks):
        super().__init__(client, callbacks)
        self.bookmarklet_template = None
        self.manual_process: Callable[[Source], None] | None = None

    async def _create_content(self):
        server_ips = list(app.urls)

        js_url = await ui.run_javascript('window.location.href')
        ui.label(f"Server IPs from nicegui: {server_ips}")
        parsed_url = urlparse(js_url)
        domain = f"{parsed_url.scheme}://{parsed_url.netloc}/"
        ui.label(f"JS URL: {domain}")

        bookmarklet_js = insert_server_address(self.bookmarklet_template, domain)
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

            with ui.element("div") as main:
                ui.markdown("Zieh diesen Link in deine Lesezeichenleiste:")
                # 🧐 👁️‍🗨️ 👁 ⚆
                local_bookmarklet = ui.link("🧐 Doppelcheck", target=compiled_bookmarklet)
                local_bookmarklet.style(
                    "font-size: 1.5em; "
                )

                ui.element("div").style("height: 100px;")

                ui.markdown("Oder füge hier Deinen den Text ein:")
                text = ui.textarea()
                button = ui.button("🧐 Doppelcheck", on_click=lambda: self.manual_process(text.value))


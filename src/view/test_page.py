import os
import random
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

        with (ui.element("div") as container):
            container.style(
                "width: 800px;"
                "margin: 0 auto;"
            )

            logo = ui.image("assets/images/logo_big.svg")
            logo.style(
                "width: 100%;"
            )

            ui.element("div").style("height: 100px;")

            def add():
                item = os.urandom(10 // 2).hex()
                table.add_rows({'name': item, 'endpoint': random.randint(0, 100)})

            # https://nicegui.io/documentation/aggrid
            # https://nicegui.io/documentation/table
            # https://chat.openai.com/c/d039f978-0c6b-4657-b407-499b9901f97a
            # https://chat.openai.com/c/7cf93826-efdf-4255-b705-ffb28eb945c0
            with ui.expansion("Interfaces") as interfaces:
                columns = [
                    {'name': 'name', 'label': 'Name', 'field': 'name'},
                    {'name': 'endpoint', 'label': 'Endpoint', 'field': 'endpoint'},
                ]
                table = ui.table(columns=columns, rows=list(), row_key='name')
                # table.classes('w-full')
                table.style("width: 100%;")
                with ui.row() as buttons:
                    ui.button('add', on_click=add)
                    ui.button('edit')
                    ui.button('remove')

            with ui.expansion("Agents") as agents:
                ui.markdown("Keypoint Assistant")
                ui.markdown("Sourcefinder Assistant")
                ui.markdown("Crosschecker Assistant")

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


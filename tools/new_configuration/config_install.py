import base64

from nicegui import ui

from tools.text_processing import compile_bookmarklet


def get_section(
        userid: str, address: str, version: str,
        video: bool = True, title: bool = True) -> None:

    with open("static/bookmarklet.js", mode="r") as file:
        bookmarklet_js = file.read()

    with open("static/main-content.css", mode="r") as file:
        main_content_style_css = file.read()

    with open("static/sidebar.css", mode="r") as file:
        sidebar_style = file.read()

    with open("static/sidebar-content.css", mode="r") as file:
        sidebar_content_style = file.read()

    bookmarklet_js = bookmarklet_js.replace("[localhost:8000]", address)
    bookmarklet_js = bookmarklet_js.replace("[unique user identification]", userid)
    bookmarklet_js = bookmarklet_js.replace("[version number]", version)
    bookmarklet_js = bookmarklet_js.replace("[main content style]", main_content_style_css)
    bookmarklet_js = bookmarklet_js.replace("[sidebar style]", sidebar_style)
    bookmarklet_js = bookmarklet_js.replace("[sidebar content style]", sidebar_content_style)

    with open("static/images/android-chrome-512x512.png", mode="rb") as file:
        favicon_data = file.read()
        favicon_base64_encoded = base64.b64encode(favicon_data)
        favicon_base64_str = f"data:image/png;base64,{favicon_base64_encoded.decode('utf-8')}"

    compiled_bookmarklet = compile_bookmarklet(bookmarklet_js)
    # todo:
    #   see max width here: https://tailwindcss.com/docs/max-width

    if title:
        logo = ui.image("static/images/logo_big.svg")
        logo.classes(add="w-full")

        ui.element("div").classes(add="h-8")

    ui.element("div").classes(add="h-8")

    link_html = (
        f'Drag <a href="{compiled_bookmarklet}" id="doppelcheck-bookmarklet-name" class="bg-blue-500 '
        f'hover:bg-blue-700 text-white font-bold py-2 px-4 mx-2 rounded inline-block" onclick="return false;" '
        f'icon="{favicon_base64_str}">'
        f'🔍 Doppelcheck 🔎</a> to your bookmarks to use it on any website.'
    )
    # ⦾ 👁️ 🤨 🧐
    with ui.html(link_html) as bookmarklet_text:
        bookmarklet_text.classes(add="w-full text-center")

    if video:
        with ui.element("div") as spacer:
            spacer.classes(add="h-8")

        with ui.video(
                "static/videos/installation.webm",
                autoplay=True, loop=True, muted=True, controls=False) as video:
            video.classes(add="w-full max-w-2xl m-auto")

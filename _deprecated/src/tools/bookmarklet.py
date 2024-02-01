import urllib.parse as parse


def get_bookmarklet_template() -> str:
    input_file = "assets/js/bookmarklet.js"

    with open(input_file, mode="r") as f:
        return f.read()


def insert_server_address(js_template: str, server_address: str) -> str:
    return js_template.replace("https://localhost:8000/", server_address.removesuffix("/") + "/")


def compile_bookmarklet(js: str) -> str:
    return "javascript:void%20function(){" + parse.quote(js) + "}();"

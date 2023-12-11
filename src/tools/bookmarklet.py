import urllib.parse as parse


def compile_bookmarklet() -> str:
    input_file = "assets/js/bookmarklet.js"

    with open(input_file, mode="r") as f:
        data = f.read()
        encoded_data = parse.quote(data)

    # 🧐 👁️‍🗨️ 👁 ⚆
    # f.write("<a href=\"javascript:void%20function(){" + encoded_data + "}();\"> 🧐 Doppelcheck</a>")
    return "javascript:void%20function(){" + encoded_data + "}();"


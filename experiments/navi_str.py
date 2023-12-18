from __future__ import annotations
import requests
from lxml import etree
from typing import Generator


class SliceCombinationException(Exception):
    pass


class XpathSlice:
    _order = 0

    def __init__(self, xpaths: tuple[str], texts: tuple[str]) -> None:
        self._order = XpathSlice._order
        XpathSlice._order += 1
        self.xpaths = xpaths
        self.texts = texts

    @property
    def order(self) -> int:
        return self._order

    def get_text(self) -> str:
        return " ".join(x.strip() for x in self.texts)

    def __str__(self) -> str:
        return f"{self._order:03d} {self.get_text()} {str(self.xpaths)}"


EXCLUDED_TAGS = {
    "script", "style", "meta", "link", "br", "hr", "img",
    "input", "button", "select", "option", "form", "iframe",
    "head", "title", "noscript", "area", "map", "nav", "footer", "header"
}


def is_excluded(node: etree._Element) -> bool:
    """Check if any node in the absolute path is in EXCLUDED_TAGS"""
    if node.tag in EXCLUDED_TAGS or node.tag == etree.Comment:  # Skip comments
        return True
    parent = node.getparent()
    while parent is not None:
        if parent.tag in EXCLUDED_TAGS:
            return True
        parent = parent.getparent()
    return False


def get_text_xpaths(root: etree._Element) -> Generator[tuple[str, str], None, None]:
    """Recursively yield text nodes that are not purely whitespace."""
    root_tree = root.getroottree()
    for node in root.iter():
        if is_excluded(node):
            continue

        if node.text and node.text.strip():
            yield node.text, root_tree.getpath(node)

        if node.tail and node.tail.strip():
            yield node.tail, root_tree.getpath(node)


def index_html_new(html_content: str, max_length: int = 40) -> Generator[XpathSlice, None, None]:
    parser = etree.HTMLParser()
    tree = etree.fromstring(html_content, parser=parser)

    line_xpaths = list[str]()
    line_texts = list[str]()

    for node_text, xpath in get_text_xpaths(tree):
        len_node = len(node_text)  # todo: just `len(node_text.strip())`?
        len_line = sum(map(len, line_texts))

        while len_line + len_node >= max_length:
            slice_index = max_length - len_line

            node_front_slice = node_text[:slice_index]
            line_xpaths.append(xpath)
            line_texts.append(node_front_slice)
            yield XpathSlice(tuple(line_xpaths), tuple(line_texts))

            line_xpaths.clear()
            line_texts.clear()

            len_node -= slice_index
            if 0 >= len_node:
                break

            len_line = 0
            node_text = node_text[slice_index:]

        if len_line + len_node < max_length:
            line_xpaths.append(xpath)
            line_texts.append(node_text)
            continue

    if len(line_xpaths) > 0:
        yield XpathSlice(tuple(line_xpaths), tuple(line_texts))


def main() -> None:
    url = "https://www.tagesschau.de/ausland/europa/eu-gipfel-blcokade-ungarn-100.html"

    response = requests.get(url)
    html_text = response.text

    text_slices = index_html_new(html_text, 20)

    for each_xslice in text_slices:
        print(each_xslice)


if __name__ == "__main__":
    main()

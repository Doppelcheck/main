from __future__ import annotations
import requests
from lxml import etree
from typing import Generator


class SliceCombinationException(Exception):
    pass


class XpathSlice:
    _order = 0

    def __init__(self, xpaths: list[str], texts: list[str], finished: bool) -> None:
        self._order = XpathSlice._order
        XpathSlice._order += 1
        self.xpaths = xpaths
        self.texts = texts
        self.finished = finished

    @property
    def order(self) -> int:
        return self._order

    def __str__(self) -> str:
        return f"{self._order:03d}"


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


def get_text_nodes(root: etree._Element) -> Generator[tuple[str, etree._Element], None, None]:
    """Recursively yield text nodes that are not purely whitespace."""
    for node in root.iter():
        if is_excluded(node):
            continue

        if node.text and node.text.strip():
            yield node.text.strip(), node


def index_html(html_content: str, min_length: int = 20, max_length: int = 50) -> list[tuple[XpathSlice, str]]:
    parser = etree.HTMLParser()
    tree = etree.fromstring(html_content, parser=parser)
    xpath_slices = list()
    current_slice_text = ""
    current_xpaths = list()
    current_texts = list()

    for text, node in get_text_nodes(tree):
        current_text = text
        node_xpath = node.getroottree().getpath(node)

        while current_text:
            additional_text = current_text[:max_length - len(current_slice_text)]
            if len(current_xpaths) >= 1:
                current_slice_text += " "

            current_slice_text += additional_text
            current_xpaths.append(node_xpath)
            current_texts.append(current_text)
            current_text = current_text[len(additional_text):]

            if len(current_slice_text) >= min_length:
                is_last_slice = len(current_text) == 0
                xpath_slice = XpathSlice(xpaths=current_xpaths, texts=current_texts, finished=is_last_slice)
                xpath_slices.append((xpath_slice, current_slice_text))
                current_slice_text = ""
                current_xpaths = list()
                current_texts = list()

    return xpath_slices


def main() -> None:
    url = "https://www.tagesschau.de/ausland/europa/eu-gipfel-blcokade-ungarn-100.html"

    response = requests.get(url)
    html_text = response.text

    texts_with_paths = index_html(html_text)

    for each_xpath, each_text in texts_with_paths:
        print(each_xpath.xpaths)
        reference = f"{each_xpath.order}\n{each_text}\n"
        print(reference)


if __name__ == "__main__":
    main()

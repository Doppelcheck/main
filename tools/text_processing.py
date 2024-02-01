import dataclasses
import re
import string
from typing import Generator, Iterable, AsyncGenerator, Callable
from urllib import parse

from lxml import etree
from lxml.etree import _Element


EXCLUDED_TAGS = {
    "script", "style", "meta", "link", "br", "hr", "img",
    "input", "button", "select", "option", "form", "iframe",
    "head", "title", "noscript", "area", "map", "nav", "footer", "header"
}

EXCLUDED_IDS = {
    "doppelcheck-sidebar"
}


def is_excluded(node: _Element) -> bool:
    """Check if any node in the absolute path is in EXCLUDED_TAGS"""
    if node.tag in EXCLUDED_TAGS or node.get("id") in EXCLUDED_IDS or node.tag == etree.Comment:  # Skip comments
        return True

    parent = node.getparent()
    while parent is not None:
        if parent.tag in EXCLUDED_TAGS:
            return True
        parent = parent.getparent()
    return False


def text_node_generator(html_content: str) -> Generator[str, None, None]:
    parser = etree.HTMLParser()
    tree = etree.fromstring(html_content, parser=parser)

    for node in tree.iter():
        if is_excluded(node):
            continue

        if node.text:
            yield node.text

        if node.tail:
            yield node.tail


def replace_whitespace(text: str) -> str:
    """Replace multiple whitespaces in the text with a single space."""
    return re.sub(r'\s+', ' ', text)


def get_text_lines(segment_generator: Iterable[str], line_length: int) -> Generator[str, None, None]:
    accumulated_line = ""

    for segment in segment_generator:
        accumulated_line += segment
        accumulated_line = replace_whitespace(accumulated_line)

        while len(accumulated_line) >= line_length:
            yield accumulated_line[:line_length]
            accumulated_line = accumulated_line[line_length:]

    if accumulated_line:
        yield accumulated_line


def lined_text(lines: Iterable[str]) -> str:
    numbered_lines = (f"{line_number+1:03d} {each_line}" for line_number, each_line in enumerate(lines))
    return "\n".join(numbered_lines)


def get_range(range_str: str) -> tuple[int, int]:
    if "-" in range_str:
        from_str, to_str = range_str.strip().removesuffix(":").split("-")
        return int(from_str), int(to_str)

    only_digits = "".join(each_char for each_char in range_str if each_char in string.digits)
    from_line, to_line = int(only_digits), int(only_digits)
    return from_line, to_line


@dataclasses.dataclass(frozen=True)
class CodeBlockSegment:
    block_index: int
    block_type: str
    segment: str


async def pipe_codeblock_content[E](
        stream: AsyncGenerator[E, None], get_text: Callable[[E], str]) -> AsyncGenerator[CodeBlockSegment, None]:

    block_type = ""
    block_index = 0
    state = 0
    async for each_dict in stream:
        each_text = get_text(each_dict)
        if each_text is None:
            continue

        for each_char in each_text:
            if state == 0:
                block_type = ""
                if each_char == "`":
                    state = 1

            elif state == 1:
                state = 2 if each_char == "`" else 0

            elif state == 2:
                state = 3 if each_char == "`" else 0

            elif state == 3:
                if each_char == "\n":
                    state = 5
                else:
                    block_type += each_char
                    state = 4

            elif state == 4:
                if each_char == "\n":
                    state = 5
                else:
                    block_type += each_char

            elif state == 5:
                if each_char == "`":
                    state = 7
                else:
                    codeblock_segment = CodeBlockSegment(block_index, block_type, each_char)
                    yield codeblock_segment

            elif state == 7:
                if each_char == "`":
                    state = 9
                else:
                    codeblock_segment = CodeBlockSegment(block_index, block_type, "`" + each_char)
                    yield codeblock_segment
                    state = 5

            elif state == 9:
                if each_char == "`":
                    state = 11
                else:
                    codeblock_segment = CodeBlockSegment(block_index, block_type, "``" + each_char)
                    yield codeblock_segment
                    state = 5

            elif state == 11:
                if each_char == "\n":
                    state = 0
                    block_index += 1
                else:
                    codeblock_segment = CodeBlockSegment(block_index, block_type, "```" + each_char)
                    yield codeblock_segment
                    state = 5


def extract_code_block(text: str, code_type: str = "") -> str:
    """
    Extracts the first code block from a string using regular expressions.
    """
    pattern = r"```" + code_type + r"\n(.*?)\n```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        found_match = match.group(1)
        return found_match.removeprefix(f"```{code_type}").removeprefix("```").removesuffix("```").strip()
    return ""


def compile_bookmarklet(js: str) -> str:
    return "javascript:void%20function(){" + parse.quote(js) + "}();"
import re
from typing import Generator, Iterable
from lxml import etree
from lxml.etree import _Element

EXCLUDED_TAGS = {
    "script", "style", "meta", "link", "br", "hr", "img",
    "input", "button", "select", "option", "form", "iframe",
    "head", "title", "noscript", "area", "map", "nav", "footer", "header"
}


def is_excluded(node: _Element) -> bool:
    """Check if any node in the absolute path is in EXCLUDED_TAGS"""
    if node.tag in EXCLUDED_TAGS or node.tag == etree.Comment:  # Skip comments
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


def pipe_codeblock_content(text_str: Iterable[str]) -> Generator[tuple[int, str], None, None]:
    block_type = ""
    block_count = 0
    state = 0
    for each_segment in text_str:
        for each_char in each_segment:
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
                elif each_char == "`":
                    state = 7
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
                    yield block_count, block_type, each_char

            elif state == 7:
                if each_char == "`":
                    state = 9
                else:
                    yield block_count, block_type, "`" + each_char
                    state = 5

            elif state == 9:
                if each_char == "`":
                    state = 11
                else:
                    yield block_count, block_type, "``" + each_char
                    state = 5

            elif state == 11:
                if each_char == "\n":
                    state = 0
                    block_count += 1
                else:
                    yield block_count, block_type, "```" + each_char
                    state = 5


if __name__ == "__main__":
    test = """
Sure, here is an example string with multiple non-nested triple single quote fenced code blocks:

```python
print("This is a Python code block.")
```

asdfsdf

```javascript
console.log("This is a JavaScript code block.");
```


asdfasdf

```sql
SELECT * FROM users;
```


This string contains three code blocks, each delimited by triple single quotes. The first block is a Python code block, the second block is a JavaScript code block, and the third block is an SQL code block. The code blocks are not nested within each other, and there are no empty lines or other non-code content between the blocks.
    """

    g = (each_char for each_char in test)
    li = list()
    for each_content in pipe_codeblock_content(g):
        li += each_content[2]
        print(each_content)

    print("".join(li))

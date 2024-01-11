import re


def generate_block(text: str, block_type: str = "") -> str:
    return (
        f"```{block_type.strip()}\n"
        f"{text.strip()}\n"
        f"```\n"
        f"\n"
    )


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


def text_around(text: str, substring: str) -> tuple[str, str]:
    """
    Returns the text before the first occurrence of a substring.
    """
    prefix, _, suffix = text.partition(substring)
    return prefix, suffix

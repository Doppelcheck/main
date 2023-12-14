import re


def extract_code_block(text: str, code_type: str = "") -> str:
    """
    Extracts the first code block from a string using regular expressions.
    """
    pattern = r"```" + code_type + r"\n(.*?)\n```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""

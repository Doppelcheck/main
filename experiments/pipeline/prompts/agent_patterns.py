from typing import Iterable

import num2words

from experiments.pipeline.tools.text_processing import lined_text


def extraction(
        lines: Iterable[str],
        num_claims: int = 3, words_per_claim: int = 20, language: str | None = None
) -> str:

    num_claims_str = f"{num_claims:d}" \
        if num_claims >= 13 \
        else num2words.num2words(num_claims)

    words_per_claim_str = f"{words_per_claim:d}" \
        if words_per_claim >= 13 \
        else num2words.num2words(words_per_claim)

    language_instruction = f" Answer in {language}." if language else " Answer in the language of the text."

    numbered_text = lined_text(lines)

    return (
        f"```text\n"
        f"{numbered_text}\n"
        f"```\n"
        f"\n"
        f"Identify and extract the {num_claims_str} key claims from the text in the code block above. Exclude all "
        f"examples, questions, opinions, descriptions of personal feelings, prose, advertisements, and similar "
        f"non-factual content.\n"
        f"\n"
        f"Precisely reference an exclusive range of line numbers with each extracted claim. Provide a brief, clear, "
        f"and direct rephrasing of each key claim to convey its essential statement. Use only up to "
        f"{words_per_claim_str} words for each claim.\n"
        f"\n"
        f"Respond according to the following pattern:\n"
        f"```key_claims\n"
        f"<line start>-<line end>: <key_claim a>\n"
        f"015-027: <key_claim b>\n"
        f"056-081: <key_claim c>\n"
        f"[...]\n"
        f"```\n"
        f"\n"
        f"Answer in one triple single quote fenced code block with the keyword `key_claims` containing all "
        f"{num_claims_str} key claims. Ignore any text that is not part of the main topic.{language_instruction}"
    )

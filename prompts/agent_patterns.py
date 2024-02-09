from typing import Iterable

import num2words

from tools.text_processing import lined_text


def extraction(
        lines: Iterable[str], num_claims: int = 3, words_per_claim: int = 20, language: str | None = None) -> str:

    num_claims_str = f"{num_claims:d}" \
        if num_claims >= 13 \
        else num2words.num2words(num_claims)

    words_per_claim_str = f"{words_per_claim:d}" \
        if words_per_claim >= 13 \
        else num2words.num2words(words_per_claim)

    if language is None or language == "default":
        language_instruction = " Respond in the language of the text."
    else:
        language_instruction = f" Respond in {language}."

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
        f"```\n"
        f"<line start>-<line end>: <key_claim a>\n"
        f"015-027: <key_claim b>\n"
        f"056-081: <key_claim c>\n"
        f"[...]\n"
        f"```\n"
        f"\n"
        f"Answer in one triple single quote fenced code block containing all {num_claims_str} key claims. Ignore any "
        f"text that is not part of the main topic.{language_instruction}"
    )


def google(claim: str, context: str | None = None, language: str | None = None) -> str:
    context_data = (
        f"```context\n"
        f"{context}\n"
        f"```\n"
        f"\n"
    ) if context else ""

    context_instruction = (
        f" Refine your query according to the provided context."
    ) if context else ""

    language_instruction = f"Respond in {language}" if language else "Respond in the language of the claim"

    return (
        f"{context_data}"
        f"```claim\n"
        f"{claim}\n"
        f"```\n"
        f"\n"
        f"Generate the optimal Google search query to get results that allow for the verification of the claim "
        f"above.{context_instruction}\n"
        f"\n"
        f"Make use of special Google search operators to improve retrieval precision and recall. Do not restrict "
        f"the query to particular top-level domains like with `site:ru` or similar.\n"
        f"\n"
        f"IMPORTANT: Split up compound words.\n"
        f"\n"
        f"{language_instruction} and exactly and only with the search query requested in a fenced code block according "
        f"to the following pattern.\n"
        f"```\n"
        f"[query]\n"
        f"```\n"
    )


def compare(claim: str, text: str, language: str | None = None) -> str:
    if language is None:
        language_instruction = "the language of the claim"
    else:
        language_instruction = language

    return (
        f"Carefully read the following claim and text. Your task is to assess how well the text matches the claim.\n"
        f"\n"
        f"```claim\n"
        f"{claim}\n"
        f"```\n"
        f"\n"
        f"```text\n"
        f"{text}\n"
        f"```\n"
        f"\n"
        f"Assign a score based on the following scale:\n"
        f"  +2: The text strongly supports the claim\n"
        f"  +1: The text generally supports the claim, with some limitations or minor contradictions\n"
        f"   0: The text neither clearly supports nor contradicts the claim, or it's unclear\n"
        f"  -1: The text contradicts the claim but not completely\n"
        f"  -2: The text is in strong opposition to the claim\n"
        f"\n"
        f"IMPORTANT: Do not assess the correctness of the claim itself or of the text, determine only the semantic "
        f"match between claim and text!\n"
        f"\n"
        f"Also provide one sentence of explanation for your rating. Respond in {language_instruction} and answer with "
        f"a single triple single quote fenced code block according to the following pattern.\n"
        f"```\n"
        f"+1\n"
        f"<explanation>\n"
        f"```\n"
    )

from typing import Iterable

import num2words

from tools.text_processing import lined_text


def instruction_keypoint_extraction(
        lines: Iterable[str], num_keypoints: int = 3,
        customized_instruction: str | None = None, language: str | None = None) -> str:

    num_keypoints_str = f"{num_keypoints:d}" if num_keypoints >= 13 else num2words.num2words(num_keypoints)

    if language is None or language == "default":
        language_instruction = " Respond in the language of the text."
    else:
        language_instruction = f" Respond in {language}."

    numbered_text = lined_text(lines)

    customizable = customized_instruction or (
        "The text is a news report. Extract its key factual claims, converting any relative time and place references "
        "to their absolute counterparts. Exclude examples, questions, opinions, personal feelings, prose, "
        "advertisements, and other non-factual elements."
    )

    return (
        f"Read the following text carefully to extract the {num_keypoints_str} most important keypoints.\n"
        f"\n"
        f"```text\n"
        f"{numbered_text}\n"
        f"```\n"
        f"\n"
        f"{customizable}"
        f"\n"
        f"Precisely refer to an exclusive range of line numbers with each extracted keypoint. Provide a concise, clear, "
        f"and comprehensive rephrasing of each keypoint to convey its essence in one sentence.\n"
        f"\n"
        f"Respond according to the following pattern:\n"
        f"```\n"
        f"<line start>-<line end>: <keypoint a>\n"
        f"015-027: <keypoint b>\n"
        f"056-081: <keypoint c>\n"
        f"[...]\n"
        f"```\n"
        f"\n"
        f"Answer in one triple single quote fenced code block containing all {num_keypoints_str} keypoints. Ignore any "
        f"information that is not part of the main content.{language_instruction}"
    )


def instruction_crosschecking(
        claim: str, report: str, context: str | None = None,
        customized_instruction: str | None = None, language: str | None = None) -> str:

    if language is None or language == "default":
        language_instruction = "the language of the keypoint"
    else:
        language_instruction = language

    if context is None:
        context_data = ""
        context_instruction = ""
    else:
        context_data = (
            f"```context\n"
            f"{context}\n"
            f"```\n"
            f"\n"
        )
        context_instruction = " Treat the provided context like additional keypoint information."

    customizable = customized_instruction or (
        "The keypoint is a claim and the source reference is a news report. Now rate the claim based on the "
        "report by picking one of the following options:\n"
        "  \"🟩 Strong support\": report strongly supports claim\n"
        "  \"🟨 Some support\": report generally supports claim, with limitations or minor contradictions\n"
        "  \"⬜️ No mention\": report neither clearly supports nor contradicts claim, or is unclear\n"
        "  \"🟧​ Some contradiction\": report contradicts claim but not completely\n"
        "  \"🟥 Strong contradiction\": report is in strong opposition to claim\n"
        "\n"
        "IMPORTANT: Do not assess the correctness of either claim or report, determine your rating only based on how "
        "well the claim holds up against the news report.\n"
    )

    return (
        f"Carefully read the following information. Your task is to assess how well the keypoint matches "
        f"the information in the source.{context_instruction}\n"
        f"\n"
        f"{context_data}"
        f"```keypoint\n"
        f"{claim}\n"
        f"```\n"
        f"\n"
        f"```source\n"
        f"{report}\n"
        f"```\n"
        f"\n"
        f"{customizable}"
        f"\n"
        f"Also, in a new line, provide one concise but comprehensive sentence explaining your rating. "
        f"\n"
        f"Respond in {language_instruction} and answer with a single triple single quote fenced code block according "
        f"to the following pattern.\n"
        f"```\n"
        f"<rating>\n"
        f"<explanation>\n"
        f"```\n"
    )

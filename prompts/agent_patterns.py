from typing import Iterable

import num2words

from tools.text_processing import lined_text


def instruction_keypoint_extraction(lines: Iterable[str], customized_instruction: str,
                                    num_keypoints: int = 3, language: str | None = None) -> str:

    num_keypoints_str = f"{num_keypoints:d}" if num_keypoints >= 13 else num2words.num2words(num_keypoints)

    if language is None or language == "default":
        language_instruction = " Respond in the language of the text."
    else:
        language_instruction = f" Respond in {language}."

    numbered_text = lined_text(lines)

    return (
        f"Read the following text carefully to extract the {num_keypoints_str} most important "
        f"keypoint{'s' if num_keypoints >= 2 else ''}.\n"
        f"\n"
        f"```text\n"
        f"{numbered_text}\n"
        f"```\n"
        f"\n"
        f"{customized_instruction.strip()}\n"
        f"\n"
        f"Precisely refer to an exclusive range of line numbers with each extracted keypoint. Provide a concise, "
        f"clear, and rephrasing of each keypoint to convey its essence. Respond according to the following pattern:\n"
        f"```\n"
        f"<line start>-<line end>: <keypoint a>\n"
        f"0015-0027: <keypoint b>\n"
        f"0056-0081: <keypoint c>\n"
        f"[...]\n"
        f"```\n"
        f"\n"
        f"Answer in one triple single quote fenced code block containing exactly and only {num_keypoints_str} "
        f"keypoint{'s' if num_keypoints >= 2 else ''}. Ignore any information that is not part of the main content."
        f"{language_instruction}"
    )


def instruction_crosschecking(claim: str, report: str, customized_instruction: str,
                              language: str | None = None) -> str:

    if language is None or language == "default":
        language_instruction = "the language of the keypoint"
    else:
        language_instruction = language

    return (
        f"Carefully read the following information. Your task is to assess how well the keypoint matches "
        f"the information in the source.\n"
        f"\n"
        f"```keypoint\n"
        f"{claim}\n"
        f"```\n"
        f"\n"
        f"```source\n"
        f"{report}\n"
        f"```\n"
        f"\n"
        f"{customized_instruction}"
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

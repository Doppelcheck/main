from __future__ import annotations

import asyncio
from typing import Mapping

from ollama_instructor.ollama_instructor_client import OllamaInstructorClient
from ollama import AsyncClient
from pydantic import BaseModel


class Keypoints(BaseModel):
    """
    A summary of a line or a group of lines.
    """
    quote_line_number_start: int
    quote_line_number_end: int
    summary: str


class Summary(BaseModel):
    """
    Extracted lines and their summaries.
    """
    keypoints: list[Keypoints]


async def chat_stream() -> None:

    # OLLAMA_HOST=0.0.0.0:8800 OLLAMA_MODELS=~/.ollama/.models ollama serve

    # todo:
    #  catch context exceeded exception
    #  implement continual interactive summarization

    with open("prompts/lines_full.txt", mode="r") as f:
        lines = f.read()

    prompt = {
        'role': 'user',
        'content': (
            "```text\n"
            f"{lines}"
            "```\n"
            "\n"
            "Summarize the key points of the text above in this exact output format:\n"
            "```output\n"
            "["
            "   {"
            "       \"quote_line_number_start\": [line number here],\n"
            "       \"quote_line_number_end\": [line number here],\n"
            "       \"summary\": [summary of lines here, in quotes, with punctuation and capitalization as in the original text]\n"
            "   },\n"
            "   {"
            "       \"quote_line_number_start\": [line number here],\n"
            "       \"quote_line_number_end\": [line number here],\n"
            "       \"summary\": [summary of lines here, in quotes, with punctuation and capitalization as in the original text]\n"
            "   },\n"
            "   {"
            "       \"quote_line_number_start\": [line number here],\n"
            "       \"quote_line_number_end\": [line number here],\n"
            "       \"summary\": [summary of lines here, in quotes, with punctuation and capitalization as in the original text]\n"
            "   },\n"
            "   [...]\n"
            "]\n"
            "```\n"
            "\n"
            "The summary should be a list of dictionaries, each containing the keys `quote_line_number_start`, `quote_line_number_end`, and `summary`.\n"
        )
    }

    prompt = {
        'role': 'user',
        'content': (
            "```text\n"
            f"{lines}"
            "```\n"
            "\n"
            "Summarize the key points of the text above.\n"
        )
    }

    # model = 'llama2:text'
    # model = 'mistral'
    # model = "dolphin-mixtral"
    # model = "llama3"
    # model = "phi3"
    # model = "qwen2.5:0.5b"
    # model = "llama3.2"
    # model = "phi3.5"
    model = "qwen2.5"

    """
    client = OllamaInstructorClient()
    response = client.chat_completion_with_stream(
        model=model, messages=[prompt], pydantic_model=Summary
    )
    response_list = list(response)
    for each_keypoint in response_list:
        print(each_keypoint["message"]["content"])
        print()
        # print(f"lines {each_keypoint.quote_line_number_start:03d}-{each_keypoint.quote_line_number_end:03d}: {each_keypoint.summary}")
    """
    client = AsyncClient()  # host="http://localhost:8800")
    async for part in await client.chat(model=model, messages=[prompt], stream=True):
        message: Mapping[str, any] = part['message']
        content = message['content']
        print(content, end='', flush=True)


async def chat(client: AsyncClient, model: str, screen_content: str) -> str:
    prompt = {
        'role': 'user',
        'content': screen_content
    }

    response = await client.chat(model=model, messages=[prompt])
    response_txt = response['message']['content']
    return response_txt


async def main() -> None:
    await chat_stream()


if __name__ == "__main__":
    asyncio.run(main())

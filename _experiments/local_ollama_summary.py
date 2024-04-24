from __future__ import annotations

import asyncio
from typing import Mapping

from ollama import AsyncClient


async def chat_stream() -> None:

    # OLLAMA_HOST=0.0.0.0:8800 OLLAMA_MODELS=~/.ollama/.models ollama serve

    # todo:
    #  catch context exceeded exception
    #  implement continual interactive summarization

    client = AsyncClient(host="http://localhost:8800")

    with open("prompts/lines_full.txt", mode="r") as f:
        lines = f.read()

    prompt = {
        'role': 'user',
        'content': (
            "```text\n"
            f"{lines}"
            "```\n"
            "\n"
            "Extract the lines and summarize the key points of the text above.\n"
            "\n"
            "Use this exact output format:\n"
            "```output\n"
            "lines 002-004: The quick brown fox jumps over the lazy dog.\n"
            "lines 007-010: Horatio, I am thy father's spirit.\n"
            "lines 012-013: Life is but a walking shadow.\n"
            "```"
        )
    }

    # model = 'llama2:text'
    model = 'mistral'
    # model = "dolphin-mixtral"
    # model = "llama3"
    # model = "phi3"

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

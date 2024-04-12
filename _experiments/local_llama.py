from __future__ import annotations
from typing import Mapping

from ollama import AsyncClient


async def chat_stream():

    # OLLAMA_HOST=0.0.0.0:8800 OLLAMA_MODELS=~/.ollama/.models ollama serve

    # todo:
    #  catch context exceeded exception
    #  implement continual interactive summarization

    client = AsyncClient(host="http://localhost:8800")

    with open("prompts/extract_short.txt", mode="r") as f:
        prompt_content = f.read()

    prompt = {
        'role': 'user',
        'content': prompt_content
    }

    async for part in await client.chat(model='mistral', messages=[prompt], stream=True):
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

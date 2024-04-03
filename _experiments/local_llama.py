import asyncio
from typing import Mapping

from ollama import AsyncClient


async def chat():

    # OLLAMA_HOST=0.0.0.0:8800 OLLAMA_MODELS=~/.ollama/.models ollama serve

    client = AsyncClient(host="http://localhost:8800")

    prompt = {
        'role': 'user',
        'content': 'Why is the sky blue?'
    }

    async for part in await client.chat(model='mistral', messages=[prompt], stream=True):
        message: Mapping[str, any] = part['message']
        content = message['content']
        print(content, end='', flush=True)


asyncio.run(chat())

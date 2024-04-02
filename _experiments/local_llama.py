import asyncio
from ollama import AsyncClient


async def chat():
    message = {'role': 'user', 'content': 'Why is the sky blue?'}

    async for part in await AsyncClient(host="http://0.0.0.0:8800").chat(model='llama2', messages=[message], stream=True):
        print(part['message']['content'], end='', flush=True)


asyncio.run(chat())

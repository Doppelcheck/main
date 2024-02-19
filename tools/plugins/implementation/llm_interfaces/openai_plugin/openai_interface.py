import dataclasses
import time
from typing import AsyncGenerator, Callable

import openai
from loguru import logger
from openai.types.chat import ChatCompletionChunk

from tools.data_objects import ParametersOpenAi
from tools.plugins.abstract import InterfaceLLM


class PromptOpenAI(InterfaceLLM):
    def __init__(self, key: str) -> None:
        self._client = openai.AsyncOpenAI(api_key=key)

    async def reply_to_prompt(
            self, prompt: str,
            parameters: ParametersOpenAi,
            info_callback: Callable[[dict[str, any]], None] | None = None
    ) -> str:

        logger.info(prompt)

        arguments = dataclasses.asdict(parameters)

        reply = ""
        while True:
            try:
                messages = [{"role": "user", "content": prompt}]
                response = await self._client.chat.completions.create(messages=messages, **arguments)
                if info_callback is not None:
                    info_callback(response.model_dump(mode="json"))

                choice, = response.choices
                message = choice.message
                reply = message.content
                break

            except Exception as e:
                logger.error(e)
                time.sleep(1)
                continue

        logger.info(reply)
        return reply.strip()

    async def stream_reply_to_prompt(
            self, prompt: str,
            parameters: ParametersOpenAi,
            info_callback: Callable[[dict[str, any]], None] | None = None

    ) -> AsyncGenerator[str, None]:

        logger.info(prompt)

        arguments = dataclasses.asdict(parameters)

        try:
            messages = [{"role": "user", "content": prompt}]
            response = await self._client.chat.completions.create(messages=messages, **arguments, stream=True)
            async for each_chunk in response:
                each_chunk: ChatCompletionChunk
                logger.info(each_chunk)
                if info_callback is not None:
                    info_callback(each_chunk.model_dump(mode="json"))

                stream_chunk = each_chunk.choices[0].delta.content
                yield stream_chunk

        except Exception as e:
            logger.error(e)

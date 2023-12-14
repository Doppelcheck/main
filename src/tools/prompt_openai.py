import time

import openai
from loguru import logger


class PromptOpenAI:
    def __init__(self, config: dict[str, any]) -> None:
        self._client = openai.AsyncOpenAI(api_key=config.pop("key"))
        self._config = config.pop("parameters")

    async def reply_to_prompt(self, prompt: str, **kwargs: any) -> str:
        arguments = dict(self._config)
        arguments.update(kwargs)

        reply = ""
        while True:
            try:
                messages = [{"role": "user", "content": prompt}]
                response = await self._client.chat.completions.create(messages=messages, **arguments)
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

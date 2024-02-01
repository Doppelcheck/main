import time
from typing import Generator

import openai
from loguru import logger


class PromptOpenAI:
    @staticmethod
    def chunk_text(text: str, max_len: int = 1_000, overlap: int = 100) -> Generator[str, None, None]:
        len_text = len(text)
        start = 0
        end = max_len
        while True:
            if end >= len_text:
                yield text[start:]
                break
            yield text[start:end]
            start += max_len - overlap
            end += max_len - overlap

    def __init__(self, config: dict[str, any]) -> None:
        self._client = openai.AsyncOpenAI(api_key=config["key"])
        self._config = config["parameters"]

    async def summarize(self, text: str, max_len_input: int = 10_000, max_len_summary: int = 500) -> str:
        len_text = len(text)
        if len_text < max_len_summary:
            return text

        summaries = list()
        for each_chunk in self.chunk_text(text, max_len=max_len_input):
            summary = await self.summarize(each_chunk, max_len_input=max_len_input, max_len_summary=max_len_summary)
            summaries.append(summary)
        text = "\n".join(summaries)

        prompt = (
            f"```text\n"
            f"{text}\n"
            f"```\n"
            f"\n"
            f"Summarize the text above in about {max_len_summary} characters keeping its original language."
        )
        response = await self.reply_to_prompt(prompt)
        return response

    async def reply_to_prompt(self, prompt: str, **kwargs: any) -> str:
        logger.info(prompt)

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

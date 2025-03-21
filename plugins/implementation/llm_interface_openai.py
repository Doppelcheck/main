from __future__ import annotations

import asyncio

from nicegui import ui

import time
from typing import AsyncGenerator, Callable

import openai
from loguru import logger

from plugins.abstract import InterfaceLLM, Parameters, InterfaceLLMConfig, DictSerializableImplementation, \
    DictSerializable, ConfigurationCallbacks
from tools.text_processing import chunk_text


class ContextExceededError(Exception):
    pass


class OpenAi(InterfaceLLM):
    async def summarize(
            self, text: str, parameters: Parameters | None = None, len_summary: int = 100_000, manual_limit: int = -1
    ) -> str:
        len_text = len(text)
        if len_summary >= len_text:
            return text

        try:
            prompt = (
                f"```text\n"
                f"{text}\n"
                f"```\n"
                f"\n"
                f"Summarize the text above with less than {len_summary} characters. Remove all redundancies and "
                f"repetitions. IMPORTANT: Keep its original language, tone, style, and perspective!"
            )
            if -1 < manual_limit < len(prompt):
                raise ContextExceededError("Manual limit exceeded.")

            response = await self.reply_to_prompt(prompt, parameters)

        except ContextExceededError as e:
            logger.warning("context exceeded", e)
            chunks = chunk_text(text, len_chunks=len_text // 2, overlap=len_summary // 10)
            tasks = [
                self.summarize(each_chunk, parameters=parameters, len_summary=len_summary)
                for each_chunk in chunks
            ]

            summaries = await asyncio.gather(*tasks)
            concatenated_summaries = "\n".join(summaries)
            if len_summary >= len(concatenated_summaries):
                return concatenated_summaries

            response = await self.summarize(concatenated_summaries, parameters=parameters, len_summary=len_summary)
            if len(response) >= len_summary:
                logger.warning(f"Summarized text is too long: {len(response)} characters.")

        return response[:len_summary]

    @staticmethod
    def name() -> str:
        return "OpenAI"

    class ConfigParameters(Parameters):
        @classmethod
        def from_state(cls, state: dict[str, any]) -> OpenAi.ConfigParameters:
            return OpenAi.ConfigParameters(**state)

        def __init__(
                self, model: str = "gpt-4-1106-preview", frequency_penalty: float = 0,
                logit_bias: dict[int, float] | None = None, max_tokens: int | None = None,
                presence_penalty: float = 0, temperature: float = 0, top_p: float | None = None,
                user: str | None = None,
                **kwargs: any  # discard the rest
        ) -> None:
            # https://platform.openai.com/docs/api-reference/chat/create
            self.model = model
            self.frequency_penalty = frequency_penalty
            self.logit_bias = logit_bias
            # self.logprobs: bool = False
            # self.top_logprobs: int | None = None
            self.max_tokens = max_tokens
            # self.n: int = 1
            self.presence_penalty = presence_penalty
            # self.response_format: dict[str, str] | None = None
            # self.seed: int | None = None
            # self.stop: str | list[str] | None = None
            self.temperature = temperature
            self.top_p = top_p
            # self.tools: list[str] = None
            self.user = user

    class ConfigInterface(InterfaceLLMConfig):
        @classmethod
        def from_state(cls, state: dict[str, any]) -> DictSerializableImplementation:
            parameters = DictSerializable.from_object_dict(state["parameters"])
            return OpenAi.ConfigInterface(
                name=state["name"], parameters=parameters, from_admin=state["from_admin"], api_key=state["api_key"]
            )

        def object_to_state(self) -> dict[str, any]:
            return {
                "name": self.name,
                "parameters": self.parameters.to_object_dict(),
                "from_admin": self.from_admin,
                "api_key": self.api_key
            }

        @staticmethod
        def _from_dict(state: dict[str, any]) -> DictSerializableImplementation:
            return OpenAi.ConfigInterface(**state)

        def __init__(self, name: str, parameters: OpenAi.ConfigParameters, from_admin: bool, api_key: str) -> None:
            super().__init__(name, from_admin)
            self.parameters = parameters
            self.api_key = api_key

    @staticmethod
    def configuration(instance_id: str, user_accessible: bool) -> ConfigurationCallbacks:
        def _reset_parameters() -> None:
            api_key_input.value = ""
            default_parameters = OpenAi.ConfigParameters()
            editor.run_editor_method("set", {"json": default_parameters.object_to_state()})

        async def _get_config() -> OpenAi.ConfigInterface:
            logger.info(f"adding LLM interface: {instance_id}")

            editor_content = await editor.run_editor_method("get")
            json_content = editor_content['json']

            parameters = OpenAi.ConfigParameters(**json_content)
            new_interface = OpenAi.ConfigInterface(
                name="", parameters=parameters, from_admin=instance_id is None, api_key=api_key_input.value
            )
            _reset_parameters()
            return new_interface

        with ui.input(
                label="OpenAI API Key", placeholder="\"sk-\" + alphanumeric characters",
                validation={
                    "Must start with \"sk-\"": lambda v: v.startswith("sk-"),
                    "Must be 51 or 164 characters long": lambda v: len(v) == 51 or len(v) == 164
                }
        ) as api_key_input:
            api_key_input.classes('w-full')
        _default = OpenAi.ConfigParameters()
        with ui.json_editor({"content": {"json": _default.object_to_state()}}) as editor:
            editor.classes('w-full')

        with ui.markdown(
                "Go <a href=\"https://platform.openai.com/docs/api-reference/chat/create\" "
                "target=\"_blank\">here</a> for a detailed documentation."
        ) as description:
            description.classes('w-full')

        with ui.markdown(
                "The following OpenAI API parameters have been disabled for compatibility: `stream`, `messages`, "
                "`logprobs`, `top_logprobs`, `n`, `response_format`, `seed`, `stop`, and `tools`."
        ) as _:
            pass

        return ConfigurationCallbacks(reset=_reset_parameters, get_config=_get_config)

    @classmethod
    def from_state(cls, state: dict[str, any]) -> DictSerializableImplementation:
        parameters = DictSerializable.from_object_dict(state["parameters"])
        return OpenAi(
            name=state["name"], parameters=parameters, from_admin=state["from_admin"], api_key=state["api_key"]
        )

    def __init__(self, name: str, parameters: Parameters, from_admin: bool, api_key: str) -> None:
        super().__init__(name, parameters, from_admin)
        self._key = api_key
        self._client = openai.AsyncOpenAI(api_key=api_key)

    async def reply_to_prompt(self, prompt: str, info_callback: Callable[[dict[str, any]], None] | None = None) -> str:
        logger.info(prompt)
        arguments = {k: v for k, v in self.parameters.object_to_state().items() if v is not None}
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

            except openai.BadRequestError as e:
                if e.code == 'context_length_exceeded':
                    raise ContextExceededError() from e

            except Exception as e:
                logger.error(e)
                time.sleep(1)
                continue

        logger.info(reply)
        return reply.strip()

    async def stream_reply_to_prompt(
            self, prompt: str,
            info_callback: Callable[[dict[str, any]], None] | None = None
    ) -> AsyncGenerator[str, None]:

        logger.info(prompt)

        arguments = {k: v for k, v in self.parameters.object_to_state().items() if v is not None}

        try:
            messages = [{"role": "user", "content": prompt}]
            response = await self._client.chat.completions.create(messages=messages, **arguments, stream=True)
            async for each_chunk in response:
                logger.info(each_chunk)
                if info_callback is not None:
                    info_callback(each_chunk.model_dump(mode="json"))

                stream_chunk = each_chunk.choices[0].delta.content
                yield stream_chunk

        except openai.BadRequestError as e:
            if e.code == 'context_length_exceeded':
                raise ContextExceededError() from e

        except Exception as e:
            logger.error(e)

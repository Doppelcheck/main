from __future__ import annotations

import re
from urllib.parse import urlparse

from nicegui import ui

import time
from typing import AsyncGenerator, Callable, Mapping, AsyncIterator

import ollama
from loguru import logger

from plugins.abstract import InterfaceLLM, Parameters, InterfaceLLMConfig, DictSerializableImplementation, \
    DictSerializable, ConfigurationCallbacks


class Ollama(InterfaceLLM):
    @staticmethod
    def name() -> str:
        return "Ollama"

    class ConfigParameters(Parameters):
        @classmethod
        def from_state(cls, state: dict[str, any]) -> Ollama.ConfigParameters:
            return Ollama.ConfigParameters(**state)

        def __init__(
                self, model: str = "llama2", keep_alive: str = "5m",
                **kwargs: any  # discard the rest
        ) -> None:
            # https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-chat-completion
            self.model = model
            # self.format = "json"
            # self.options: dict[str, any] | None = None
            # self.template: str | None = None
            # self.stream = False
            self.keep_alive = keep_alive

    class ConfigInterface(InterfaceLLMConfig):
        @classmethod
        def from_state(cls, state: dict[str, any]) -> DictSerializableImplementation:
            parameters = DictSerializable.from_object_dict(state["parameters"])
            return Ollama.ConfigInterface(
                name=state["name"], parameters=parameters, from_admin=state["from_admin"], host=state["host"]
            )

        def object_to_state(self) -> dict[str, any]:
            return {
                "name": self.name,
                "parameters": self.parameters.to_object_dict(),
                "from_admin": self.from_admin,
                "host": self.host
            }

        @staticmethod
        def _from_dict(state: dict[str, any]) -> DictSerializableImplementation:
            return Ollama.ConfigInterface(**state)

        def __init__(self, name: str, parameters: Ollama.ConfigParameters, from_admin: bool, host: str) -> None:
            super().__init__(name, from_admin)
            self.parameters = parameters
            self.host = host

    @staticmethod
    def configuration(instance_id: str, user_accessible: bool) -> ConfigurationCallbacks:
        def _reset_parameters() -> None:
            host_input.value = ""
            default_parameters = Ollama.ConfigParameters()
            editor.run_editor_method("set", {"json": default_parameters.object_to_state()})

        async def _get_config() -> Ollama.ConfigInterface:
            logger.info(f"adding LLM interface: {instance_id}")

            editor_content = await editor.run_editor_method("get")
            json_content = editor_content['json']

            parameters = Ollama.ConfigParameters(**json_content)
            new_interface = Ollama.ConfigInterface(
                name="", parameters=parameters, from_admin=instance_id is None, host=host_input.value
            )
            _reset_parameters()
            return new_interface

        def _is_valid_api_endpoint(url: str) -> bool:
            try:
                parsed_url = urlparse(url)
                if parsed_url.scheme not in ['http', 'https']:
                    return False

                if not parsed_url.netloc:
                    return False

                match = re.match(r'^[^:]+(:([0-9]+))?$', parsed_url.netloc)
                if match and match.group(2):  # If a port is present
                    port = int(match.group(2))
                    if port < 1 or 65535 < port:
                        return False

                return True

            except Exception as e:
                print(f"Error: {e}")
                return False

        with ui.input(
                label="Ollama host", placeholder="<scheme>://<domain>[:<port>][/<path>]",
                validation={
                    "Must be a valid REST endpoint": _is_valid_api_endpoint
                }
        ) as host_input:
            host_input.classes('w-full')
        _default = Ollama.ConfigParameters()
        with ui.json_editor({"content": {"json": _default.object_to_state()}}) as editor:
            editor.classes('w-full')

        with ui.markdown(
                "Go <a href=\"https://github.com/ollama/ollama/blob/main/docs/api.md\" "
                "target=\"_blank\">here</a> for a detailed documentation."
        ) as description:
            description.classes('w-full')

        with ui.markdown(
                "The following Ollama API parameters have been disabled for compatibility: `stream`, `messages`, "
                "`logprobs`, `top_logprobs`, `n`, `response_format`, `seed`, `stop`, and `tools`."
        ) as _:
            pass

        return ConfigurationCallbacks(reset=_reset_parameters, get_config=_get_config)

    @classmethod
    def from_state(cls, state: dict[str, any]) -> DictSerializableImplementation:
        parameters = DictSerializable.from_object_dict(state["parameters"])
        return Ollama(
            name=state["name"], parameters=parameters, from_admin=state["from_admin"], host=state["host"]
        )

    def __init__(self, name: str, parameters: Parameters, from_admin: bool, host: str) -> None:
        super().__init__(name, parameters, from_admin)
        self._host = host
        self._client = ollama.AsyncClient(host=host)

    async def reply_to_prompt(self, prompt: str, info_callback: Callable[[dict[str, any]], None] | None = None) -> str:

        logger.info(prompt)

        arguments = {k: v for k, v in self.parameters.object_to_state().items() if v is not None}

        reply = ""
        while True:
            try:
                messages = [{"role": "user", "content": prompt}]
                response: Mapping[str, any] = await self._client.chat(messages=messages, format="json", **arguments)
                if info_callback is not None:
                    info_callback(dict(response))

                message = response["message"]
                reply = message["content"]
                break

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

            response: AsyncIterator[Mapping[str, any]] = await self._client.chat(
                messages=messages, format="json", **arguments, stream=True
            )

            full_response = []
            async for each_chunk in response:
                logger.info(each_chunk)
                if info_callback is not None:
                    info_callback(dict(each_chunk))

                message = each_chunk["message"]
                content = message["content"]
                full_response.append(content)
                yield content

                # if message["done"]:
                #     break

            print("".join(full_response))

        except Exception as e:
            logger.error(e)
            raise e

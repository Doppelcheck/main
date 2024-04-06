from __future__ import annotations

from typing import AsyncGenerator
from urllib.parse import urlparse, unquote

import wikipedia
from loguru import logger
from nicegui import ui

from plugins.abstract import InterfaceData, Parameters, DictSerializableImplementation, InterfaceDataConfig, \
    DictSerializable, ConfigurationCallbacks, Uri, InterfaceLLM, Document
from tools.global_instances import WIKIPEDIA_LANGUAGES
from tools.text_processing import extract_code_block


class Wikipedia(InterfaceData):
    @staticmethod
    def _get_query(claim: str, context: str | None = None, language: str | None = None) -> str:
        context_data = (
            f"```context\n"
            f"{context}\n"
            f"```\n"
            f"\n"
        ) if context else ""

        context_instruction = (
            f" Refine your query according to the provided context."
        ) if context else ""

        language_instruction = f"Respond in {language}" if language or language != "default" else "Respond in the language of the claim"

        return (
            f"{context_data}"
            f"```claim\n"
            f"{claim}\n"
            f"```\n"
            f"\n"
            f"Generate a Wikipedia search query for results to verify of the claim above."
            f"{context_instruction}\n"
            f"\n"
            f"{language_instruction}, add the according Wikipedia language code (one of "
            f"{', '.join(WIKIPEDIA_LANGUAGES)}), and respond in a fenced code block according to the following "
            f"pattern.\n"
            f"```\n"
            f"[wikipedia search query]\n"
            f"[wikipedia language code]\n"
            f"```\n"
            f"\n"
            f"IMPORTANT: Don't wrap the full query or the language code in double quotes!"
        )

    @staticmethod
    def name() -> str:
        return "Wikipedia"

    class ConfigParameters(Parameters):
        @classmethod
        def from_state(cls, state: dict[str, any]) -> DictSerializableImplementation:
            return Wikipedia.ConfigParameters(**state)

        def __init__(
            self, language: str = "en",
            **kwargs: any  # discard the rest
        ) -> None:
            # https://wikipedia.readthedocs.io/en/latest/code.html
            self.language = language

    class ConfigInterface(InterfaceDataConfig):
        @classmethod
        def from_state(cls, state: dict[str, any]) -> DictSerializableImplementation:
            parameters = DictSerializable.from_object_dict(state["parameters"])
            return Wikipedia.ConfigInterface(
                name=state["name"], parameters=parameters, from_admin=state["from_admin"]
            )

        def object_to_state(self) -> dict[str, any]:
            return {
                "name": self.name,
                "parameters": self.parameters.to_object_dict(),
                "from_admin": self.from_admin
            }

        def __init__(self, name: str, parameters: Wikipedia.ConfigParameters, from_admin: bool) -> None:
            super().__init__(name, from_admin)
            self.parameters = parameters

    @staticmethod
    def configuration(instance_id: str | None, user_accessible: bool) -> ConfigurationCallbacks:
        def _reset_parameters() -> None:
            pass

        async def _get_config() -> Wikipedia.ConfigInterface:
            logger.info(f"adding data interface: {instance_id}")
            parameters = Wikipedia.ConfigParameters()
            new_interface = Wikipedia.ConfigInterface(name="", parameters=parameters, from_admin=instance_id is None)
            _reset_parameters()
            return new_interface

        with ui.markdown(
                "Go <a href=\"https://wikipedia.readthedocs.io/en/latest/code.html\" target=\"_blank\">here</a> for a "
                "detailed documentation."
        ) as description:
            description.classes('w-full')

        return ConfigurationCallbacks(reset=_reset_parameters, get_config=_get_config)

    @staticmethod
    def from_object_dict(object_dict: dict[str, any]) -> DictSerializableImplementation:
        return Wikipedia(**object_dict)

    @classmethod
    def from_state(cls, state: dict[str, any]) -> DictSerializableImplementation:
        parameters = DictSerializable.from_object_dict(state["parameters"])
        return Wikipedia(
            name=state["name"], parameters=parameters, from_admin=state["from_admin"]
        )

    def __init__(self, name: str, parameters: Wikipedia.ConfigParameters, from_admin: bool) -> None:
        super().__init__(name, parameters, from_admin)

    async def get_search_query(
            self, llm_interface: InterfaceLLM, keypoint_text: str,
            context: str | None = None, language: str | None = None):
        summarized_context = await llm_interface.summarize(context)
        prompt = Wikipedia._get_query(keypoint_text, context=summarized_context, language=language)

        response = await llm_interface.reply_to_prompt(prompt)
        query = extract_code_block(response)
        return query

    def wikipedia_pageid_from_title(self, title: str) -> int:
        return wikipedia.page(title).pageid

    def wikipedia_url_from_title(self, title: str) -> str:
        return wikipedia.page(title=title).url

    def wikipedia_title_from_url(self, url: str) -> str:
        parsed_url = urlparse(url)
        title = parsed_url.path.rsplit(sep='/', maxsplit=1)[-1]
        return unquote(title).replace("_", " ")

    async def get_uris(self, query: str) -> AsyncGenerator[Uri, None]:
        search_query, language_code = query.split(sep="\n", maxsplit=1)
        wikipedia.set_lang(language_code.strip())
        results = wikipedia.search(search_query.strip(), results=5)
        for each_item in results:
            try:
                yield Uri(uri_string=self.wikipedia_url_from_title(each_item), title=each_item)
            except wikipedia.exceptions.PageError as e:
                logger.warning(f"Page not found: {each_item}")
            except wikipedia.exceptions.DisambiguationError as e:
                logger.warning(f"Disambiguation: {each_item}")
            except wikipedia.exceptions.HTTPTimeoutError as e:
                logger.warning(f"HTTP timeout: {each_item}")
            except wikipedia.exceptions.RedirectError as e:
                logger.warning(f"Redirect: {each_item}")
            except wikipedia.exceptions.WikipediaException as e:
                logger.warning(f"General Wikipedia exception: {each_item}")

    async def get_source_content(self, uri: str) -> Document:
        title = self.wikipedia_title_from_url(uri)
        try:
            page = wikipedia.page(title)

        except wikipedia.exceptions.WikipediaException as e:
            return Document(uri=uri, content=None, error=str(e))

        return Document(uri=uri, content=page.content)

    async def get_context(
            self, uri: str, full_content: str | None = None) -> str | None:

        try:
            page = wikipedia.page(uri)

        except wikipedia.exceptions.WikipediaException as e:
            return None

        context = f"{page.title.upper()}\n\n{page.summary}"
        if len(context.strip()) < 20:
            return None

        return context

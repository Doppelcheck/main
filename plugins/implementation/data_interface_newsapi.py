from __future__ import annotations

from newsapi import NewsApiClient

from typing import AsyncGenerator

from loguru import logger
from nicegui import ui

from plugins.abstract import InterfaceData, Parameters, DictSerializableImplementation, InterfaceDataConfig, \
    DictSerializable, ConfigurationCallbacks, Uri, InterfaceLLM
from tools.content_retrieval import Document
from tools.global_instances import BROWSER_INSTANCE, HTTPX_SESSION
from tools.text_processing import extract_code_block


class NewsApi(InterfaceData):
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

        language_instruction = f"Respond in {language}" if language else "Respond in the language of the claim"

        return (
            f"{context_data}"
            f"```claim\n"
            f"{claim}\n"
            f"```\n"
            f"\n"
            f"Generate the optimal Google search query to get results that allow for the verification of the claim "
            f"above.{context_instruction}\n"
            f"\n"
            f"Make use of special Google search operators to improve result quality. Do not restrict the query to "
            f"particular top-level domains like with `site:ru` or similar and make sure not to make it too specific.\n"
            f"\n"
            f"IMPORTANT: Split up compound words! Don't wrap the full query in double quotes!\n"
            f"\n"
            f"{language_instruction} and exactly and only with the search query requested in a fenced code block according "
            f"to the following pattern.\n"
            f"```\n"
            f"[query]\n"
            f"```\n"
        )

    @staticmethod
    def name() -> str:
        return "NewsApi"

    class ConfigParameters(Parameters):
        @classmethod
        def from_state(cls, state: dict[str, any]) -> DictSerializableImplementation:
            return NewsApi.ConfigParameters(**state)

        def __init__(
                self, cx: str, key: str, c2coff: int | None = None, cr: str | None = None,
                dateRestrict: str | None = None, exactTerms: str | None = None, excludeTerms: str | None = None,
                fileType: str | None = None, filter: str = "1", gl: str | None = None, highRange: str | None = None,
                hl: str | None = None, hq: str | None = None, linkSite: str | None = None, lowRange: str | None = None,
                lr: str | None = None, num: int = 10, orTerms: str | None = None, rights: str | None = None,
                safe: str = 'off', siteSearch: str | None = None, siteSearchFilter: str | None = None,
                sort: str | None = "date", start: int = 1,
                **kwargs: any  # discard the rest
        ) -> None:

            # https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list
            self.cx = cx
            self.key = key
            self.c2coff = c2coff
            self.cr = cr
            self.dateRestrict = dateRestrict
            self.exactTerms = exactTerms
            self.excludeTerms = excludeTerms
            self.fileType = fileType
            self.filter = filter
            self.gl = gl
            self.highRange = highRange
            self.hl = hl
            self.hq = hq
            self.linkSite = linkSite
            self.lowRange = lowRange
            self.lr = lr
            self.num = num
            self.orTerms = orTerms
            self.rights = rights
            self.safe = safe
            self.siteSearch = siteSearch
            self.siteSearchFilter = siteSearchFilter
            self.sort = sort   # changed default for news focus
            self.start = start

    class ConfigInterface(InterfaceDataConfig):
        @classmethod
        def from_state(cls, state: dict[str, any]) -> DictSerializableImplementation:
            parameters = DictSerializable.from_object_dict(state["parameters"])
            return NewsApi.ConfigInterface(
                name=state["name"], parameters=parameters, from_admin=state["from_admin"]
            )

        def object_to_state(self) -> dict[str, any]:
            return {
                "name": self.name,
                "parameters": self.parameters.to_object_dict(),
                "from_admin": self.from_admin
            }

        def __init__(self, name: str, parameters: NewsApi.ConfigParameters, from_admin: bool) -> None:
            super().__init__(name, from_admin)
            self.parameters = parameters

    @staticmethod
    def configuration(user_id: str, user_accessible: bool, is_admin: bool) -> ConfigurationCallbacks:
        def _reset_parameters() -> None:
            default_parameters = NewsApi.ConfigParameters("", "")
            editor.run_editor_method("set", {"json": default_parameters.object_to_state()})

        async def _get_config() -> NewsApi.ConfigInterface:
            logger.info(f"adding data interface: {user_id}")
            editor_content = await editor.run_editor_method("get")
            json_content = editor_content['json']
            parameters = NewsApi.ConfigParameters(**json_content)
            new_interface = NewsApi.ConfigInterface(name="", parameters=parameters, from_admin=is_admin)
            _reset_parameters()
            return new_interface

        _default = NewsApi.ConfigParameters("", "")
        with ui.json_editor({"content": {"json": _default.object_to_state()}}) as editor:
            editor.classes('w-full')
        with ui.markdown(
                "Info: `cx` is the custom Google search engine ID, `key` is your Google API key."
        ) as description:
            description.classes('w-full')
        with ui.markdown(
                "Go <a href=\"https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list\" "
                "target=\"_blank\">here</a> for a detailed documentation."
        ) as description:
            description.classes('w-full')

        ui.label("The following Google search API parameter has been disabled: `q`.").classes('w-full')
        ui.label("The parameter `sort` has been set to a default value of \"date\" for news.").classes('w-full')

        return ConfigurationCallbacks(reset=_reset_parameters, get_config=_get_config)

    @staticmethod
    def from_object_dict(object_dict: dict[str, any]) -> DictSerializableImplementation:
        return NewsApi(**object_dict)

    @classmethod
    def from_state(cls, state: dict[str, any]) -> DictSerializableImplementation:
        parameters = DictSerializable.from_object_dict(state["parameters"])
        return NewsApi(
            name=state["name"], parameters=parameters, from_admin=state["from_admin"]
        )

    def __init__(self, name: str, parameters: NewsApi.ConfigParameters, from_admin: bool) -> None:
        super().__init__(name, parameters, from_admin)

    async def get_search_query(
            self, llm_interface: InterfaceLLM, keypoint_text: str,
            context: str | None = None, language: str | None = None):
        prompt = NewsApi._get_query(keypoint_text, context=context, language=language)

        response = await llm_interface.reply_to_prompt(prompt)
        query = extract_code_block(response)
        return query

    async def get_uris(self, query: str, doc_count: int) -> AsyncGenerator[Uri, None]:

        url = "https://www.googleapis.com/customsearch/v1"
        # https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list#response
        # todo: use llm to craft parameter dict

        params = {k: v for k, v in self.parameters.object_to_state().items() if v is not None}
        params["q"] = query
        params["num"] = doc_count

        # async with httpx.AsyncClient() as httpx_session:
        #    response = await httpx_session.get(url, params=params)

        response = await HTTPX_SESSION.get(url, params=params)

        if response.status_code != 200:
            items = list()

        else:
            result = response.json()

            items = result.get("items")
            if items is None:
                items = list()

        for each_item in items:
            yield Uri(uri_string=each_item['link'])

    async def get_document_content(self, uri: str) -> Document:
        return await BROWSER_INSTANCE.get_html_content(uri)


if __name__ == "__main__":
    newsapi = NewsApiClient(api_key='9e9afcad6ca340faae5e253895db02da')

    # /v2/top-headlines
    top_headlines = newsapi.get_top_headlines(
        q='bitcoin',
        sources='bbc-news,the-verge',
        # category='business',
        # language='en',
        # country='us'
    )

    # /v2/everything
    all_articles = newsapi.get_everything(
        q='bitcoin',
        sources='bbc-news,the-verge',
        domains='bbc.co.uk,techcrunch.com',
        from_param='2024-02-01',
        to='2024-02-10',
        language='en',
        sort_by='relevancy',
        page=2
    )

    # /v2/top-headlines/sources
    sources = newsapi.get_sources()
    # https://newsapi.org/docs/endpoints/everything
    print()
from __future__ import annotations

from typing import AsyncGenerator

from loguru import logger
from nicegui import ui

from tools.content_retrieval import Document
from tools.global_instances import BROWSER_INSTANCE, HTTPX_SESSION
from tools.plugins.abstract import InterfaceData, Uri, Parameters, InterfaceDataConfig, DictSerializableImplementation, \
    DictSerializable, ConfigurationCallbacks


class Google(InterfaceData):
    @staticmethod
    def name() -> str:
        return "Google"

    class ConfigParameters(Parameters):
        @classmethod
        def from_state(cls, state: dict[str, any]) -> DictSerializableImplementation:
            return Google.ConfigParameters(**state)

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
            return Google.ConfigInterface(
                name=state["name"], parameters=parameters, from_admin=state["from_admin"]
            )

        def object_to_state(self) -> dict[str, any]:
            return {
                "name": self.name,
                "parameters": self.parameters.to_object_dict(),
                "from_admin": self.from_admin
            }

        def __init__(self, name: str, parameters: Google.ConfigParameters, from_admin: bool) -> None:
            super().__init__(name, from_admin)
            self.parameters = parameters

    @staticmethod
    def configuration(user_id: str, user_accessible: bool) -> ConfigurationCallbacks:
        admin = user_id == "ADMIN"

        def _reset_parameters() -> None:
            default_parameters = Google.ConfigParameters("", "")
            editor.run_editor_method("set", {"json": default_parameters.object_to_state()})

        async def _get_config() -> Google.ConfigInterface:
            logger.info(f"adding data interface: {user_id}")
            editor_content = await editor.run_editor_method("get")
            json_content = editor_content['json']
            parameters = Google.ConfigParameters(**json_content)
            new_interface = Google.ConfigInterface(name="", parameters=parameters, from_admin=admin)
            _reset_parameters()
            return new_interface

        _default = Google.ConfigParameters("", "")
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
        return Google(**object_dict)

    @classmethod
    def from_state(cls, state: dict[str, any]) -> DictSerializableImplementation:
        parameters = DictSerializable.from_object_dict(state["parameters"])
        return Google(
            name=state["name"], parameters=parameters, from_admin=state["from_admin"]
        )

    def __init__(self, name: str, parameters: Google.ConfigParameters, from_admin: bool) -> None:
        super().__init__(name, parameters, from_admin)

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

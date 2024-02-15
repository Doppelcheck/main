import dataclasses
from contextlib import contextmanager
from typing import Callable

from nicegui import ui
from nicegui.element import Element
# from pydantic import BaseModel, Field
from enum import Enum

from tools.data_access import get_nested_value, set_nested_value


class ProviderLLM(Enum):
    OpenAI = "OpenAI"
    Mistral = "Mistral"
    Anthropic = "Anthropic"
    ollama = "ollama"
    llamafile = "llamafile"


class ProviderData(Enum):
    Google = "Google"
    Bing = "Bing"
    DuckDuckGo = "DuckDuckGo"
    GDELT = "GDELT"
    Twitter = "Twitter"
    MBFC = "MBFC"
    CrossRef = "CrossRef"
    ReutersConnect = "ReutersConnect"


@dataclasses.dataclass
class Parameters:
    pass


@dataclasses.dataclass
class ParametersOpenAi(Parameters):
    # https://platform.openai.com/docs/api-reference/chat/create
    model: str = "gpt-4-1106-preview"  # positional
    frequency_penalty: float = 0
    logit_bias: dict[int, float] | None = None
    # logprobs: bool = False
    # top_logprobs: int | None = None
    max_tokens: int | None = None
    # n: int = 1
    presence_penalty: float = 0
    # response_format: dict[str, str] | None = None
    # seed: int | None = None
    # stop: str | list[str] | None = None
    temperature: float = 0.  # 1.
    top_p: float | None = None  # 1
    # tools: list[str] = None
    # tool_choice: str | dict[str, any] | None = None
    user: str | None = None


@dataclasses.dataclass
class ParametersGoogle(Parameters):
    # https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list
    cx: str
    key: str
    c2coff: int | None = None
    cr: str | None = None
    dateRestrict: str | None = None
    exactTerms: str | None = None
    excludeTerms: str | None = None
    fileType: str | None = None
    filter: int = 1
    gl: str | None = None
    highRange: str | None = None
    hl: str | None = None
    hq: str | None = None
    linkSite: str | None = None
    lowRange: str | None = None
    lr: str | None = None
    num: int | None = 10
    orTerms: str | None = None
    rights: str | None = None
    safe: str = 'off'
    siteSearch: str | None = None
    siteSearchFilter: str | None = None
    sort: str | None = "date"
    start: int | None = None


@dataclasses.dataclass
class InterfaceLLM:
    name: str
    parameters: Parameters
    provider: ProviderLLM


@dataclasses.dataclass
class InterfaceData:
    name: str
    parameters: Parameters
    provider: ProviderData


@dataclasses.dataclass
class InterfaceOpenAi(InterfaceLLM):
    api_key: str = ""
    parameters: ParametersOpenAi
    provider: ProviderLLM = ProviderLLM.OpenAI


@dataclasses.dataclass
class InterfaceGoogle(InterfaceData):
    api_key: str = ""
    engine_id: str = ""
    parameters: ParametersGoogle
    provider: ProviderData = ProviderData.Google


class ConfigModel:
    def __init__(self, user_id: str) -> None:
        self._user_id: str = user_id
        self._key_path: tuple[str, ...] = ("users", user_id, "config")

        self._general_name: str = "Default instance"
        self._general_language: str = "default"

        self._llm_interfaces: list[InterfaceLLM] = list()
        self._data_interfaces: list[InterfaceData] = list()

        self._extraction_llm: InterfaceLLM | None = None
        self._extraction_claims: int = 3

        self._retrieval_llm: InterfaceLLM | None = None
        self._retrieval_data: InterfaceData | None = None
        self._retrieval_max_documents: int = 10

        self._comparison_llm: InterfaceLLM | None = None
        self._comparison_data: InterfaceData | None = None

    @property
    def user_id(self) -> str:
        return self._user_id

    def _llm_to_json(self, llm: InterfaceLLM) -> dict[str, any]:
        d = dataclasses.asdict(llm)
        d["_type"] = type(llm).__name__
        return d

    def _json_to_llm(self, **d: dict[str, any]) -> InterfaceLLM:
        if d.pop("_type") == "InterfaceOpenAi":
            return InterfaceOpenAi(**d)
        raise ValueError(f"Unknown type: {d['_type']}")

    def get_general_name(self) -> str:
        value = get_nested_value(self._key_path + ("general_name",), default=self._general_name)
        return value

    def set_general_name(self, value: str) -> None:
        self._general_name = value
        set_nested_value(self._key_path + ("general_name",), value)

    def get_general_language(self) -> str:
        value = get_nested_value(self._key_path + ("general_language",), default=self._general_language)
        return value

    def set_general_language(self, value: str) -> None:
        self._general_language = value
        set_nested_value(self._key_path + ("general_language",), value)

    def get_llm_interfaces(self) -> list[InterfaceLLM]:
        value = get_nested_value(self._key_path + ("llm_interfaces",), default=self._llm_interfaces)
        return [self._json_to_llm(**each) for each in value]

    def add_llm_interface(self, interface: InterfaceLLM) -> None:
        values = get_nested_value(self._key_path + ("llm_interfaces",), default=self._llm_interfaces)
        values.append(self._llm_to_json(interface))
        set_nested_value(self._key_path + ("llm_interfaces",), values)

    def remove_llm_interface(self, key_name: str) -> None:
        values = get_nested_value(self._key_path + ("llm_interfaces",), default=self._llm_interfaces)
        values = [each_interface for each_interface in values if each_interface["name"] != key_name]
        set_nested_value(self._key_path + ("llm_interfaces",), values)

    def get_data_interfaces(self) -> list[InterfaceData]:
        value = get_nested_value(self._key_path + ("data_interfaces",), default=self._data_interfaces)
        return [InterfaceData(**each) for each in value]

    def add_data_interface(self, interface: InterfaceData) -> None:
        values = get_nested_value(self._key_path + ("data_interfaces",), default=self._data_interfaces)
        values.append(dataclasses.asdict(interface))
        set_nested_value(self._key_path + ("data_interfaces",), values)

    def remove_data_interface(self, key_name: str) -> None:
        values = get_nested_value(self._key_path + ("data_interfaces",), default=self._data_interfaces)
        values = [each_interface for each_interface in values if each_interface["name"] != key_name]
        set_nested_value(self._key_path + ("data_interfaces",), values)

    def get_extraction_llm(self) -> InterfaceLLM | None:
        value = get_nested_value(self._key_path + ("extraction_llm",), default=self._extraction_llm)
        if value is None:
            return None
        return self._json_to_llm(**value)

    def set_extraction_llm(self, value: InterfaceLLM | None) -> None:
        self._extraction_llm = value
        set_nested_value(self._key_path + ("extraction_llm",), self._llm_to_json(value))

    def get_extraction_claims(self) -> int:
        value = get_nested_value(self._key_path + ("extraction_claims",), default=self._extraction_claims)
        return value

    def set_extraction_claims(self, value: int) -> None:
        self._extraction_claims = value
        set_nested_value(self._key_path + ("extraction_claims",), value)

    def get_retrieval_llm(self) -> InterfaceLLM | None:
        value = get_nested_value(self._key_path + ("retrieval_llm",), default=self._retrieval_llm)
        if value is None:
            return None
        return self._json_to_llm(**value)

    def set_retrieval_llm(self, value: InterfaceLLM | None) -> None:
        self._retrieval_llm = value
        set_nested_value(self._key_path + ("retrieval_llm",), self._llm_to_json(value))

    def get_retrieval_data(self) -> InterfaceData | None:
        value = get_nested_value(self._key_path + ("retrieval_data",), default=self._retrieval_data)
        if value is None:
            return None
        return InterfaceData(**value)

    def set_retrieval_data(self, value: InterfaceData | None) -> None:
        self._retrieval_data = value
        set_nested_value(self._key_path + ("retrieval_data",), dataclasses.asdict(value))

    def get_retrieval_max_documents(self) -> int:
        value = get_nested_value(self._key_path + ("retrieval_max_documents",), default=self._retrieval_max_documents)
        return value

    def set_retrieval_max_documents(self, value: int) -> None:
        self._retrieval_max_documents = value
        set_nested_value(self._key_path + ("retrieval_max_documents",), value)

    def get_comparison_llm(self) -> InterfaceLLM | None:
        value = get_nested_value(self._key_path + ("comparison_llm",), default=self._comparison_llm)
        if value is None:
            return None
        return self._json_to_llm(**value)

    def set_comparison_llm(self, value: InterfaceLLM | None) -> None:
        self._comparison_llm = value
        set_nested_value(self._key_path + ("comparison_llm",), self._llm_to_json(value))

    def get_comparison_data(self) -> InterfaceData | None:
        value = get_nested_value(self._key_path + ("comparison_data",), default=self._comparison_data)
        if value is None:
            return None
        return InterfaceData(**value)

    def set_comparison_data(self, value: InterfaceData | None) -> None:
        self._comparison_data = value
        set_nested_value(self._key_path + ("comparison_data",), dataclasses.asdict(value))


@contextmanager
def store(element_type: type[Element], set_value: Callable[[str], any], get_value: Callable[[], any], **kwargs) -> None:
    timer: ui.timer | None = None

    def update_timer(callback: Callable[..., any]) -> None:
        nonlocal timer
        if timer is not None:
            timer.cancel()
            del timer
        timer = ui.timer(interval=1.0, active=True, once=True, callback=callback)

    def delay(value: any, validation: dict[str, Callable[[str], bool]] | None = None) -> None:
        if validation is None or all(each_validation(value) for each_validation in validation.values()):
            def set_storage() -> None:
                set_value(value)
                ui.notify(f"{kwargs.get('label', 'Setting')} saved", timeout=500)  # , progress=True)

            update_timer(set_storage)

    last_value = get_value()
    with element_type(
        value=last_value, **kwargs,
        on_change=lambda event: delay(event.value, validation=kwargs.get("validation"))
    ) as element:
        yield element

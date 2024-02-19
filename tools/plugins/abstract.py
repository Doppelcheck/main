import dataclasses
import importlib
from abc import abstractmethod, ABC
from typing import Callable, AsyncGenerator, Sequence, TypeVar

from tools.text_processing import chunk_text


PluginImplementation = TypeVar("PluginImplementation", bound="PluginBase")


class PluginBase(ABC):
    @staticmethod
    def _get_class(class_name: str, module_name: str) -> type[PluginImplementation]:
        module = importlib.import_module(module_name)
        class_: type[PluginImplementation] = getattr(module, class_name)
        return class_

    @classmethod
    @abstractmethod
    def _from_dict(cls, state: dict[str, any]) -> PluginImplementation:
        raise NotImplementedError("Method not implemented")

    @staticmethod
    def from_dict(state: dict[str, any]) -> PluginImplementation:
        class_name = state.pop("__class__")
        module_name = state.pop("__module__")
        class_: type[PluginImplementation] = PluginBase._get_class(class_name, module_name)
        return class_._from_dict(**state)

    @abstractmethod
    def _to_dict(self) -> dict[str, any]:
        raise NotImplementedError("Method not implemented")

    def to_dict(self) -> dict[str, any]:
        state_dict = self._to_dict()
        state_dict["__class__"] = self.__class__.__name__
        state_dict["__module__"] = self.__module__
        return state_dict


@dataclasses.dataclass(frozen=True)
class Uri:
    uri_string: str | None
    error: str | None = None


@dataclasses.dataclass(frozen=True)
class Document:
    uri: str
    content: str | None
    error: str | None = None


@dataclasses.dataclass
class Parameters:
    pass


@dataclasses.dataclass
class InterfaceConfig:
    name: str
    provider: str
    from_admin: bool


@dataclasses.dataclass
class InterfaceLLMConfig(InterfaceConfig):
    pass


@dataclasses.dataclass
class InterfaceDataConfig(InterfaceConfig):
    pass


class InterfaceData(PluginBase):
    @abstractmethod
    async def get_uris(self, query: str, doc_count: int, parameters: Parameters) -> Sequence[str]:
        raise NotImplementedError("Method not implemented")

    @abstractmethod
    async def get_document_content(self, uri: str) -> Document:
        raise NotImplementedError("Method not implemented")


class InterfaceLLM(PluginBase):
    async def summarize(
            self, text: str, parameters: Parameters | None = None,
            max_len_input: int = 10_000, max_len_summary: int = 500) -> str:

        len_text = len(text)
        if len_text < max_len_summary:
            return text

        summaries = list()
        for each_chunk in chunk_text(text, max_len=max_len_input):
            summary = await self.summarize(
                each_chunk, parameters=parameters,
                max_len_input=max_len_input, max_len_summary=max_len_summary)
            summaries.append(summary)
        text = "\n".join(summaries)

        prompt = (
            f"```text\n"
            f"{text}\n"
            f"```\n"
            f"\n"
            f"Summarize the text above in about {max_len_summary} characters keeping its original language."
        )
        response = await self.reply_to_prompt(prompt, parameters)
        return response

    @abstractmethod
    async def reply_to_prompt(
            self, prompt: str, parameters: Parameters,
            info_callback: Callable[[dict[str, any]], None] | None = None
    ) -> str:

        raise NotImplementedError("Method not implemented")

    @abstractmethod
    async def stream_reply_to_prompt(
            self, prompt: str, parameters: Parameters,
            info_callback: Callable[[dict[str, any]], None] | None = None
    ) -> AsyncGenerator[str, None]:
        raise NotImplementedError("Method not implemented")


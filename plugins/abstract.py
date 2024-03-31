from __future__ import annotations
import dataclasses
import importlib
import inspect
from abc import abstractmethod, ABC, ABCMeta
from typing import Callable, AsyncGenerator, TypeVar, Awaitable

from tools.text_processing import chunk_text

DictSerializableImplementation = TypeVar("DictSerializableImplementation", bound="DictSerializable")


class DictSerializable(ABC):
    @staticmethod
    def get_class(qualified_class_name: str, module_name: str) -> type[DictSerializableImplementation]:
        context = importlib.import_module(module_name)
        for each_class in qualified_class_name.split("."):
            context = getattr(context, each_class)

        return context

    @classmethod
    @abstractmethod
    def from_state(cls, state: dict[str, any]) -> DictSerializableImplementation:
        raise NotImplementedError("Method not implemented")

    @staticmethod
    def from_object_dict(object_dict: dict[str, any]) -> DictSerializableImplementation:
        class_name = object_dict["__class__"]
        module_name = object_dict["__module__"]

        class_ = DictSerializable.get_class(class_name, module_name)
        return class_.from_state({k: v for k, v in object_dict.items() if not k.startswith("__")})

    @abstractmethod
    def object_to_state(self) -> dict[str, any]:
        raise NotImplementedError("Method not implemented")

    def to_object_dict(self) -> dict[str, any]:
        state_dict = self.object_to_state()
        state_dict["__class__"] = self.__class__.__qualname__
        state_dict["__module__"] = self.__module__
        return state_dict


class Parameters(DictSerializable, ABC):
    def object_to_state(self) -> dict[str, any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("__")}


class InterfaceConfig(DictSerializable, ABC):
    def __init__(self, name: str, from_admin: bool) -> None:
        self.name = name
        self.from_admin = from_admin

    def get_interface_class(self) -> type[Interface]:
        module_name = self.__module__
        qualified_class_name = self.__class__.__qualname__

        module = importlib.import_module(module_name)
        class_name = qualified_class_name.split(".", maxsplit=1)[0]
        class_ = getattr(module, class_name)
        return class_


class InterfaceLLMConfig(InterfaceConfig, ABC):
    pass


class InterfaceDataConfig(InterfaceConfig, ABC):
    pass


class InterfaceMeta(ABCMeta):
    def __init__(cls: type[Interface], name: str, bases: tuple[type, ...], dct: dict[str, any]) -> None:
        super().__init__(name, bases, dct)

        if inspect.isabstract(cls):
            return

        nested_class = dct.get("ConfigParameters")
        if nested_class is None or not inspect.isclass(nested_class):
            raise TypeError(f"Interface implementation `{name}` must define a `ConfigParameters` inner class.")
        if not issubclass(nested_class, Parameters):
            raise TypeError(f"`{name}.ConfigParameters` must be a subclass of `Parameters`.")

        nested_class = dct.get("ConfigInterface")
        if nested_class is None or not inspect.isclass(nested_class):
            raise TypeError(f"Interface implementation `{name}` must define a `ConfigInterface` inner class.")
        if not issubclass(nested_class, InterfaceConfig):
            raise TypeError(f"`{name}.ConfigInterface` must be a subclass of `InterfaceConfig`.")


@dataclasses.dataclass(frozen=True)
class ConfigurationCallbacks:
    get_config: Callable[[], Awaitable[InterfaceLLMConfig | InterfaceDataConfig]]
    reset: Callable[[], None]


class Interface(DictSerializable, ABC):
    @staticmethod
    @abstractmethod
    def name() -> str:
        raise NotImplementedError("Method not implemented")

    @staticmethod
    @abstractmethod
    def configuration(user_id: str | None, user_accessible: bool) -> ConfigurationCallbacks:
        raise NotImplementedError("Method not implemented")

    def __init__(self, name: str, parameters: Parameters, from_admin: bool) -> None:
        self.name = name
        self.parameters = parameters
        self.from_admin = from_admin

    def object_to_state(self) -> dict[str, any]:
        return {
            "name": self.name,
            "parameters": self.parameters.to_object_dict(),
            "from_admin": self.from_admin
        }


class InterfaceData(Interface, ABC, metaclass=InterfaceMeta):
    @abstractmethod
    async def get_uris(self, query: str) -> AsyncGenerator[Uri, None]:
        raise NotImplementedError("Method not implemented")

    @abstractmethod
    async def get_document_content(self, uri: str) -> Document:
        raise NotImplementedError("Method not implemented")

    @abstractmethod
    async def get_search_query(
            self, llm_interface: InterfaceLLM, keypoint_text: str,
            context: str | None = None, language: str | None = None):
        raise NotImplementedError("Method not implemented")

    @abstractmethod
    async def get_context(
            self, uri: str, full_content: str | None = None) -> str | None:
        raise NotImplementedError("Method not implemented")


class InterfaceLLM(Interface, ABC, metaclass=InterfaceMeta):
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
            self, prompt: str, info_callback: Callable[[dict[str, any]], None] | None = None
    ) -> str:

        raise NotImplementedError("Method not implemented")

    @abstractmethod
    async def stream_reply_to_prompt(
            self, prompt: str, info_callback: Callable[[dict[str, any]], None] | None = None
    ) -> AsyncGenerator[str, None]:

        raise NotImplementedError("Method not implemented")


@dataclasses.dataclass(frozen=True)
class Uri:
    uri_string: str | None
    title: str | None = None
    error: str | None = None


@dataclasses.dataclass(frozen=True)
class Document:
    uri: str
    content: str | None
    error: str | None = None

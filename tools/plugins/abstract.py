import dataclasses
from abc import abstractmethod
from typing import Callable, AsyncGenerator, Sequence, TypeVar, Awaitable, Any

from tools.text_processing import chunk_text


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
    max_documents: int


class InterfaceData:
    @abstractmethod
    async def get_uris(self, query: str, doc_count: int, parameters: Parameters) -> Sequence[str]:
        raise NotImplementedError("Method not implemented")

    @abstractmethod
    async def get_document_content(self, uri: str) -> Document:
        raise NotImplementedError("Method not implemented")


class InterfaceLLM:
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


_AwaitableT_co = TypeVar("_AwaitableT_co", bound=Awaitable[Any], covariant=True)

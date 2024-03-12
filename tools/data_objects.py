from abc import ABC
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class GoogleCustomSearch:
    api_key: str | None = None
    engine_id: str | None = None


@dataclass
class ParametersOpenAi:
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


@dataclass(kw_only=True)
class Pong:
    message_type: str = "pong_message"


@dataclass(kw_only=True)
class Message(ABC):
    message_type: str
    content: str | None = field(default=None)


@dataclass(kw_only=True)
class ErrorMessage(Message):
    message_type: str = "error_message"


@dataclass(kw_only=True)
class QuoteMessage(Message):
    keypoint_index: int
    message_type: str = "quote_message"
    stop: bool = field(default=False)


@dataclass(kw_only=True)
class KeypointMessage(Message):
    keypoint_index: int
    message_type: str = "keypoint_message"
    stop: bool = field(default=False)
    stop_all: bool = field(default=False)


@dataclass(kw_only=True)
class SourcesMessage(Message):
    keypoint_index: int
    message_type: str = "sources_message"
    title: str | None = field(default=None)
    stop: bool = field(default=False)


@dataclass(kw_only=True)
class RatingMessage(Message):
    keypoint_index: int
    source_index: int
    message_type: str = "rating_message"
    stop: bool = field(default=False)


@dataclass(kw_only=True)
class ExplanationMessage(Message):
    keypoint_index: int
    source_index: int
    message_type: str = "explanation_message"
    stop: bool = field(default=False)

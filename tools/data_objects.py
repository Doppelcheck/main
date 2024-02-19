from dataclasses import dataclass


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


@dataclass
class MessageSegment:
    segment: str
    last_segment: bool
    last_message: bool


@dataclass
class ClaimSegment(MessageSegment):
    claim_id: int
    purpose: str = "extract"
    highlight: str | None = None


@dataclass
class DocumentSegment(MessageSegment):
    claim_id: int
    document_id: int
    document_uri: str
    success: bool = True
    purpose: str = "retrieve"


@dataclass
class ComparisonSegment(MessageSegment):
    claim_id: int
    document_id: int
    match_value: int
    purpose: str = "compare"


@dataclass
class Doc:
    claim_id: int
    uri: str
    content: str | None

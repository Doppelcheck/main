from dataclasses import dataclass


@dataclass
class OpenAIParameters:
    # https://platform.openai.com/docs/api-reference/chat/create
    model: str = "gpt-4-1106-preview"  # positional
    # frequency_penalty: float = 0
    # logit_bias: dict[int, float] | None = None
    # logprobs: bool = False
    # top_logprobs: int | None = None
    # max_tokens: int | None = None
    # n: int = 1
    # presence_penalty: float = 0
    # response_format: dict[str, str] | None = None
    # seed: int | None = None
    # stop: str | list[str] | None = None
    temperature: float = 0.  # 1.
    top_p: float | None = None  # 1
    # tools: list[str] = None
    # tool_choice: str | dict[str, any] | None = None
    # user: str | None = None


@dataclass
class GoogleCustomSearch:
    api_key: str | None = None
    engine_id: str | None = None


@dataclass
class UserConfig:
    name_instance: str = "standard instance"
    claim_count: int = 3
    language: str = "default"

    google_custom_search: dict[str, str] | GoogleCustomSearch | None = None

    openai_api_key: str | None = None
    openai_parameters: dict[str, str] | OpenAIParameters | None = None

    def __post_init__(self) -> None:
        if self.google_custom_search is not None and not isinstance(self.google_custom_search, GoogleCustomSearch):
            self.google_custom_search = GoogleCustomSearch(**self.google_custom_search)
        if self.openai_parameters is not None and not isinstance(self.openai_parameters, OpenAIParameters):
            self.openai_parameters = OpenAIParameters(**self.openai_parameters)
        else:
            self.openai_parameters = OpenAIParameters()

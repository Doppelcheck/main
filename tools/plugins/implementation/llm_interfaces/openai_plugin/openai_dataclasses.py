import dataclasses

from tools.plugins.abstract import InterfaceLLMConfig, Parameters


@dataclasses.dataclass
class ParametersOpenAi(Parameters):
    # https://platform.openai.com/docs/api-reference/chat/create
    model: str = "gpt-4-1106-preview"
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
    temperature: float = 0
    top_p: float | None = None
    # tools: list[str] = None
    user: str | None = None


@dataclasses.dataclass
class InterfaceOpenAi(InterfaceLLMConfig):
    api_key: str
    parameters: ParametersOpenAi
    provider: str = dataclasses.field(default="OpenAI", init=False)


if __name__ == "__main__":
    p = ParametersOpenAi()
    i = InterfaceOpenAi(name="", api_key="", parameters=p)
    print(dataclasses.asdict(i))

    p = InterfaceLLMConfig(name="", provider="")
    print(dataclasses.asdict(p))

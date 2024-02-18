from tools.plugins.abstract import InterfaceLLM, InterfaceData
from tools.plugins.implementation import InterfaceOpenAi, InterfaceGoogle


def llm_from_dict(llm_dict: dict[str, any]) -> InterfaceLLM:
    llm_dict = dict(llm_dict)
    provider = llm_dict.pop("provider")
    return InterfaceOpenAi(**llm_dict)


def data_from_dict(data_dict: dict[str, any]) -> InterfaceData:
    data_dict = dict(data_dict)
    provider = data_dict.pop("provider")
    return InterfaceGoogle(**data_dict)

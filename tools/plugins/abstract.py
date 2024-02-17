import dataclasses


@dataclasses.dataclass
class InterfaceLLM:
    name: str
    provider: str


@dataclasses.dataclass
class InterfaceData:
    name: str
    provider: str


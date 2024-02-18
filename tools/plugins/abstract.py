import dataclasses


@dataclasses.dataclass
class Interface:
    name: str
    provider: str
    from_admin: bool


@dataclasses.dataclass
class InterfaceLLM(Interface):
    pass


@dataclasses.dataclass
class InterfaceData(Interface):
    pass

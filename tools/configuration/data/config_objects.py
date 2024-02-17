import dataclasses
from contextlib import contextmanager
from typing import Callable, TypeVar

from loguru import logger
from nicegui import ui
from nicegui.element import Element

from tools.data_access import get_nested_value, set_nested_value
from tools.plugins.abstract import InterfaceLLM, InterfaceData

from tools.plugins import implementation


# todo: generate via introspection
ProvidersLLM = {
    "OpenAI": implementation.InterfaceOpenAi,
    #"Mistral": llm_interfaces.Mistral,
    #"Anthropic": llm_interfaces.Anthropic,
    #"ollama": llm_interfaces.Ollama,
    #"llamafile": llm_interfaces.Llamafile,
}

ProvidersData = {
    "Google": implementation.InterfaceGoogle,
}


class ConfigModel:
    @staticmethod
    def _llm_from_dict(llm_dict: dict[str, any]) -> InterfaceLLM:
        llm_dict = dict(llm_dict)
        provider = llm_dict.pop("provider")
        interface_class = ProvidersLLM[provider]
        return interface_class(**llm_dict)

    @staticmethod
    def _data_from_dict(data_dict: dict[str, any]) -> InterfaceData:
        data_dict = dict(data_dict)
        provider = data_dict.pop("provider")
        interface_class = ProvidersData[provider]
        return interface_class(**data_dict)

    @staticmethod
    def _user_path(user_id: str, key: str) -> tuple[str, ...]:
        return "users", user_id, "config", key

    @staticmethod
    def get_user_access(user_id: str, key: str) -> bool:
        key_path = ConfigModel._user_path(user_id, f"user_access_{key}")
        return get_nested_value(key_path, default=False)

    @staticmethod
    def set_user_access(user_id: str, key: str, value: bool) -> None:
        key_path = ConfigModel._user_path(user_id, f"user_access_{key}")
        set_nested_value(key_path, value)

    @staticmethod
    def _set_value(user_id: str, key: str, value: any) -> None:
        key_path = ConfigModel._user_path(user_id, key)
        if user_id == "ADMIN":
            set_nested_value(key_path, value)

        elif ConfigModel.get_user_access(user_id, key):
            set_nested_value(key_path, value)

    @staticmethod
    def _get_value(user_id: str, key: str, default: any = None) -> any:
        admin_key_path = ConfigModel._user_path("ADMIN", key)
        admin_value = get_nested_value(admin_key_path, default=default)
        if user_id == "ADMIN":
            return admin_value

        user_key_path = ConfigModel._user_path(user_id, key)
        return get_nested_value(user_key_path, default=admin_value)

    @staticmethod
    def get_general_name(user_id: str) -> str:
        return ConfigModel._get_value(user_id, "general_name", default="standard instance")

    @staticmethod
    def set_general_name(user_id: str, value: str) -> None:
        ConfigModel._set_value(user_id, "general_name", value)

    @staticmethod
    def get_general_language(user_id: str) -> str:
        return ConfigModel._get_value(user_id, "general_language", default="default")

    @staticmethod
    def set_general_language(user_id, value: str) -> None:
        ConfigModel._set_value(user_id, "general_language", value)

    @staticmethod
    def get_llm_interfaces(user_id: str) -> list[InterfaceLLM]:
        interfaces = list[InterfaceLLM]()

        value = ConfigModel._get_value(user_id, "llm_interfaces", default=dict[str, dict[str, any]]())
        for each_dict in value.values():
            each_interface = ConfigModel._llm_from_dict(each_dict)
            interfaces.append(each_interface)

        return interfaces

    @staticmethod
    def add_llm_interface(user_id: str, interface: InterfaceLLM) -> None:
        user_access = ConfigModel.get_user_access(user_id, "llm_interfaces")
        if not user_access and user_id != "ADMIN":
            return

        value = ConfigModel._get_value(user_id, "llm_interfaces", default=dict[str, dict[str, any]]())
        llm_dict = dataclasses.asdict(interface)
        name = llm_dict["name"]
        value[name] = llm_dict
        ConfigModel._set_value(user_id, "llm_interfaces", value)

    @staticmethod
    def remove_llm_interface(user_id: str, llm_interface_name: str) -> None:
        user_access = ConfigModel.get_user_access(user_id, "llm_interfaces")
        if not user_access and user_id != "ADMIN":
            return

        value = ConfigModel._get_value(user_id, "llm_interfaces", default=dict[str, dict[str, any]]())
        try:
            del value[llm_interface_name]
        except KeyError as e:
            logger.error(f"Could not remove {llm_interface_name} from {user_id}: {e}")

        ConfigModel._set_value(user_id, "llm_interfaces", value)

    @staticmethod
    def get_data_interfaces(user_id: str) -> list[InterfaceData]:
        interfaces = list[InterfaceData]()

        value = ConfigModel._get_value(user_id, "data_interfaces", default=dict[str, dict[str, any]]())
        for each_dict in value.values():
            each_interface = ConfigModel._data_from_dict(each_dict)
            interfaces.append(each_interface)

        return interfaces

    @staticmethod
    def add_data_interface(user_id: str, interface: InterfaceData) -> None:
        user_access = ConfigModel.get_user_access(user_id, "data_interfaces")
        if not user_access and user_id != "ADMIN":
            return

        value = ConfigModel._get_value(user_id, "data_interfaces", default=dict[str, dict[str, any]]())
        data_dict = dataclasses.asdict(interface)
        name = data_dict["name"]
        value[name] = data_dict
        ConfigModel._set_value(user_id, "data_interfaces", value)

    @staticmethod
    def remove_data_interface(user_id: str, key_name: str) -> None:
        user_access = ConfigModel.get_user_access(user_id, "data_interfaces")
        if not user_access and user_id != "ADMIN":
            return

        value = ConfigModel._get_value(user_id, "data_interfaces", default=dict[str, dict[str, any]]())
        try:
            del value[key_name]
        except KeyError as e:
            logger.error(f"Could not remove {key_name} from {user_id}: {e}")

        ConfigModel._set_value(user_id, "data_interfaces", value)

    @staticmethod
    def get_extraction_llm(user_id: str) -> InterfaceLLM | None:
        value = ConfigModel._get_value(user_id, "extraction_llm")
        if value is None:
            return None
        interface = ConfigModel._llm_from_dict(value)
        return interface

    @staticmethod
    def set_extraction_llm(user_id: str, value: InterfaceLLM) -> None:
        interface_llm = dataclasses.asdict(value)
        ConfigModel._set_value(user_id, "extraction_llm", interface_llm)

    @staticmethod
    def get_extraction_claims(user_id: str) -> int:
        value = ConfigModel._get_value(user_id, "extraction_claims", default=3)
        return value

    @staticmethod
    def set_extraction_claims(user_id: str, value: int) -> None:
        ConfigModel._set_value(user_id, "extraction_claims", value)

    @staticmethod
    def get_retrieval_llm(user_id: str, self) -> InterfaceLLM | None:
        value = ConfigModel._get_value(user_id, "retrieval_llm")
        if value is None:
            return None
        interface = ConfigModel._llm_from_dict(value)
        return interface

    @staticmethod
    def set_retrieval_llm(user_id: str, value: InterfaceLLM) -> None:
        interface_llm = dataclasses.asdict(value)
        ConfigModel._set_value(user_id, "retrieval_llm", interface_llm)

    @staticmethod
    def get_retrieval_data(user_id: str) -> InterfaceData | None:
        value = ConfigModel._get_value(user_id, "retrieval_data")
        if value is None:
            return None
        interface = ConfigModel._data_from_dict(value)
        return interface

    @staticmethod
    def set_retrieval_data(user_id: str, value: InterfaceData) -> None:
        interface_data = dataclasses.asdict(value)
        ConfigModel._set_value(user_id, "retrieval_data", interface_data)

    @staticmethod
    def get_retrieval_max_documents(user_id: str) -> int:
        value = ConfigModel._get_value(user_id, "retrieval_max_documents", default=10)
        return value

    @staticmethod
    def set_retrieval_max_documents(user_id: str, value: int) -> None:
        ConfigModel._set_value(user_id, "retrieval_max_documents", value)

    @staticmethod
    def get_comparison_llm(user_id: str) -> InterfaceLLM | None:
        value = ConfigModel._get_value(user_id, "comparison_llm")
        if value is None:
            return None
        interface = ConfigModel._llm_from_dict(value)
        return interface

    @staticmethod
    def set_comparison_llm(user_id: str, value: InterfaceLLM) -> None:
        comparison_llm = dataclasses.asdict(value)
        ConfigModel._set_value(user_id, "comparison_llm", comparison_llm)

    @staticmethod
    def get_comparison_data(user_id: str) -> InterfaceData | None:
        value = ConfigModel._get_value(user_id, "comparison_data")
        if value is None:
            return None

        interface = ConfigModel._data_from_dict(value)
        return interface

    @staticmethod
    def set_comparison_data(user_id: str, value: InterfaceData) -> None:
        comparison_data = dataclasses.asdict(value)
        ConfigModel._set_value(user_id, "comparison_data", comparison_data)


@contextmanager
def store_deprecated(element_type: type[Element], set_value: Callable[[str], any], get_value: Callable[[], any], **kwargs) -> None:
    timer: ui.timer | None = None

    def update_timer(callback: Callable[..., any]) -> None:
        nonlocal timer
        if timer is not None:
            timer.cancel()
            del timer
        timer = ui.timer(interval=1.0, active=True, once=True, callback=callback)

    def delay(value: any, validation: dict[str, Callable[[str], bool]] | None = None) -> None:
        if validation is None or all(each_validation(value) for each_validation in validation.values()):
            def set_storage() -> None:
                set_value(value)
                ui.notify(f"{kwargs.get('label', 'Setting')} saved", timeout=500)  # , progress=True)

            update_timer(set_storage)

    last_value = get_value()
    with element_type(
        value=last_value, **kwargs,
        on_change=lambda event: delay(event.value, validation=kwargs.get("validation"))
    ) as element:
        yield element


UiElement = TypeVar("UiElement", bound=Element)


class Store:
    def __init__(
            self,
            element_type: type[UiElement], set_value: Callable[[str], any], default: any, delay: float = 1.0,
            **kwargs):
        self.element_type = element_type
        self.set_value = set_value
        self.default = default
        self.delay = delay
        self.kwargs = kwargs
        self.timer: ui.timer | None = None

    def __enter__(self) -> UiElement:
        def update_timer(callback: Callable[..., any]) -> None:
            if self.timer is not None:
                self.timer.cancel()
            self.timer = ui.timer(interval=self.delay, active=True, once=True, callback=callback)

        def delay(value: any, validation: dict[str, Callable[[str], bool]] | None = None) -> None:
            if validation is None or all(each_validation(value) for each_validation in validation.values()):
                def set_storage() -> None:
                    self.set_value(value)
                    name = self.kwargs.get('label', self.kwargs.get('text', 'Setting'))
                    ui.notify(f"{name} updated", timeout=500)

                update_timer(set_storage)

        element = self.element_type(
            value=self.default, **self.kwargs,
            on_change=lambda event: delay(event.value, validation=self.kwargs.get("validation"))
        )

        return element

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.timer is not None:
            self.timer.cancel()


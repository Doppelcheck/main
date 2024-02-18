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


class AccessModel:

    @staticmethod
    def _access_path(key: str) -> tuple[str, ...]:
        return "users", "access", key

    @staticmethod
    def _get_user_access(key: str) -> bool:
        key_path = AccessModel._access_path(key)
        return get_nested_value(key_path, default=False)

    @staticmethod
    def _set_user_access(key: str, value: bool) -> None:
        key_path = AccessModel._access_path(key)
        set_nested_value(key_path, value)

    @staticmethod
    def set_access_name(user_access: bool) -> None:
        AccessModel._set_user_access("name", user_access)

    @staticmethod
    def get_access_name() -> bool:
        return AccessModel._get_user_access("name")

    @staticmethod
    def set_access_language(user_access: bool) -> None:
        AccessModel._set_user_access("language", user_access)

    @staticmethod
    def get_access_language() -> bool:
        return AccessModel._get_user_access("language")

    @staticmethod
    def set_extraction_llm(user_access: bool) -> None:
        AccessModel._set_user_access("extraction_llm_name", user_access)

    @staticmethod
    def get_extraction_llm() -> bool:
        return AccessModel._get_user_access("extraction_llm_name")

    @staticmethod
    def set_extraction_claims(user_access: bool) -> None:
        AccessModel._set_user_access("extraction_claims", user_access)

    @staticmethod
    def get_extraction_claims() -> bool:
        return AccessModel._get_user_access("extraction_claims")

    @staticmethod
    def set_retrieval_llm(user_access: bool) -> None:
        AccessModel._set_user_access("retrieval_llm_name", user_access)

    @staticmethod
    def get_retrieval_llm() -> bool:
        return AccessModel._get_user_access("retrieval_llm_name")

    @staticmethod
    def set_retrieval_data(user_access: bool) -> None:
        AccessModel._set_user_access("retrieval_data_name", user_access)

    @staticmethod
    def get_retrieval_data() -> bool:
        return AccessModel._get_user_access("retrieval_data_name")

    @staticmethod
    def set_retrieval_max_documents(user_access: bool) -> None:
        AccessModel._set_user_access("retrieval_max_documents", user_access)

    @staticmethod
    def get_retrieval_max_documents() -> bool:
        return AccessModel._get_user_access("retrieval_max_documents")

    @staticmethod
    def set_comparison_llm(user_access: bool) -> None:
        AccessModel._set_user_access("comparison_llm_name", user_access)

    @staticmethod
    def get_comparison_llm() -> bool:
        return AccessModel._get_user_access("comparison_llm_name")

    @staticmethod
    def set_comparison_data(user_access: bool) -> None:
        AccessModel._set_user_access("comparison_data_name", user_access)

    @staticmethod
    def get_comparison_data() -> bool:
        return AccessModel._get_user_access("comparison_data_name")

    @staticmethod
    def set_add_llm(user_access: bool) -> None:
        AccessModel._set_user_access("add_llm", user_access)

    @staticmethod
    def get_add_llm() -> bool:
        return AccessModel._get_user_access("add_llm")

    @staticmethod
    def set_remove_llm(user_access: bool) -> None:
        AccessModel._set_user_access("remove_llm", user_access)

    @staticmethod
    def get_remove_llm() -> bool:
        return AccessModel._get_user_access("remove_llm")

    @staticmethod
    def set_add_data(user_access: bool) -> None:
        AccessModel._set_user_access("add_data", user_access)

    @staticmethod
    def get_add_data() -> bool:
        return AccessModel._get_user_access("add_data")

    @staticmethod
    def set_remove_data(user_access: bool) -> None:
        AccessModel._set_user_access("remove_data", user_access)

    @staticmethod
    def get_remove_data() -> bool:
        return AccessModel._get_user_access("remove_data")


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
    def _set_value(user_id: str, key: str, value: any) -> None:
        key_path = ConfigModel._user_path(user_id, key)
        set_nested_value(key_path, value)

    @staticmethod
    def _get_value(user_id: str, key: str, default: any = None) -> any:
        user_key_path = ConfigModel._user_path(user_id, key)
        return get_nested_value(user_key_path, default=default)

    @staticmethod
    def get_llm_interface(user_id: str, interface_name: str) -> InterfaceLLM | None:
        value = ConfigModel._get_value(user_id, "llm_interfaces", default=dict[str, dict[str, any]]())
        interface_dict = value.get(interface_name)
        if interface_dict is None:
            logger.error(f"LLM interface {interface_name} not found")
            return None

        interface = ConfigModel._llm_from_dict(interface_dict)
        return interface

    @staticmethod
    def get_data_interface(user_id: str, name: str) -> InterfaceData | None:
        value = ConfigModel._get_value(user_id, "data_interfaces", default=dict[str, dict[str, any]]())
        interface_dict = value.get(name)
        if interface_dict is None:
            logger.error(f"Data interface {name} not found")
            return None

        interface = ConfigModel._data_from_dict(interface_dict)
        return interface

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
        value = ConfigModel._get_value(user_id, "llm_interfaces", default=dict[str, dict[str, any]]())
        llm_dict = dataclasses.asdict(interface)
        name = llm_dict["name"]
        value[name] = llm_dict
        ConfigModel._set_value(user_id, "llm_interfaces", value)

    @staticmethod
    def remove_llm_interface(user_id: str, llm_interface_name: str) -> None:
        is_admin = user_id == "ADMIN"

        value = ConfigModel._get_value(user_id, "llm_interfaces", default=dict[str, dict[str, any]]())
        interface = value.get(llm_interface_name)
        if not is_admin and interface["from_admin"]:
            logger.error(f"User {user_id} cannot remove admin data interface {llm_interface_name}.")
            return

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
        value = ConfigModel._get_value(user_id, "data_interfaces", default=dict[str, dict[str, any]]())
        data_dict = dataclasses.asdict(interface)
        name = data_dict["name"]
        value[name] = data_dict
        ConfigModel._set_value(user_id, "data_interfaces", value)

    @staticmethod
    def remove_data_interface(user_id: str, data_interface_name: str) -> None:
        is_admin = user_id == "ADMIN"

        value = ConfigModel._get_value(user_id, "data_interfaces", default=dict[str, dict[str, any]]())
        interface = value.get(data_interface_name)
        if not is_admin and interface["from_admin"]:
            logger.error(f"User {user_id} cannot remove admin data interface {data_interface_name}.")
            return

        try:
            del value[data_interface_name]
        except KeyError as e:
            logger.error(f"Could not remove {data_interface_name} from {user_id}: {e}")

        ConfigModel._set_value(user_id, "data_interfaces", value)

    @staticmethod
    def get_extraction_llm(user_id: str) -> InterfaceLLM | None:
        interface_name = ConfigModel._get_value(user_id, "extraction_llm")
        if interface_name is None:
            logger.error(f"No extraction LLM interface set for {user_id}")
            return None

        interface = ConfigModel.get_llm_interface(user_id, interface_name)
        return interface

    @staticmethod
    def set_extraction_llm(user_id: str, interface_name: str) -> None:
        ConfigModel._set_value(user_id, "extraction_llm", interface_name)

    @staticmethod
    def get_extraction_claims(user_id: str) -> int:
        value = ConfigModel._get_value(user_id, "extraction_claims", default=3)
        return value

    @staticmethod
    def set_extraction_claims(user_id: str, value: int) -> None:
        ConfigModel._set_value(user_id, "extraction_claims", value)

    @staticmethod
    def get_retrieval_llm(user_id: str) -> InterfaceLLM | None:
        interface_name = ConfigModel._get_value(user_id, "retrieval_llm")
        if interface_name is None:
            logger.error(f"No retrieval LLM interface set for {user_id}")
            return None

        interface = ConfigModel.get_llm_interface(user_id, interface_name)
        return interface

    @staticmethod
    def set_retrieval_llm(user_id: str, interface_name: str) -> None:
        ConfigModel._set_value(user_id, "retrieval_llm", interface_name)

    @staticmethod
    def get_retrieval_data(user_id: str) -> InterfaceData | None:
        interface_name = ConfigModel._get_value(user_id, "retrieval_data")
        if interface_name is None:
            logger.error(f"No retrieval data interface set for {user_id}")
            return None

        interface = ConfigModel.get_llm_interface(user_id, interface_name)
        return interface

    @staticmethod
    def set_retrieval_data(user_id: str, interface_name: str) -> None:
        ConfigModel._set_value(user_id, "retrieval_data", interface_name)

    @staticmethod
    def get_retrieval_max_documents(user_id: str) -> int:
        value = ConfigModel._get_value(user_id, "retrieval_max_documents", default=10)
        return value

    @staticmethod
    def set_retrieval_max_documents(user_id: str, value: int) -> None:
        ConfigModel._set_value(user_id, "retrieval_max_documents", value)

    @staticmethod
    def get_comparison_llm(user_id: str) -> InterfaceLLM | None:
        interface_name = ConfigModel._get_value(user_id, "comparison_llm")
        if interface_name is None:
            logger.error(f"No comparison LLM interface set for {user_id}")
            return None

        interface = ConfigModel.get_llm_interface(user_id, interface_name)
        return interface

    @staticmethod
    def set_comparison_llm(user_id: str, interface_name: str) -> None:
        ConfigModel._set_value(user_id, "comparison_llm", interface_name)

    @staticmethod
    def get_comparison_data(user_id: str) -> InterfaceData | None:
        interface_name = ConfigModel._get_value(user_id, "comparison_data")
        if interface_name is None:
            logger.error(f"No comparison data interface set for {user_id}")
            return None

        interface = ConfigModel.get_llm_interface(user_id, interface_name)
        return interface

    @staticmethod
    def set_comparison_data(user_id: str, interface_name: str) -> None:
        ConfigModel._set_value(user_id, "comparison_data", interface_name)


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
            element_type: type[UiElement], set_value: Callable[[any], any], default: any, delay: float = 1.0,
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


def get_interface(interfaces: list[dict[str, any]], name: str) -> dict[str, any] | None:
    for each_interface in interfaces:
        if each_interface[name] == name:
            return each_interface

    logger.error(f"Interface {name} not found")
    return None

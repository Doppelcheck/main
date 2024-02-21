from __future__ import annotations

import json
from typing import Callable

from loguru import logger
from nicegui import ui
from nicegui.elements.mixins.text_element import TextElement
from nicegui.elements.mixins.validation_element import ValidationElement
from nicegui.elements.mixins.value_element import ValueElement
from nicegui.events import GenericEventArguments

from tools.data_access import get_nested_value, set_nested_value
from tools.plugins.abstract import InterfaceLLMConfig, InterfaceDataConfig


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
    def get_llm_interface(user_id: str, interface_name: str) -> InterfaceLLMConfig | None:
        llm_interface_dicts = ConfigModel._get_value(
            "ADMIN", "llm_interfaces", default=dict[str, dict[str, any]]()
        )
        user_llm_interface_dicts = ConfigModel._get_value(
            user_id, "llm_interfaces", default=dict[str, dict[str, any]]()
        )
        llm_interface_dicts.update(user_llm_interface_dicts)

        interface_dict = llm_interface_dicts.get(interface_name)
        if interface_dict is None:
            logger.error(f"LLM interface {interface_name} not found")
            return None

        interface = InterfaceLLMConfig.from_object_dict(interface_dict)
        return interface

    @staticmethod
    def get_data_interface(user_id: str, name: str) -> InterfaceDataConfig | None:
        data_interface_dicts = ConfigModel._get_value(
            "ADMIN", "data_interfaces", default=dict[str, dict[str, any]]()
        )
        user_data_interface_dicts = ConfigModel._get_value(
            user_id, "data_interfaces", default=dict[str, dict[str, any]]()
        )
        data_interface_dicts.update(user_data_interface_dicts)

        interface_dict = data_interface_dicts.get(name)
        if interface_dict is None:
            logger.error(f"Data interface {name} not found")
            return None

        interface = InterfaceDataConfig.from_object_dict(interface_dict)
        return interface

    @staticmethod
    def get_general_name(user_id: str) -> str:
        return ConfigModel._get_value(
            user_id, "general_name",
            default=ConfigModel._get_value("ADMIN", "general_name", default="standard instance")
        )

    @staticmethod
    def set_general_name(user_id: str, value: str) -> None:
        ConfigModel._set_value(user_id, "general_name", value)

    @staticmethod
    def get_general_language(user_id: str) -> str:
        return ConfigModel._get_value(
            user_id, "general_language",
            default=ConfigModel._get_value("ADMIN", "general_language", default="default")
        )

    @staticmethod
    def set_general_language(user_id, value: str) -> None:
        ConfigModel._set_value(user_id, "general_language", value)

    @staticmethod
    def get_llm_interfaces(user_id: str) -> list[InterfaceLLMConfig]:
        interface_dicts = ConfigModel._get_value(user_id, "llm_interfaces", default=dict[str, dict[str, any]]())
        if user_id != "ADMIN":
            admin_interfaces = ConfigModel._get_value("ADMIN", "llm_interfaces", default=dict[str, dict[str, any]]())
            interface_dicts.update(admin_interfaces)

        interfaces = list[InterfaceLLMConfig]()

        for each_dict in interface_dicts.values():
            each_interface = InterfaceLLMConfig.from_object_dict(each_dict)
            interfaces.append(each_interface)

        return interfaces

    @staticmethod
    def add_llm_interface(user_id: str, interface: InterfaceLLMConfig) -> None:
        value = ConfigModel._get_value(user_id, "llm_interfaces", default=dict[str, dict[str, any]]())
        llm_dict = interface.to_object_dict()
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
    def get_data_interfaces(user_id: str) -> list[InterfaceDataConfig]:
        interface_dicts = ConfigModel._get_value("ADMIN", "data_interfaces", default=dict[str, dict[str, any]]())
        if user_id != "ADMIN":
            admin_interfaces = ConfigModel._get_value(user_id, "data_interfaces", default=dict[str, dict[str, any]]())
            interface_dicts.update(admin_interfaces)

        interfaces = list[InterfaceDataConfig]()

        for each_dict in interface_dicts.values():
            each_interface = InterfaceDataConfig.from_object_dict(each_dict)
            interfaces.append(each_interface)

        return interfaces

    @staticmethod
    def add_data_interface(user_id: str, interface: InterfaceDataConfig) -> None:
        value = ConfigModel._get_value(user_id, "data_interfaces", default=dict[str, dict[str, any]]())
        data_dict = interface.to_object_dict()
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
    def get_extraction_llm(user_id: str) -> InterfaceLLMConfig | None:
        interface_name = ConfigModel._get_value(user_id, "extraction_llm")
        if interface_name is not None:
            interface = ConfigModel.get_llm_interface(user_id, interface_name)
            return interface

        interface_name = ConfigModel._get_value("ADMIN", "extraction_llm")
        if interface_name is not None:
            interface = ConfigModel.get_llm_interface(user_id, interface_name)
            return interface

        interfaces = ConfigModel.get_llm_interfaces(user_id)
        if len(interfaces) > 0:
            return interfaces[0]

        interfaces = ConfigModel.get_llm_interfaces("ADMIN")
        if len(interfaces) > 0:
            return interfaces[0]

        return None

    @staticmethod
    def set_extraction_llm(user_id: str, interface_name: str) -> None:
        ConfigModel._set_value(user_id, "extraction_llm", interface_name)

    @staticmethod
    def get_extraction_claims(user_id: str) -> int:
        value = ConfigModel._get_value(
            user_id, "extraction_claims",
            default=ConfigModel._get_value("ADMIN", "extraction_claims", default=3)
        )
        return value

    @staticmethod
    def set_extraction_claims(user_id: str, value: int) -> None:
        ConfigModel._set_value(user_id, "extraction_claims", value)

    @staticmethod
    def get_retrieval_llm(user_id: str) -> InterfaceLLMConfig | None:
        interface_name = ConfigModel._get_value(user_id, "retrieval_llm")
        if interface_name is not None:
            return ConfigModel.get_llm_interface(user_id, interface_name)

        interface_name = ConfigModel._get_value("ADMIN", "retrieval_llm")
        if interface_name is not None:
            return ConfigModel.get_llm_interface(user_id, interface_name)

        interfaces = ConfigModel.get_llm_interfaces(user_id)
        if len(interfaces) > 0:
            return interfaces[0]

        interfaces = ConfigModel.get_llm_interfaces("ADMIN")
        if len(interfaces) > 0:
            return interfaces[0]

        return None

    @staticmethod
    def set_retrieval_llm(user_id: str, interface_name: str) -> None:
        ConfigModel._set_value(user_id, "retrieval_llm", interface_name)

    @staticmethod
    def get_retrieval_data(user_id: str) -> InterfaceDataConfig | None:
        interface_name = ConfigModel._get_value(user_id, "retrieval_data")
        if interface_name is not None:
            return ConfigModel.get_data_interface(user_id, interface_name)

        interface_name = ConfigModel._get_value("ADMIN", "retrieval_data")
        if interface_name is not None:
            return ConfigModel.get_data_interface(user_id, interface_name)

        interfaces = ConfigModel.get_data_interfaces(user_id)
        if len(interfaces) > 0:
            return interfaces[0]

        interfaces = ConfigModel.get_data_interfaces("ADMIN")
        if len(interfaces) > 0:
            return interfaces[0]

        return None

    @staticmethod
    def set_retrieval_data(user_id: str, interface_name: str) -> None:
        ConfigModel._set_value(user_id, "retrieval_data", interface_name)

    @staticmethod
    def get_retrieval_max_documents(user_id: str) -> int:
        value = ConfigModel._get_value(
            user_id, "retrieval_max_documents",
            default=ConfigModel._get_value("ADMIN", "retrieval_max_documents", default=10)
        )
        return value

    @staticmethod
    def set_retrieval_max_documents(user_id: str, value: int) -> None:
        ConfigModel._set_value(user_id, "retrieval_max_documents", value)

    @staticmethod
    def get_comparison_llm(user_id: str) -> InterfaceLLMConfig | None:
        interface_name = ConfigModel._get_value(user_id, "comparison_llm")
        if interface_name is not None:
            return ConfigModel.get_llm_interface(user_id, interface_name)

        interface_name = ConfigModel._get_value("ADMIN", "comparison_llm")
        if interface_name is not None:
            return ConfigModel.get_llm_interface(user_id, interface_name)

        interfaces = ConfigModel.get_llm_interfaces(user_id)
        if len(interfaces) > 0:
            return interfaces[0]

        interfaces = ConfigModel.get_llm_interfaces("ADMIN")
        if len(interfaces) > 0:
            return interfaces[0]

        return None

    @staticmethod
    def set_comparison_llm(user_id: str, interface_name: str) -> None:
        ConfigModel._set_value(user_id, "comparison_llm", interface_name)

    @staticmethod
    def get_comparison_data(user_id: str) -> InterfaceDataConfig | None:
        interface_name = ConfigModel._get_value(user_id, "comparison_data")
        if interface_name is not None:
            return ConfigModel.get_data_interface(user_id, interface_name)

        interface_name = ConfigModel._get_value("ADMIN", "comparison_data")
        if interface_name is not None:
            return ConfigModel.get_data_interface(user_id, interface_name)

        interfaces = ConfigModel.get_data_interfaces(user_id)
        if len(interfaces) > 0:
            return interfaces[0]

        interfaces = ConfigModel.get_data_interfaces("ADMIN")
        if len(interfaces) > 0:
            return interfaces[0]

        return None

    @staticmethod
    def set_comparison_data(user_id: str, interface_name: str) -> None:
        ConfigModel._set_value(user_id, "comparison_data", interface_name)


class Store:
    def __init__(self, element: ValueElement, set_value: Callable[[any], any], delay: float = 1.0):
        self.element = element
        self.set_value = set_value
        self.delay = delay
        self.timer: ui.timer | None = None

    def _update_timer(self, callback: Callable[..., any]) -> None:
        if self.timer is not None:
            self.timer.cancel()
        self.timer = ui.timer(interval=self.delay, active=True, once=True, callback=callback)

    def _set_storage(self, value: any, name: str | None = None) -> None:
        name = "Value" if name is None else f"'{name}'"
        self.set_value(value)
        ui.notify(f"{name} set to {json.dumps(value)}", timeout=500)

    def _delay_validation(self, event: GenericEventArguments, validation: dict[str, Callable[[str], bool]] | None = None) -> None:
        value = self.element.value
        if isinstance(self.element, TextElement):
            name = self.element.text
        else:
            name = event.sender._props.get("label")
        if validation is not None and all(each_validation(value) for each_validation in validation.values()):
            self._update_timer(lambda: self._set_storage(value, name=name))

    def _delay(self, event: GenericEventArguments) -> None:
        value = self.element.value
        if isinstance(self.element, TextElement):
            name = self.element.text
        else:
            name = event.sender._props.get("label")
        self._update_timer(lambda: self._set_storage(value, name=name))

    def __enter__(self) -> Store:
        if isinstance(self.element, ValidationElement):
            def delay(value: any) -> None:
                assert isinstance(self.element, ValidationElement)
                self._delay_validation(value, validation=self.element.validation)
        else:
            delay = self._delay

        self.element.on("update:model-value", lambda event: delay(event))

        return self

    def __exit__(self, exc_type: type | None, exc_value: Exception | None, traceback: any) -> bool | None:
        if self.timer is not None:
            self.timer.cancel()

        return


def get_interface(interfaces: list[dict[str, any]], name: str) -> dict[str, any] | None:
    for each_interface in interfaces:
        if each_interface[name] == name:
            return each_interface

    logger.error(f"Interface {name} not found")
    return None

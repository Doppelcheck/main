from __future__ import annotations

import json
from typing import Callable

from loguru import logger
from nicegui import ui
from nicegui.elements.mixins.text_element import TextElement
from nicegui.elements.mixins.validation_element import ValidationElement
from nicegui.elements.mixins.value_element import ValueElement
from nicegui.events import GenericEventArguments

from model.data_access import get_nested_value, set_nested_value
from plugins.abstract import InterfaceLLMConfig, InterfaceDataConfig
from tools.text_processing import truncate_text


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

    @staticmethod
    def set_extraction_prompt(value: bool) -> None:
        return AccessModel._set_user_access("change_extraction_prompt", value)

    @staticmethod
    def get_extraction_prompt() -> bool:
        return AccessModel._get_user_access("change_extraction_prompt")

    @staticmethod
    def set_comparison_prompt(value: bool) -> None:
        return AccessModel._set_user_access("change_comparison_prompt", value)

    @staticmethod
    def get_comparison_prompt() -> bool:
        return AccessModel._get_user_access("change_comparison_prompt")



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
    def get_llm_interface(user_id: str, interface_name: str, is_admin: bool) -> InterfaceLLMConfig | None:
        interfaces = ConfigModel.get_llm_interfaces(user_id, is_admin)
        for each_interface in interfaces:
            if each_interface.name == interface_name:
                return each_interface
        return None

    @staticmethod
    def get_data_interface(user_id: str, name: str, is_admin: bool) -> InterfaceDataConfig | None:
        interfaces = ConfigModel.get_data_interfaces(user_id, is_admin)
        for each_interface in interfaces:
            if each_interface.name == name:
                return each_interface
        return None

    @staticmethod
    def get_general_name(user_id: str, is_admin: bool) -> str:
        admin_value = ConfigModel._get_value("ADMIN", "general_name", default="Doppelcheck")
        if is_admin:
            return admin_value
        return ConfigModel._get_value(user_id,  "general_name", default=admin_value)

    @staticmethod
    def set_general_name(user_id: str, value: str) -> None:
        ConfigModel._set_value(user_id, "general_name", value)

    @staticmethod
    def get_general_language(user_id: str, is_admin: bool) -> str:
        admin_value = ConfigModel._get_value("ADMIN", "general_language", default="default")
        if is_admin:
            return admin_value
        return ConfigModel._get_value(user_id, "general_language", default=admin_value)

    @staticmethod
    def set_general_language(user_id, value: str) -> None:
        ConfigModel._set_value(user_id, "general_language", value)

    @classmethod
    def get_extraction_prompt(cls, user_id: str, is_admin: bool) -> str:
        default = (
            "The text is a news report. Extract its key factual claims, converting any relative time and place "
            "references to their absolute counterparts. Exclude examples, questions, opinions, personal feelings, "
            "prose, advertisements, and other non-factual elements."
        )
        admin_value = cls._get_value("ADMIN", "extraction_prompt", default=default)
        if is_admin:
            return admin_value
        return cls._get_value(user_id, "extraction_prompt", default=admin_value)

    @classmethod
    def set_extraction_prompt(cls, user_id: str, value: str) -> None:
        cls._set_value(user_id, "extraction_prompt", value)

    @staticmethod
    def get_comparison_prompt(user_id: str, is_admin: bool) -> str:
        default = (
            "The keypoint is a claim and the source reference is a news report. Now rate the claim based on the "
            "report by picking one of the following options:\n"
            "\n"
            "  \"🟩 Strong support\": report strongly supports claim\n"
            "  \"🟨 Some support\": report generally supports claim, with limitations or minor contradictions\n"
            "  \"⬜️ No mention\": report neither clearly supports nor contradicts claim, or is unclear\n"
            "  \"🟧​ Some contradiction\": report contradicts claim but not completely\n"
            "  \"🟥 Strong contradiction\": report is in strong opposition to claim\n"
            "\n"
            "IMPORTANT: Do not assess the correctness of either claim or report, determine your rating only based on "
            "how well the claim holds up against the news report.\n"
        )

        admin_value = ConfigModel._get_value("ADMIN", "comparison_prompt", default=default)
        if is_admin:
            return admin_value
        return ConfigModel._get_value(user_id, "comparison_prompt", default=admin_value)

    @staticmethod
    def set_comparison_prompt(user_id: str, value: str) -> None:
        ConfigModel._set_value(user_id, "comparison_prompt", value)


    @staticmethod
    def get_llm_interfaces(user_id: str, is_admin: bool) -> list[InterfaceLLMConfig]:
        interface_dicts = ConfigModel._get_value("ADMIN", "llm_interfaces", default=dict[str, dict[str, any]]())
        if not is_admin:
            user_interfaces = ConfigModel._get_value(user_id, "llm_interfaces", default=dict[str, dict[str, any]]())
            interface_dicts.update(user_interfaces)

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
    def remove_llm_interface(user_id: str, llm_interface_name: str, is_admin: bool) -> None:
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
    def get_data_interfaces(user_id: str, is_admin: bool) -> list[InterfaceDataConfig]:
        interface_dicts = ConfigModel._get_value("ADMIN", "data_interfaces", default=dict[str, dict[str, any]]())
        if not is_admin:
            user_interfaces = ConfigModel._get_value(user_id, "data_interfaces", default=dict[str, dict[str, any]]())
            interface_dicts.update(user_interfaces)

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
    def remove_data_interface(user_id: str, data_interface_name: str, is_admin: bool) -> None:
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
    def get_extraction_llm(user_id: str, is_admin: bool) -> InterfaceLLMConfig | None:
        interface_name = ConfigModel._get_value(user_id, "extraction_llm")
        if interface_name is not None:
            interface = ConfigModel.get_llm_interface(user_id, interface_name, is_admin)
            return interface

        interface_name = ConfigModel._get_value("ADMIN", "extraction_llm")
        if interface_name is not None:
            interface = ConfigModel.get_llm_interface(user_id, interface_name, is_admin)
            return interface

        interfaces = ConfigModel.get_llm_interfaces(user_id, is_admin)
        if len(interfaces) > 0:
            return interfaces[0]

        interfaces = ConfigModel.get_llm_interfaces("ADMIN", is_admin)
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
    def get_retrieval_llm(user_id: str, is_admin: bool) -> InterfaceLLMConfig | None:
        interface_name = ConfigModel._get_value(user_id, "retrieval_llm")
        if interface_name is not None:
            return ConfigModel.get_llm_interface(user_id, interface_name, is_admin)

        interface_name = ConfigModel._get_value("ADMIN", "retrieval_llm")
        if interface_name is not None:
            return ConfigModel.get_llm_interface(user_id, interface_name, is_admin)

        interfaces = ConfigModel.get_llm_interfaces(user_id, is_admin)
        if len(interfaces) > 0:
            return interfaces[0]

        interfaces = ConfigModel.get_llm_interfaces("ADMIN", is_admin)
        if len(interfaces) > 0:
            return interfaces[0]

        return None

    @staticmethod
    def set_retrieval_llm(user_id: str, interface_name: str) -> None:
        ConfigModel._set_value(user_id, "retrieval_llm", interface_name)

    @staticmethod
    def get_retrieval_data(user_id: str, is_admin: bool) -> InterfaceDataConfig | None:
        interface_name = ConfigModel._get_value(user_id, "retrieval_data")
        if interface_name is not None:
            return ConfigModel.get_data_interface(user_id, interface_name, is_admin)

        interface_name = ConfigModel._get_value("ADMIN", "retrieval_data")
        if interface_name is not None:
            return ConfigModel.get_data_interface(user_id, interface_name, is_admin)

        interfaces = ConfigModel.get_data_interfaces(user_id, is_admin)
        if len(interfaces) > 0:
            return interfaces[0]

        interfaces = ConfigModel.get_data_interfaces("ADMIN", is_admin)
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
    def get_comparison_llm(user_id: str, is_admin: bool) -> InterfaceLLMConfig | None:
        interface_name = ConfigModel._get_value(user_id, "comparison_llm")
        if interface_name is not None:
            return ConfigModel.get_llm_interface(user_id, interface_name, is_admin)

        interface_name = ConfigModel._get_value("ADMIN", "comparison_llm")
        if interface_name is not None:
            return ConfigModel.get_llm_interface(user_id, interface_name, is_admin)

        interfaces = ConfigModel.get_llm_interfaces(user_id, is_admin)
        if len(interfaces) > 0:
            return interfaces[0]

        interfaces = ConfigModel.get_llm_interfaces("ADMIN", is_admin)
        if len(interfaces) > 0:
            return interfaces[0]

        return None

    @staticmethod
    def set_comparison_llm(user_id: str, interface_name: str) -> None:
        ConfigModel._set_value(user_id, "comparison_llm", interface_name)

    @staticmethod
    def get_comparison_data(user_id: str, is_admin: bool) -> InterfaceDataConfig | None:
        interface_name = ConfigModel._get_value(user_id, "comparison_data")
        if interface_name is not None:
            return ConfigModel.get_data_interface(user_id, interface_name, is_admin)

        interface_name = ConfigModel._get_value("ADMIN", "comparison_data")
        if interface_name is not None:
            return ConfigModel.get_data_interface(user_id, interface_name, is_admin)

        interfaces = ConfigModel.get_data_interfaces(user_id, is_admin)
        if len(interfaces) > 0:
            return interfaces[0]

        interfaces = ConfigModel.get_data_interfaces("ADMIN", is_admin)
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

    def _set_storage(self, name: str | None = None) -> None:
        value = self.element.value
        name = "Value" if name is None else f"'{name}'"
        self.set_value(value)
        truncated = truncate_text(json.dumps(value), 50)
        ui.notify(f"{name} set to {truncated}", timeout=500)

    def _delay_validation(self, event: GenericEventArguments, validation: dict[str, Callable[[str], bool]] | None = None) -> None:
        value = self.element.value
        if isinstance(self.element, TextElement):
            name = self.element.text
        else:
            name = event.sender._props.get("label")
        if validation is not None and all(each_validation(value) for each_validation in validation.values()):
            self._update_timer(lambda: self._set_storage(name=name))

    def _delay(self, event: GenericEventArguments) -> None:
        value = self.element.value
        if isinstance(self.element, TextElement):
            name = self.element.text
        else:
            name = event.sender._props.get("label")
        self._update_timer(lambda: self._set_storage(name=name))

    def __enter__(self) -> Store:
        if isinstance(self.element, ValidationElement):
            def delay(value: GenericEventArguments) -> None:
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



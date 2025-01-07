from __future__ import annotations

import hashlib

from loguru import logger

from model.data_access import get_nested_value, set_nested_value
from plugins.abstract import InterfaceLLMConfig, InterfaceDataConfig


class ConfigModel:
    @staticmethod
    def _instance_path(instance_id: str | None, key: str) -> tuple[str, ...]:
        if instance_id is None:
            return "system", "config", key

        return "instances", instance_id, "config", key

    @staticmethod
    def _set_value(instance_id: str | None, key: str, value: any) -> None:
        key_path = ConfigModel._instance_path(instance_id, key)
        set_nested_value(key_path, value)

    @staticmethod
    def _get_value(instance_id: str | None, key: str, /, *, default: any = None) -> any:
        instance_key_path = ConfigModel._instance_path(instance_id, key)
        return get_nested_value(instance_key_path, default=default)

    @staticmethod
    def get_llm_interface(instance_id: str | None, interface_name: str) -> InterfaceLLMConfig | None:
        interfaces = ConfigModel.get_llm_interfaces(instance_id)
        return interfaces.get(interface_name)

    @staticmethod
    def get_data_interface(instance_id: str | None, name: str) -> InterfaceDataConfig | None:
        interfaces = ConfigModel.get_data_interfaces(instance_id)
        return interfaces.get(name)

    @staticmethod
    def get_general_name(instance_id: str | None) -> str:
        name = ConfigModel._get_value(instance_id, "general_name")
        if name is None:
            name = ConfigModel._get_value(None, "general_name", default="Doppelcheck")

        return name

    @staticmethod
    def set_general_name(instance_id: str | None, value: str) -> None:
        ConfigModel._set_value(instance_id, "general_name", value)

    @staticmethod
    def get_keypoint_index(instance_id: str | None) -> int:
        value = ConfigModel._get_value(instance_id, "keypoint_index", default=0)
        return value

    @staticmethod
    def increment_keypoint_index(instance_id: str | None) -> int:
        value = ConfigModel._get_value(instance_id, "keypoint_index", default=0)
        value += 1
        ConfigModel._set_value(instance_id, "keypoint_index", value)
        return value

    @staticmethod
    def get_general_language(instance_id: str | None) -> str:
        language = ConfigModel._get_value(instance_id, "general_language")
        if language is None:
            language = ConfigModel._get_value(None, "general_language", default="default")
        return language

    @staticmethod
    def set_general_language(instance_id, value: str) -> None:
        ConfigModel._set_value(instance_id, "general_language", value)

    @staticmethod
    def get_extraction_prompt(instance_id: str | None) -> str | None:
        prompt = ConfigModel._get_value(instance_id, "extraction_prompt")
        if prompt is None:
            return ConfigModel._get_value(None, "extraction_prompt")
        return prompt

    @staticmethod
    def set_extraction_prompt(instance_id: str | None, value: str) -> None:
        ConfigModel._set_value(instance_id, "extraction_prompt", value)

    @staticmethod
    def get_comparison_prompt(instance_id: str | None) -> str | None:
        prompt = ConfigModel._get_value(instance_id, "comparison_prompt")
        if prompt is None:
            return ConfigModel._get_value(None, "comparison_prompt")
        return prompt

    @staticmethod
    def set_comparison_prompt(instance_id: str | None, value: str) -> None:
        ConfigModel._set_value(instance_id, "comparison_prompt", value)

    @staticmethod
    def get_llm_interfaces(instance_id: str | None) -> dict[str, InterfaceLLMConfig]:
        available_interfaces = ConfigModel._get_value(None, "llm_interfaces", default=dict())
        instance_interfaces = ConfigModel._get_value(instance_id, "llm_interfaces", default=dict())

        available_interfaces.update(instance_interfaces)

        interfaces = dict[str, InterfaceLLMConfig]()
        if available_interfaces is None:
            return interfaces

        for each_key, each_dict in available_interfaces.items():
            each_interface = InterfaceLLMConfig.from_object_dict(each_dict)
            interfaces[each_key] = each_interface

        return interfaces

    @staticmethod
    def add_llm_interface(instance_id: str | None, interface: InterfaceLLMConfig) -> None:
        value = ConfigModel._get_value(instance_id, "llm_interfaces", default=dict[str, dict[str, any]]())
        llm_dict = interface.to_object_dict()
        name = llm_dict["name"]
        value[name] = llm_dict
        ConfigModel._set_value(instance_id, "llm_interfaces", value)

    @staticmethod
    def remove_llm_interface(instance_id: str | None, llm_interface_name: str) -> None:
        value = ConfigModel._get_value(instance_id, "llm_interfaces")
        if value is None:
            logger.error(f"Could not remove {llm_interface_name} from {instance_id}: no llm_interfaces found.")
            return

        try:
            del value[llm_interface_name]

        except KeyError as e:
            logger.error(f"Could not remove {llm_interface_name} from {instance_id}: {e}")

        ConfigModel._set_value(instance_id, "llm_interfaces", value)

    @staticmethod
    def get_data_interfaces(instance_id: str | None) -> dict[str, InterfaceDataConfig]:
        available_interfaces = ConfigModel._get_value(None, "data_interfaces", default=dict())
        instance_interfaces = ConfigModel._get_value(instance_id, "data_interfaces", default=dict())

        available_interfaces.update(instance_interfaces)

        interfaces = dict[str, InterfaceDataConfig]()
        if available_interfaces is None:
            return interfaces

        for each_key, each_dict in available_interfaces.items():
            each_interface = InterfaceDataConfig.from_object_dict(each_dict)
            interfaces[each_key] = each_interface

        return interfaces

    @staticmethod
    def add_data_interface(instance_id: str | None, interface: InterfaceDataConfig) -> None:
        value = ConfigModel._get_value(instance_id, "data_interfaces", default=dict[str, dict[str, any]]())
        data_dict = interface.to_object_dict()
        name = data_dict["name"]
        value[name] = data_dict
        ConfigModel._set_value(instance_id, "data_interfaces", value)

    @staticmethod
    def remove_data_interface(instance_id: str | None, data_interface_name: str) -> None:
        value = ConfigModel._get_value(instance_id, "data_interfaces")
        if value is None:
            logger.error(f"Could not remove {data_interface_name} from {instance_id}: no data_interfaces found.")
            return

        try:
            del value[data_interface_name]

        except KeyError as e:
            logger.error(f"Could not remove {data_interface_name} from {instance_id}: {e}")

        ConfigModel._set_value(instance_id, "data_interfaces", value)

    @staticmethod
    def get_extraction_llm(instance_id: str | None) -> InterfaceLLMConfig | None:
        interface_name = ConfigModel._get_value(instance_id, "extraction_llm")
        if interface_name is None:
            interface_name = ConfigModel._get_value(None, "extraction_llm")
            if interface_name is None:
                return None

        interface = ConfigModel.get_llm_interface(instance_id, interface_name)
        return interface

    @staticmethod
    def set_extraction_llm(instance_id: str | None, interface_name: str) -> None:
        ConfigModel._set_value(instance_id, "extraction_llm", interface_name)

    @staticmethod
    def get_number_of_keypoints(instance_id: str | None) -> int:
        value = ConfigModel._get_value(instance_id, "extraction_claims")
        if value is None:
            value = ConfigModel._get_value(None, "extraction_claims", default=3)
            return value
        return value

    @staticmethod
    def set_extraction_claims(instance_id: str | None, value: int) -> None:
        ConfigModel._set_value(instance_id, "extraction_claims", value)

    @staticmethod
    def get_retrieval_llm(instance_id: str | None) -> InterfaceLLMConfig | None:
        interface_name = ConfigModel._get_value(instance_id, "retrieval_llm")
        if interface_name is None:
            interface_name = ConfigModel._get_value(None, "retrieval_llm")
            if interface_name is None:
                return None

        interface = ConfigModel.get_llm_interface(instance_id, interface_name)
        return interface

    @staticmethod
    def set_retrieval_llm(instance_id: str | None, interface_name: str) -> None:
        ConfigModel._set_value(instance_id, "retrieval_llm", interface_name)

    @staticmethod
    def get_selected_data_interfaces(instance_id: str | None) -> list[InterfaceDataConfig]:
        selected_interfaces = ConfigModel._get_value(instance_id, "selected_data_interfaces")
        if selected_interfaces is None:
            selected_interfaces = ConfigModel._get_value(None, "selected_data_interfaces")
            if selected_interfaces is None:
                return list()

        interfaces = [ConfigModel.get_data_interface(instance_id, each_name) for each_name in selected_interfaces]
        return interfaces

    @staticmethod
    def set_selected_data_interfaces(instance_id: str | None, interface_names: list[str]) -> None:
        ConfigModel._set_value(instance_id, "selected_data_interfaces", interface_names)

    @staticmethod
    def get_retrieval_max_documents(instance_id: str | None) -> int:
        value = ConfigModel._get_value(
            instance_id, "retrieval_max_documents",
            default=ConfigModel._get_value("ADMIN", "retrieval_max_documents", default=5)
        )
        return value

    @staticmethod
    def set_retrieval_max_documents(instance_id: str | None, value: int) -> None:
        ConfigModel._set_value(instance_id, "retrieval_max_documents", value)

    @staticmethod
    def get_comparison_llm(instance_id: str | None) -> InterfaceLLMConfig | None:
        interface_name = ConfigModel._get_value(instance_id, "comparison_llm")
        if interface_name is None:
            interface_name = ConfigModel._get_value(None, "comparison_llm")
            if interface_name is None:
                return None

        interface = ConfigModel.get_llm_interface(instance_id, interface_name)
        return interface

    @staticmethod
    def set_comparison_llm(instance_id: str | None, interface_name: str) -> None:
        ConfigModel._set_value(instance_id, "comparison_llm", interface_name)

    @staticmethod
    def get_extraction_mode(instance_id: str | None) -> str:
        value = ConfigModel._get_value(instance_id, "extraction_mode")
        if value is None:
            value = ConfigModel._get_value(None, "extraction_mode", default="NLP supported")
        return value

    @staticmethod
    def set_extraction_mode(instance_id: str | None, mode: str) -> None:
        ConfigModel._set_value(instance_id, "extraction_mode", mode)


class PasswordsModel:
    @staticmethod
    def _password_path(user_name: str) -> tuple[str, ...]:
        return "password_hash", user_name

    @staticmethod
    def add_password(user_name: str, password: str) -> None:
        key_path = PasswordsModel._password_path(user_name)
        password_hash = hashlib.md5(password.encode())
        set_nested_value(key_path, password_hash.hexdigest())

    @staticmethod
    def check_password(user_name: str, password: str) -> bool:
        key_path = PasswordsModel._password_path(user_name)
        password_hash = hashlib.md5(password.encode())
        stored_password = get_nested_value(key_path)
        if stored_password is None:
            return False
        return password_hash.hexdigest() == stored_password

    @staticmethod
    def admin_registered() -> bool:
        return get_nested_value(("password_hash",)) is not None


class AccessModel:
    @staticmethod
    def _access_path(key: str) -> tuple[str, ...]:
        return "system", "access", key

    @staticmethod
    def _get_instance_access(key: str) -> bool:
        key_path = AccessModel._access_path(key)
        return get_nested_value(key_path, default=False)

    @staticmethod
    def _set_instance_access(key: str, value: bool) -> None:
        key_path = AccessModel._access_path(key)
        set_nested_value(key_path, value)

    @staticmethod
    def set_access_name(access: bool) -> None:
        AccessModel._set_instance_access("name", access)

    @staticmethod
    def get_access_name() -> bool:
        return AccessModel._get_instance_access("name")

    @staticmethod
    def set_access_language(access: bool) -> None:
        AccessModel._set_instance_access("language", access)

    @staticmethod
    def get_access_language() -> bool:
        return AccessModel._get_instance_access("language")

    @staticmethod
    def set_extraction_llm(access: bool) -> None:
        AccessModel._set_instance_access("extraction_llm_name", access)

    @staticmethod
    def get_extraction_llm() -> bool:
        return AccessModel._get_instance_access("extraction_llm_name")

    @staticmethod
    def set_extraction_claims(access: bool) -> None:
        AccessModel._set_instance_access("extraction_claims", access)

    @staticmethod
    def get_extraction_claims() -> bool:
        return AccessModel._get_instance_access("extraction_claims")

    @staticmethod
    def set_retrieval_llm(access: bool) -> None:
        AccessModel._set_instance_access("retrieval_llm_name", access)

    @staticmethod
    def get_retrieval_llm() -> bool:
        return AccessModel._get_instance_access("retrieval_llm_name")

    @staticmethod
    def set_select_data(access: bool) -> None:
        AccessModel._set_instance_access("select_data_interfaces", access)

    @staticmethod
    def get_select_data() -> bool:
        return AccessModel._get_instance_access("select_data_interfaces")

    @staticmethod
    def set_retrieval_max_documents(access: bool) -> None:
        AccessModel._set_instance_access("retrieval_max_documents", access)

    @staticmethod
    def get_retrieval_max_documents() -> bool:
        return AccessModel._get_instance_access("retrieval_max_documents")

    @staticmethod
    def set_comparison_llm(access: bool) -> None:
        AccessModel._set_instance_access("comparison_llm_name", access)

    @staticmethod
    def get_comparison_llm() -> bool:
        return AccessModel._get_instance_access("comparison_llm_name")

    @staticmethod
    def set_add_llm(access: bool) -> None:
        AccessModel._set_instance_access("add_llm", access)

    @staticmethod
    def get_add_llm() -> bool:
        return AccessModel._get_instance_access("add_llm")

    @staticmethod
    def set_remove_llm(access: bool) -> None:
        AccessModel._set_instance_access("remove_llm", access)

    @staticmethod
    def get_remove_llm() -> bool:
        return AccessModel._get_instance_access("remove_llm")

    @staticmethod
    def set_add_data(access: bool) -> None:
        AccessModel._set_instance_access("add_data", access)

    @staticmethod
    def get_add_data() -> bool:
        return AccessModel._get_instance_access("add_data")

    @staticmethod
    def set_remove_data(access: bool) -> None:
        AccessModel._set_instance_access("remove_data", access)

    @staticmethod
    def get_remove_data() -> bool:
        return AccessModel._get_instance_access("remove_data")

    @staticmethod
    def set_extraction_prompt(value: bool) -> None:
        return AccessModel._set_instance_access("change_extraction_prompt", value)

    @staticmethod
    def get_extraction_prompt() -> bool:
        return AccessModel._get_instance_access("change_extraction_prompt")

    @staticmethod
    def set_comparison_prompt(value: bool) -> None:
        return AccessModel._set_instance_access("change_comparison_prompt", value)

    @staticmethod
    def get_comparison_prompt() -> bool:
        return AccessModel._get_instance_access("change_comparison_prompt")

    @staticmethod
    def set_extraction_mode(value: bool) -> None:
        return AccessModel._set_instance_access("extraction_mode", value)

    @staticmethod
    def get_extraction_mode() -> bool:
        return AccessModel._get_instance_access("extraction_mode")
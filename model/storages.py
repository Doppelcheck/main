from __future__ import annotations

import hashlib

from loguru import logger

from model.data_access import get_nested_value, set_nested_value
from plugins.abstract import InterfaceLLMConfig, InterfaceDataConfig


class ConfigModel:
    @staticmethod
    def _user_path(user_id: str | None, key: str) -> tuple[str, ...]:
        if user_id is None:
            return "system", "config", key

        return "users", user_id, "config", key

    @staticmethod
    def _set_value(user_id: str | None, key: str, value: any) -> None:
        key_path = ConfigModel._user_path(user_id, key)
        set_nested_value(key_path, value)

    @staticmethod
    def _get_value(user_id: str | None, key: str, /, *, default: any = None) -> any:
        user_key_path = ConfigModel._user_path(user_id, key)
        return get_nested_value(user_key_path, default=default)

    @staticmethod
    def get_llm_interface(user_id: str | None, interface_name: str) -> InterfaceLLMConfig | None:
        interfaces = ConfigModel.get_llm_interfaces(user_id)
        return interfaces.get(interface_name)

    @staticmethod
    def get_data_interface(user_id: str | None, name: str) -> InterfaceDataConfig | None:
        interfaces = ConfigModel.get_data_interfaces(user_id)
        return interfaces.get(name)

    @staticmethod
    def get_general_name(user_id: str | None) -> str:
        name = ConfigModel._get_value(user_id, "general_name")
        if name is None:
            name = ConfigModel._get_value(None, "general_name", default="Doppelcheck")

        return name

    @staticmethod
    def set_general_name(user_id: str | None, value: str) -> None:
        ConfigModel._set_value(user_id, "general_name", value)

    @staticmethod
    def get_general_language(user_id: str | None) -> str:
        language = ConfigModel._get_value(user_id, "general_language")
        if language is None:
            language = ConfigModel._get_value(None, "general_language", default="default")
        return language

    @staticmethod
    def set_general_language(user_id, value: str) -> None:
        ConfigModel._set_value(user_id, "general_language", value)

    @staticmethod
    def get_extraction_prompt(user_id: str | None) -> str | None:
        prompt = ConfigModel._get_value(user_id, "extraction_prompt")
        if prompt is None:
            return ConfigModel._get_value(None, "extraction_prompt")
        return prompt

    @staticmethod
    def set_extraction_prompt(user_id: str | None, value: str) -> None:
        ConfigModel._set_value(user_id, "extraction_prompt", value)

    @staticmethod
    def get_comparison_prompt(user_id: str | None) -> str | None:
        prompt = ConfigModel._get_value(user_id, "comparison_prompt")
        if prompt is None:
            return ConfigModel._get_value(None, "comparison_prompt")
        return prompt

    @staticmethod
    def set_comparison_prompt(user_id: str | None, value: str) -> None:
        ConfigModel._set_value(user_id, "comparison_prompt", value)

    @staticmethod
    def get_llm_interfaces(user_id: str | None) -> dict[str, InterfaceLLMConfig]:
        available_interfaces = ConfigModel._get_value(None, "llm_interfaces", default=dict())
        user_interfaces = ConfigModel._get_value(user_id, "llm_interfaces", default=dict())

        available_interfaces.update(user_interfaces)

        interfaces = dict[str, InterfaceLLMConfig]()
        if available_interfaces is None:
            return interfaces

        for each_key, each_dict in available_interfaces.items():
            each_interface = InterfaceLLMConfig.from_object_dict(each_dict)
            interfaces[each_key] = each_interface

        return interfaces

    @staticmethod
    def add_llm_interface(user_id: str | None, interface: InterfaceLLMConfig) -> None:
        value = ConfigModel._get_value(user_id, "llm_interfaces", default=dict[str, dict[str, any]]())
        llm_dict = interface.to_object_dict()
        name = llm_dict["name"]
        value[name] = llm_dict
        ConfigModel._set_value(user_id, "llm_interfaces", value)

    @staticmethod
    def remove_llm_interface(user_id: str | None, llm_interface_name: str) -> None:
        value = ConfigModel._get_value(user_id, "llm_interfaces")
        if value is None:
            logger.error(f"Could not remove {llm_interface_name} from {user_id}: no llm_interfaces found.")
            return

        try:
            del value[llm_interface_name]

        except KeyError as e:
            logger.error(f"Could not remove {llm_interface_name} from {user_id}: {e}")

        ConfigModel._set_value(user_id, "llm_interfaces", value)

    @staticmethod
    def get_data_interfaces(user_id: str | None) -> dict[str, InterfaceDataConfig]:
        available_interfaces = ConfigModel._get_value(None, "data_interfaces", default=dict())
        user_interfaces = ConfigModel._get_value(user_id, "data_interfaces", default=dict())

        available_interfaces.update(user_interfaces)

        interfaces = dict[str, InterfaceDataConfig]()
        if available_interfaces is None:
            return interfaces

        for each_key, each_dict in available_interfaces.items():
            each_interface = InterfaceDataConfig.from_object_dict(each_dict)
            interfaces[each_key] = each_interface

        return interfaces

    @staticmethod
    def add_data_interface(user_id: str | None, interface: InterfaceDataConfig) -> None:
        value = ConfigModel._get_value(user_id, "data_interfaces", default=dict[str, dict[str, any]]())
        data_dict = interface.to_object_dict()
        name = data_dict["name"]
        value[name] = data_dict
        ConfigModel._set_value(user_id, "data_interfaces", value)

    @staticmethod
    def remove_data_interface(user_id: str | None, data_interface_name: str) -> None:
        value = ConfigModel._get_value(user_id, "data_interfaces")
        if value is None:
            logger.error(f"Could not remove {data_interface_name} from {user_id}: no data_interfaces found.")
            return

        try:
            del value[data_interface_name]

        except KeyError as e:
            logger.error(f"Could not remove {data_interface_name} from {user_id}: {e}")

        ConfigModel._set_value(user_id, "data_interfaces", value)

    @staticmethod
    def get_extraction_llm(user_id: str | None) -> InterfaceLLMConfig | None:
        interface_name = ConfigModel._get_value(user_id, "extraction_llm")
        if interface_name is None:
            interface_name = ConfigModel._get_value(None, "extraction_llm")
            if interface_name is None:
                return None

        interface = ConfigModel.get_llm_interface(user_id, interface_name)
        return interface

    @staticmethod
    def set_extraction_llm(user_id: str | None, interface_name: str) -> None:
        ConfigModel._set_value(user_id, "extraction_llm", interface_name)

    @staticmethod
    def get_extraction_claims(user_id: str | None) -> int:
        value = ConfigModel._get_value(user_id, "extraction_claims")
        if value is None:
            value = ConfigModel._get_value(None, "extraction_claims", default=3)
            return value
        return value

    @staticmethod
    def set_extraction_claims(user_id: str | None, value: int) -> None:
        ConfigModel._set_value(user_id, "extraction_claims", value)

    @staticmethod
    def get_retrieval_llm(user_id: str | None) -> InterfaceLLMConfig | None:
        interface_name = ConfigModel._get_value(user_id, "retrieval_llm")
        if interface_name is None:
            interface_name = ConfigModel._get_value(None, "retrieval_llm")
            if interface_name is None:
                return None

        interface = ConfigModel.get_llm_interface(user_id, interface_name)
        return interface

    @staticmethod
    def set_retrieval_llm(user_id: str | None, interface_name: str) -> None:
        ConfigModel._set_value(user_id, "retrieval_llm", interface_name)

    @staticmethod
    def get_retrieval_data(user_id: str | None) -> InterfaceDataConfig | None:
        interface_name = ConfigModel._get_value(user_id, "retrieval_data")
        if interface_name is None:
            interface_name = ConfigModel._get_value(None, "retrieval_data")
            if interface_name is None:
                return None

        interface = ConfigModel.get_data_interface(user_id, interface_name)
        return interface

    @staticmethod
    def set_retrieval_data(user_id: str | None, interface_name: str) -> None:
        ConfigModel._set_value(user_id, "retrieval_data", interface_name)

    @staticmethod
    def get_retrieval_max_documents(user_id: str | None) -> int:
        value = ConfigModel._get_value(
            user_id, "retrieval_max_documents",
            default=ConfigModel._get_value("ADMIN", "retrieval_max_documents", default=10)
        )
        return value

    @staticmethod
    def set_retrieval_max_documents(user_id: str | None, value: int) -> None:
        ConfigModel._set_value(user_id, "retrieval_max_documents", value)

    @staticmethod
    def get_comparison_llm(user_id: str | None) -> InterfaceLLMConfig | None:
        interface_name = ConfigModel._get_value(user_id, "comparison_llm")
        if interface_name is None:
            interface_name = ConfigModel._get_value(None, "comparison_llm")
            if interface_name is None:
                return None

        interface = ConfigModel.get_llm_interface(user_id, interface_name)
        return interface

    @staticmethod
    def set_comparison_llm(user_id: str | None, interface_name: str) -> None:
        ConfigModel._set_value(user_id, "comparison_llm", interface_name)

    @staticmethod
    def get_comparison_data(user_id: str | None) -> InterfaceDataConfig | None:
        interface_name = ConfigModel._get_value(user_id, "comparison_data")
        if interface_name is None:
            interface_name = ConfigModel._get_value(None, "comparison_data")
            if interface_name is None:
                return None

        interface = ConfigModel.get_data_interface(user_id, interface_name)
        return interface

    @staticmethod
    def set_comparison_data(user_id: str | None, interface_name: str) -> None:
        ConfigModel._set_value(user_id, "comparison_data", interface_name)


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
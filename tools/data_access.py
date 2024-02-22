from dataclasses import dataclass
from typing import Sequence

from loguru import logger
from nicegui import app
from nicegui.observables import ObservableDict, ObservableList, ObservableSet

from tools.data_objects import GoogleCustomSearch, ParametersOpenAi


def get_nested_value(key_path: Sequence[str], default: any = None) -> any:
    data = app.storage.general
    for i, each_key in enumerate(key_path):
        data = data.get(each_key)
        if data is None or (isinstance(data, str) and len(data) < 1):
            logger.debug(f"Key path [{key_path}] not found, nothing at [{i}:{each_key}], returning default value {default}")
            return default

    logger.debug(f"Got [{key_path}] as {data}")
    if isinstance(data, ObservableDict):
        return dict(data)

    if isinstance(data, ObservableList):
        return list(data)

    if isinstance(data, ObservableSet):
        return set(data)

    return data


def set_nested_value(key_path: Sequence[str], value: any) -> None:
    data = app.storage.general

    for each_key in key_path[:-1]:
        new_data = data.get(each_key)
        if new_data is None:
            data[each_key] = dict()  # converts `dict()` to observable dict
            new_data = data[each_key]
        data = new_data

    last_key = key_path[-1]
    data[last_key] = value
    app.storage.general.update()
    logger.debug(f"Set {key_path} to {value}: ")


def get_user_config_dict(userid: str) -> dict[str, any] | None:
    key_path = "users", userid, "config"
    config_dict = get_nested_value(key_path)
    return config_dict


@dataclass
class UserConfig:
    name_instance: str = "standard instance"
    claim_count: int = 3
    language: str = "default"

    google_custom_search: dict[str, str] | GoogleCustomSearch | None = None

    openai_api_key: str | None = None
    openai_parameters: dict[str, str] | ParametersOpenAi | None = None

    def __post_init__(self) -> None:
        if self.google_custom_search is not None and not isinstance(self.google_custom_search, GoogleCustomSearch):
            self.google_custom_search = GoogleCustomSearch(**self.google_custom_search)
        if self.openai_parameters is not None and not isinstance(self.openai_parameters, ParametersOpenAi):
            self.openai_parameters = ParametersOpenAi(**self.openai_parameters)
        else:
            self.openai_parameters = ParametersOpenAi()


def set_config_value(userid: str, config_path: Sequence[str], value: any) -> None:
    key_path = ("users", userid, "config") + tuple(config_path)
    set_nested_value(key_path, value)


def get_config_value(userid: str, config_path: Sequence[str], default: any = None) -> any:
    key_path = ("users", userid, "config") + tuple(config_path)
    value = get_nested_value(key_path, default=default)
    return value


def set_data_value(userid: str, key_path: Sequence[str], value: any) -> None:
    key_path = ("users", userid, "data") + tuple(key_path)
    set_nested_value(key_path, value)


def get_data_value(userid: str, data_path: Sequence[str], default: any = None) -> any:
    key_path = ("users", userid, "data") + tuple(data_path)
    value = get_nested_value(key_path, default=default)
    return value


if __name__ == "__main__":
    test_data = get_nested_value(("test",))
    print(test_data)
    set_nested_value(("test",), {"a": 1, "b": 2})
    test_data = get_nested_value(("test",))
    print(test_data)

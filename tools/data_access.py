from typing import Sequence

from loguru import logger
from nicegui import app

from tools.data_objects import UserConfig


def get_nested_value(key_path: Sequence[str], default: any = None) -> any:
    data = app.storage.general
    for i, each_key in enumerate(key_path):
        data = data.get(each_key)
        if data is None:
            logger.debug(f"Key path [{key_path}] not found, nothing at [{i}:{each_key}], returning default value {default}")
            return default

    logger.debug(f"Got [{key_path}] as {data}")
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


def get_user_config(userid: str) -> UserConfig:
    config_dict = get_user_config_dict(userid)
    return UserConfig() if config_dict is None else UserConfig(**config_dict)


def get_user_data_dict(userid: str) -> dict[str, any]:
    key_path = "users", userid, "data"
    return get_nested_value(key_path, default=dict())


def get_config_value(userid: str, config_path: Sequence[str], default: any = None) -> any:
    key_path = ("users", userid, "config") + tuple(config_path)
    value = get_nested_value(key_path, default=default)
    return value


def get_data_value(userid: str, data_path: Sequence[str], default: any = None) -> any:
    key_path = ("users", userid, "data") + tuple(data_path)
    value = get_nested_value(key_path, default=default)
    return value


def set_config_value(userid: str, config_path: Sequence[str], value: any) -> None:
    key_path = ("users", userid, "config") + tuple(config_path)
    set_nested_value(key_path, value)


def set_data_value(userid: str, key_path: Sequence[str], value: any) -> None:
    key_path = ("users", userid, "data") + tuple(key_path)
    set_nested_value(key_path, value)


if __name__ == "__main__":
    test_data = get_nested_value(("test",))
    print(test_data)
    set_nested_value(("test",), {"a": 1, "b": 2})
    test_data = get_nested_value(("test",))
    print(test_data)

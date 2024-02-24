from typing import Sequence

from loguru import logger
from nicegui import app
from nicegui.observables import ObservableDict, ObservableList, ObservableSet



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


def set_data_value(userid: str, key_path: Sequence[str], value: any) -> None:
    key_path = ("users", userid, "data") + tuple(key_path)
    set_nested_value(key_path, value)


def get_data_value(userid: str, key_path: Sequence[str], default: any = None) -> any:
    key_path = ("users", userid, "data") + tuple(key_path)
    value = get_nested_value(key_path, default=default)
    return value


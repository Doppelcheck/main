from contextlib import contextmanager
from typing import Callable

from loguru import logger
from nicegui import ui, app
from nicegui.element import Element


def get_config_dict(userid: str) -> dict[str, any]:
    current_config = app.storage.general.get(userid)
    if current_config is None:
        logger.info(f"No configuration found for user {userid}", userid)
        current_config = {
            "name_instance": "standard instance",
            "claim_count": 3
        }
        return current_config

    config_dict = {key: value for key, value in current_config.items()}

    if "name_instance" not in current_config:
        config_dict["name_instance"] = "standard instance"

    if "claim_count" not in current_config:
        config_dict["claim_count"] = 3

    return config_dict


@contextmanager
def delayed_storage(userid: str, element_type: type[Element], key_name: str, **kwargs) -> None:
    timer: ui.timer | None = None

    def update_timer(callback: Callable[..., any]) -> None:
        nonlocal timer
        if timer is not None:
            timer.cancel()
            del timer
        timer = ui.timer(interval=1.0, active=True, once=True, callback=callback)

    def delayed_set_storage(key: str, value: any) -> None:
        element.classes(add="bg-warning ")

        async def set_storage() -> None:
            _settings = app.storage.general.get(userid)
            if _settings is None:
                _settings = {key: value}
                app.storage.general[userid] = _settings
            else:
                _settings[key] = value

            element.classes(remove="bg-warning ")
            ui.notify("Settings saved", timeout=500)  # , progress=True)

        update_timer(set_storage)

    with element_type(**kwargs, on_change=lambda event: delayed_set_storage(key_name, event.value)) as element:
        element.classes(add="transition ease-out duration-500 ")
        element.classes(remove="bg-warning ")
        yield element

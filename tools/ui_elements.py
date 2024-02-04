from contextlib import contextmanager
from typing import Callable

from nicegui import ui, app
from nicegui.element import Element


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
            print(f"setting settings for {userid}: {app.storage.general.get(userid)}")
            element.classes(remove="bg-warning ")

        update_timer(set_storage)

    settings = app.storage.general.get(userid)
    last_value = "" if settings is None else settings.get(key_name, "")

    with element_type(**kwargs, value=last_value, on_change=lambda event: delayed_set_storage(key_name, event.value)) as element:
        element.classes(add="transition ease-out duration-500 ")
        element.classes(remove="bg-warning ")
        yield element

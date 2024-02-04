from contextlib import contextmanager
from typing import Callable

from nicegui import ui, app
from nicegui.element import Element


@contextmanager
def delayed_storage(userid: str, element_type: type(Element), key_name: str, **kwargs) -> None:
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
            settings = app.storage.general.get(userid)
            if settings is None:
                settings = {key: value}
                app.storage.general[userid] = settings
            else:
                settings[key] = value
            print(f"setting settings for {userid}: {app.storage.general.get(userid)}")
            element.classes(remove="bg-warning ")

        update_timer(set_storage)

    last_value = ""
    with element_type(
            **kwargs,
            value=last_value,
            on_change=lambda event: delayed_set_storage(key_name, event.value),
    ) as element:
        element.classes(add="transition ease-out duration-500 ")
        element.classes(remove="bg-warning ")
        yield element

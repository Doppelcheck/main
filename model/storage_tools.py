from __future__ import annotations

import json
from typing import Callable

from nicegui import ui
from nicegui.elements.mixins.text_element import TextElement
from nicegui.elements.mixins.validation_element import ValidationElement
from nicegui.elements.mixins.value_element import ValueElement
from nicegui.events import GenericEventArguments

from tools.text_processing import truncate_text


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

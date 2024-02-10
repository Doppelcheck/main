import dataclasses
from contextlib import contextmanager
from typing import Callable, Sequence

from fastapi.responses import RedirectResponse

from loguru import logger
from nicegui import ui
from nicegui.element import Element

from dataclasses import dataclass

from tools.data_access import set_config_value, get_config_value, set_nested_value, get_nested_value
from tools.data_objects import OpenAIParameters


def asdict_recusive(dc: dataclass) -> dict[str, any]:
    return {
        k: asdict_recusive(v) if dataclasses.is_dataclass(v) else v
        for k, v in dataclasses.asdict(dc).items()
    }


@contextmanager
def delayed_storage(userid: str, element_type: type[Element], key_path: Sequence[str], default: any = None, **kwargs) -> None:
    timer: ui.timer | None = None

    def update_timer(callback: Callable[..., any]) -> None:
        nonlocal timer
        if timer is not None:
            timer.cancel()
            del timer
        timer = ui.timer(interval=1.0, active=True, once=True, callback=callback)

    def delayed_set_storage(_key_path: Sequence[str], value: any, validation: dict[str, Callable[[str], bool]] | None = None) -> None:
        if validation is None or all(each_validation(value) for each_validation in validation.values()):
            element.classes(add="bg-warning ")

            async def set_storage() -> None:
                _user_path = ("users", userid) + tuple(_key_path)
                set_nested_value(_user_path, value)

                element.classes(remove="bg-warning ")
                ui.notify(f"{kwargs.get('label', 'Setting')} saved", timeout=500)  # , progress=True)

            update_timer(set_storage)

        else:
            pass

    user_path = ("users", userid) + tuple(key_path)
    last_value = get_nested_value(user_path, default=default)
    with element_type(
        value=last_value, **kwargs,
        on_change=lambda event: delayed_set_storage(key_path, event.value, validation=kwargs.get("validation"))
    ) as element:
        element.classes(add="transition ease-out duration-500 ")
        element.classes(remove="bg-warning ")
        yield element


def update_llm_config(user_id: str, llm_config: Element, value: str) -> None:
    llm_config.clear()

    match value:
        case "OpenAI":
            with llm_config:
                with delayed_storage(
                    user_id, ui.input, ("config", "openai_api_key",),
                    label="OpenAI API Key", placeholder="\"sk-\" + 48 alphanumeric characters",
                    password=True,
                    validation={
                        "Must start with \"sk-\"": lambda v: v.startswith("sk-"),
                        "Must be 51 characters long": lambda v: len(v) == 51
                    }
                ) as api_key:
                    pass

        case "Mistral":
            pass

        case "Anthropic":
            pass

        case "ollama":
            # https://github.com/ollama/ollama-python
            # https://github.com/ollama/ollama/blob/main/docs/api.md
            # https://github.com/ollama/ollama
            pass

        case "llamafile":
            # https://github.com/Mozilla-Ocho/llamafile
            pass

    with llm_config:
        with ui.expansion("Additional Parameters") as advanced:
            advanced.classes(add="text-lg font-bold mt-8 ")

            openai_parameters = get_config_value(user_id, ("openai_parameters",))
            logger.info(openai_parameters)
            content = {"content": {"json": openai_parameters}}
            with ui.json_editor(content, on_change=lambda: save_parameters_button.enable()) as editor:
                editor.classes(add="w-full ")

            async def save_parameters(event) -> None:
                editor_content = await editor.run_editor_method("get")
                set_config_value(user_id, ("openai_parameters",), editor_content['json'])
                ui.notify("Parameters saved", timeout=500)
                save_parameters_button.disable()

            def reset_parameters(event) -> None:
                default_settings = OpenAIParameters()
                default_dict = {"json": asdict_recusive(default_settings)}
                editor.run_editor_method("update", default_dict)
                ui.notify("Parameters reset", timeout=500)

            with ui.row():
                with ui.button("Save parameters", on_click=save_parameters) as save_parameters_button:
                    save_parameters_button.disable()

                with ui.button(
                        "Reset parameters",
                        on_click=reset_parameters
                ):
                    pass


def update_data_config(user_id: str, data_config: Element, value: str) -> None:
    match value:
        case "Google":
            data_config.clear()
            with data_config:
                with delayed_storage(
                        user_id, ui.input, ("config", "google_custom_search", "api_key"),
                        label="Google Custom Search API Key",
                        placeholder="39 alphanumeric characters",
                        validation={"Must be 39 characters long": lambda v: len(v) == 39}
                ) as api_key:
                    pass
                with delayed_storage(
                        user_id, ui.input, ("config", "google_custom_search", "engine_id"),
                        label="Google Custom Search Engine ID",
                        placeholder="17 alphanumeric characters",
                        validation={"Must be 17 characters long": lambda v: len(v) == 17}
                ) as engine_id:
                    pass

        case "Bing":
            data_config.clear()

        case "DuckDuckGo":
            data_config.clear()

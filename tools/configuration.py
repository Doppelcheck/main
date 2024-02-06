from contextlib import contextmanager
from typing import Callable

from loguru import logger
from nicegui import ui, app
from nicegui.element import Element

from dataclasses import dataclass


@dataclass
class OpenAIParameters:
    # https://platform.openai.com/docs/api-reference/chat/create
    model: str
    frequency_penalty: float = 0
    logit_bias: dict[int, float] | None = None
    logprobs: bool = False
    top_logprobs: int | None = None
    max_tokens: int | None = None
    n: int = 1
    presence_penalty: float = 0
    response_format: dict[str, str] | None = None
    seed: int | None = None
    stop: str | list[str] | None = None
    temperature: float = 1
    top_p: float = 1
    tools: list[str] = None
    tool_choice: str | dict[str, any] | None = None
    user: str | None = None


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
    settings = get_config_dict(userid)

    def update_timer(callback: Callable[..., any]) -> None:
        nonlocal timer
        if timer is not None:
            timer.cancel()
            del timer
        timer = ui.timer(interval=1.0, active=True, once=True, callback=callback)

    def delayed_set_storage(key: str, value: any, validation: dict[str, Callable[[str], bool]] | None = None) -> None:
        if validation is None or all(each_validation(value) for each_validation in validation.values()):
            element.classes(add="bg-warning ")

            async def set_storage() -> None:
                _settings = app.storage.general.get(userid)
                if _settings is None:
                    _settings = {key: value}
                    app.storage.general[userid] = _settings
                else:
                    _settings[key] = value

                element.classes(remove="bg-warning ")
                ui.notify(f"{kwargs.get('label', 'Setting')} saved", timeout=500)  # , progress=True)

            update_timer(set_storage)

        else:
            pass

    with element_type(
        value=settings.get(key_name), **kwargs,
        on_change=lambda event: delayed_set_storage(key_name, event.value, validation=kwargs.get("validation"))
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
                    user_id, ui.input, "openai_api_key",
                    label="OpenAI API Key", placeholder="\"sk-\" + 48 alphanumeric characters",
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
            pass

    with ui.label("Additional Parameters") as label:
        label.classes(add="text-lg font-bold mt-8")

    json_content = {  # get settings["llm_parameters"]
      "model": "gpt-4-1106-preview",
      "temperature": 0,
      "top_p": None
    }
    with ui.json_editor({"content": {"json": json_content}}) as editor:
        pass
    with ui.button(
            "Save parameters",
            on_click=lambda event: ui.notify("Parameters saved", timeout=500)
    ) as button:
        pass


def update_data_config(user_id: str, data_config: Element, value: str) -> None:
    match value:
        case "Google":
            data_config.clear()
            with data_config:
                with delayed_storage(
                        user_id, ui.input, "custom_search_api_key",
                        label="Google Custom Search API Key",
                        placeholder="39 alphanumeric characters",
                        validation={
                            "Must be 39 characters long": lambda v: len(v) == 39
                        }
                ) as api_key:
                    pass
                with delayed_storage(
                        user_id, ui.input, "custom_search_engine_id",
                        label="Google Custom Search Engine ID",
                        placeholder="17 alphanumeric characters",
                        validation={
                            "Must be 17 characters long": lambda v: len(v) == 17
                        }
                ) as engine_id:
                    pass

        case "Bing":
            data_config.clear()

        case "DuckDuckGo":
            data_config.clear()

import dataclasses
from contextlib import contextmanager
from typing import Callable, Sequence

from loguru import logger
from nicegui import ui, app
from nicegui.element import Element

from dataclasses import dataclass, field


def asdict_recusive(dc: dataclass) -> dict[str, any]:
    return {
        k: asdict_recusive(v) if dataclasses.is_dataclass(v) else v
        for k, v in dataclasses.asdict(dc).items()
    }


@dataclass
class OpenAIParameters:
    # https://platform.openai.com/docs/api-reference/chat/create
    model: str = "gpt-4-1106-preview"  # positional
    # frequency_penalty: float = 0
    # logit_bias: dict[int, float] | None = None
    # logprobs: bool = False
    # top_logprobs: int | None = None
    # max_tokens: int | None = None
    # n: int = 1
    # presence_penalty: float = 0
    # response_format: dict[str, str] | None = None
    # seed: int | None = None
    # stop: str | list[str] | None = None
    temperature: float = 0.  # 1.
    top_p: float | None = None  # 1
    # tools: list[str] = None
    # tool_choice: str | dict[str, any] | None = None
    # user: str | None = None


@dataclass
class GoogleCustomSearch:
    api_key: str | None = None
    engine_id: str | None = None


@dataclass
class UserConfig:
    name_instance: str = "standard instance"
    claim_count: int = 3
    language: str = "default"

    google_custom_search: dict[str, str] | GoogleCustomSearch | None = None

    openai_api_key: str | None = None
    openai_parameters: dict[str, str] | OpenAIParameters | None = None

    def __post_init__(self) -> None:
        if self.google_custom_search is not None and not isinstance(self.google_custom_search, GoogleCustomSearch):
            self.google_custom_search = GoogleCustomSearch(**self.google_custom_search)
        if self.openai_parameters is not None and not isinstance(self.openai_parameters, OpenAIParameters):
            self.openai_parameters = OpenAIParameters(**self.openai_parameters)
        else:
            self.openai_parameters = OpenAIParameters()


def get_user_config(userid: str) -> UserConfig:
    set_config = app.storage.general.get(userid, dict())
    current_config = UserConfig(**set_config)
    print("config", current_config)
    return current_config


def get_config_value(userid: str, key_path: Sequence[str], default: any = None) -> any:
    settings = get_user_config(userid)
    each_setting = dataclasses.asdict(settings)
    for each_key in key_path:
        each_setting = each_setting.get(each_key)
        if each_setting is None:
            logger.error(f"Key path {key_path} not found for reading {userid}")
            return default
    return each_setting


def set_config_value(userid: str, key_path: Sequence[str], value: any) -> None:
    settings = get_user_config(userid)
    settings_dict = dataclasses.asdict(settings)
    root_dict = settings_dict
    for each_key in key_path[:-1]:
        next_dict = settings_dict.get(each_key)
        if next_dict is None:
            next_dict = dict()
            settings_dict[each_key] = next_dict

        settings_dict = next_dict

    last_key = key_path[-1]
    settings_dict[last_key] = value
    app.storage.general[userid] = root_dict


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
                set_config_value(userid, _key_path, value)

                element.classes(remove="bg-warning ")
                ui.notify(f"{kwargs.get('label', 'Setting')} saved", timeout=500)  # , progress=True)

            update_timer(set_storage)

        else:
            pass

    last_value = get_config_value(userid, key_path, default=default)
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
                    user_id, ui.input, ("openai_api_key",),
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
            pass

    with llm_config:
        with ui.expansion("Additional Parameters") as advanced:
            advanced.classes(add="text-lg font-bold mt-8 ")

            settings = get_user_config(user_id)
            print(settings)
            content = {"content": {"json": settings.openai_parameters}}
            with ui.json_editor(content, on_change=lambda: save_parameters_button.enable()) as editor:
                editor.classes(add="w-full ")

            async def save_parameters(event) -> None:
                _settings = get_user_config(user_id)
                editor_content = await editor.run_editor_method("get")
                _settings.openai_parameters = editor_content['json']
                app.storage.general[user_id] = dataclasses.asdict(_settings)
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
                        user_id, ui.input, ("google_custom_search", "api_key"),
                        label="Google Custom Search API Key",
                        placeholder="39 alphanumeric characters",
                        validation={
                            "Must be 39 characters long": lambda v: len(v) == 39
                        }
                ) as api_key:
                    pass
                with delayed_storage(
                        user_id, ui.input, ("google_custom_search", "engine_id"),
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

import dataclasses

from loguru import logger
from nicegui import ui
from nicegui.elements.table import Table

from tools.configuration.data.config_objects import ConfigModel, Store, AccessModel
from tools.plugins.implementation.llm_interfaces.openai_plugin.custom_settings import ParametersOpenAi, InterfaceOpenAi


def openai_config(user_id: str, user_accessible: bool, interface_table: Table) -> None:
    admin = user_id == "ADMIN"

    def _reset_parameters() -> None:
        default_parameters = ParametersOpenAi()
        editor.run_editor_method("set", {"json": dataclasses.asdict(default_parameters)})

    async def _add_new_interface() -> None:
        logger.info(f"adding LLM interface: {user_id}")

        api_key = api_key_input.value
        name = name_input.value
        editor_content = await editor.run_editor_method("get")
        json_content = editor_content['json']

        default_parameters = ParametersOpenAi()
        default_dict = dataclasses.asdict(default_parameters)
        parameters_dict = {key: value for key, value in json_content.items() if key in default_dict}
        parameters = ParametersOpenAi(**parameters_dict)

        new_interface = InterfaceOpenAi(
            name=name, api_key=api_key, parameters=parameters, from_admin=admin)
        ConfigModel.add_llm_interface(user_id, new_interface)
        interface_table.add_rows({'name': name, 'type': 'OpenAI', 'admin': str(admin)})
        name_input.value = ""
        api_key_input.value = ""
        _reset_parameters()
        add_button.disable()

    def _activate_add_button() -> None:
        name_fine = all(
            each_validation(name_input.value) for each_validation in name_input.validation.values())
        key_fine = all(
            each_validation(api_key_input.value) for each_validation in api_key_input.validation.values())

        if name_fine and key_fine:
            add_button.enable()
        else:
            add_button.disable()

    # todo: pull this out as general setting for all llm interfaces
    with ui.input(
            label="Name", placeholder="name for interface",
            validation={"Name already in use": lambda x: x not in [x["name"] for x in interface_table.rows]},
            on_change=_activate_add_button if user_accessible else None
    ) as name_input:
        name_input.classes('w-full')
    with ui.input(
            label="OpenAI API Key", placeholder="\"sk-\" + 48 alphanumeric characters",
            validation={
                "Must start with \"sk-\"": lambda v: v.startswith("sk-"),
                "Must be 51 characters long": lambda v: len(v) == 51
            },
            on_change=_activate_add_button if user_accessible else None

    ) as api_key_input:
        api_key_input.classes('w-full')
    _default = ParametersOpenAi()
    with ui.json_editor({"content": {"json": dataclasses.asdict(_default)}}) as editor:
        editor.classes('w-full')

    with ui.markdown(
            "Go <a href=\"https://platform.openai.com/docs/api-reference/chat/create\" "
            "target=\"_blank\">here</a> for a detailed documentation."
    ) as description:
        description.classes('w-full')

    with ui.markdown(
            "The following OpenAI API parameters have been disabled for compatibility: `logprobs`, `top_logprobs`, "
            "`n`, `response_format`, `seed`, `stop`, and `tools`."
    ) as _:
        pass

    with ui.row().classes('w-full justify-end'):
        reset_button = ui.button("Reset", on_click=_reset_parameters).classes("m-4")
        with ui.button("Add", on_click=_add_new_interface) as add_button:
            add_button.classes("m-4")
            if not user_accessible:
                ui.tooltip("User does not have access to change this setting.")

        add_button.disable()
        if admin:
            with Store(
                    ui.checkbox, AccessModel.set_add_llm,
                    AccessModel.get_add_llm(), text="User access") as _:
                pass

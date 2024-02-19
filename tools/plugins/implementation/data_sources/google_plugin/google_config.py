import dataclasses

from loguru import logger
from nicegui import ui
from nicegui.elements.table import Table

from tools.configuration.data.config_objects import ConfigModel, Store, AccessModel
from tools.plugins.implementation import ParametersGoogle, InterfaceGoogle


def config_google(user_id: str, interface_table: Table, user_accessible: bool, admin: bool) -> None:
    def _reset_parameters() -> None:
        _default = ParametersGoogle("", "")
        editor.run_editor_method("set", {"json": dataclasses.asdict(_default)})

    async def _add_new_interface() -> None:
        logger.info(f"adding data interface: {user_id}")

        name = name_input.value
        editor_content = await editor.run_editor_method("get")
        json_content = editor_content['json']
        cx = json_content.get("cx")
        if cx is None or len(cx) == 0:
            ui.notify("Please provide a custom search engine ID under `cx`.")
            return
        key = json_content.get("key")
        if key is None or len(key) == 0:
            ui.notify("Please provide a Google API key under `key`.")
            return

        max_docs = max_documents_input.value

        default = ParametersGoogle(cx=cx, key=key)
        default_dict = dataclasses.asdict(default)
        parameters_dict = {key: value for key, value in json_content.items() if key in default_dict}
        parameters = ParametersGoogle(**parameters_dict)

        new_interface = InterfaceGoogle(max_documents=max_docs, name=name, parameters=parameters, from_admin=admin)
        ConfigModel.add_data_interface(user_id, new_interface)
        interface_table.add_rows({'name': name, 'type': 'Google', 'admin': str(admin)})
        name_input.value = ""
        max_documents_input.value = 10
        _reset_parameters()
        add_button.disable()

    def _activate_add_button() -> None:
        name_fine = all(
            each_validation(name_input.value) for each_validation in name_input.validation.values())

        if name_fine:
            add_button.enable()
        else:
            add_button.disable()

    # todo: pull this out as general setting for all data interfaces
    with ui.input(
            label="Name", placeholder="name for interface",
            validation={"Name already in use": lambda x: x not in [x["name"] for x in interface_table.rows]},
            on_change=_activate_add_button if user_accessible else None
    ) as name_input:
        name_input.classes('w-full')

    with ui.number(
            label="Max documents per query", placeholder="max number of URIs", value=10, min=1, max=10, step=1
    ) as max_documents_input:
        max_documents_input.classes('w-full')

    _default = ParametersGoogle("", "")
    with ui.json_editor({"content": {"json": dataclasses.asdict(_default)}}) as editor:
        editor.classes('w-full')
    with ui.markdown(
            "Info: `cx` is the custom Google search engine ID, `key` is your Google API key."
    ) as description:
        description.classes('w-full')
    with ui.markdown(
            "Go <a href=\"https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list\" "
            "target=\"_blank\">here</a> for a detailed documentation."
    ) as description:
        description.classes('w-full')

    ui.label("The following Google search API parameters have been disabled: `q`, `num`.").classes('w-full')
    ui.label("The parameter `sort` has been set to a default value of \"date\" for news.").classes('w-full')

    with ui.row().classes('w-full justify-end'):
        ui.button("Reset", on_click=_reset_parameters).classes("m-4")
        with ui.button("Add", on_click=_add_new_interface) as add_button:
            add_button.classes("m-4")
            if not user_accessible:
                ui.tooltip("User does not have access to change this setting.")

        add_button.disable()
        if admin:
            with Store(
                    ui.checkbox, AccessModel.set_add_data,
                    AccessModel.get_add_data(), text="User access") as _:
                pass

import dataclasses

from nicegui import ui

from tools.configuration.data.config_objects import ConfigModel, Store
from tools.plugins.implementation import ParametersGoogle, InterfaceGoogle


def get_section(user_id: str, admin: bool = False) -> None:
    async def _add_new_interface() -> None:
        name = name_input.value
        editor_content = await editor.run_editor_method("get")
        parameters = ParametersGoogle(**editor_content['json'])
        new_interface = InterfaceGoogle(name=name, parameters=parameters)
        ConfigModel.add_data_interface(user_id, new_interface)
        interfaces.add_rows({'name': name, 'type': 'Google'})
        name_input.validate()
        add_button.disable()

    def _remove_data_interface() -> None:
        for each_row in interfaces.selected:
            _each_name = each_row['name']
            ConfigModel.remove_data_interface(user_id, _each_name)
            interfaces.remove_rows(each_row)

    def _activate_add_button() -> None:
        name_fine = all(each_validation(name_input.value) for each_validation in name_input.validation.values())

        if name_fine:
            add_button.enable()
        else:
            add_button.disable()

    with ui.element("div").classes("w-full flex justify-end"):
        ui.label('Existing interfaces').classes('text-h5 p-4')
        columns = [
            {'name': 'name', 'label': 'Name', 'field': 'name'},
            {'name': 'type', 'label': 'Type', 'field': 'type'},
        ]

        rows: list[dict[str, any]] = [
            {'name': each_interface.name, 'type': each_interface.provider}
            for each_interface in ConfigModel.get_data_interfaces(user_id)
        ]

        def remove_button_toggle() -> None:
            if 0 >= len(interfaces.selected):
                remove_button.disable()
            else:
                remove_button.enable()

        interfaces = ui.table(columns, rows, row_key="name", selection="single", on_select=remove_button_toggle).classes('w-full')
        remove_button = ui.button("Remove", on_click=_remove_data_interface).classes("m-4")
        remove_button.disable()
        if admin:
            with Store(
                    ui.checkbox, lambda access: ConfigModel.set_user_access(user_id, "remove_data", access),
                    ConfigModel.get_user_access(user_id, "remove_data"), text="User access") as checkbox:
                pass

    ui.element("div").classes('h-8')
    with ui.element("div").classes("w-full flex justify-end"):
        ui.label('New interface').classes('text-h5 p-4')
        with ui.tabs().classes('w-full') as llm_tabs:
            tabs = {each: ui.tab(each) for each in ["Google"]}
            for each_name, each_tab in tabs.items():
                if each_name != 'Google':
                    each_tab.disable()

        tab_openai = tabs['Google']
        with ui.tab_panels(llm_tabs, value=tab_openai).classes('w-full'):
            with ui.tab_panel(tab_openai):
                with ui.input(
                    label="Name", placeholder="name for interface",
                    validation={"Name already in use": lambda x: x not in [x["name"] for x in interfaces.rows]},
                    on_change=_activate_add_button
                ) as name_input:
                    name_input.classes('w-full')

                default_parameters = ParametersGoogle(cx="", key="")
                with ui.json_editor({"content": {"json": dataclasses.asdict(default_parameters)}}) as editor:
                    editor.classes('w-full')

        with ui.markdown("Info: `cx` is the custom Google search engine ID, `key` is your Google API key.") as description:
            description.classes('w-full')

        add_button = ui.button("Add", on_click=_add_new_interface).classes("m-4")
        add_button.disable()
        if admin:
            with Store(
                    ui.checkbox, lambda access: ConfigModel.set_user_access(user_id, "add_data", access),
                    ConfigModel.get_user_access(user_id, "add_data"), text="User access") as checkbox:
                pass

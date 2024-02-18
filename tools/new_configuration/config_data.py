import dataclasses

from loguru import logger
from nicegui import ui

from tools.configuration.data.config_objects import ConfigModel, Store, AccessModel
from tools.plugins.implementation import ParametersGoogle, InterfaceGoogle


def get_section(user_id: str, admin: bool = False) -> None:
    def _reset_parameters() -> None:
        _default = ParametersGoogle("", "")
        editor.run_editor_method("set", {"json": dataclasses.asdict(_default)})

    async def _add_new_interface() -> None:
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

        print(f"adding data interface: {user_id}")
        # todo: prevent passing arguments not in ParametersGoogle
        parameters = ParametersGoogle(**json_content)
        new_interface = InterfaceGoogle(name=name, parameters=parameters, from_admin=admin)
        ConfigModel.add_data_interface(user_id, new_interface)
        interface_table.add_rows({'name': name, 'type': 'Google', 'admin': str(admin)})
        name_input.value = ""
        _reset_parameters()
        add_button.disable()

    def _remove_data_interface() -> None:
        if len(interface_table.selected) != 1:
            ui.notify("Please select exactly one data interface to remove.")
            return

        selected_interface = interface_table.selected[0]
        selected_name = selected_interface['name']
        data_interface = ConfigModel.get_data_interface(user_id, selected_name)
        if data_interface is None:
            logger.error(f"Removing data interface {selected_name} failed.")
            return

        if data_interface.from_admin and not admin:
            ui.notify(f"Data interface {selected_name} is from admin and cannot be removed by user.")
            return

        interface_retrieval = ConfigModel.get_retrieval_data(user_id)
        if interface_retrieval is not None and selected_name == interface_retrieval.name:
            ui.notify(f"Data interface {selected_name} in use for retrieval.")
            return

        interface_comparison = ConfigModel.get_comparison_data(user_id)
        if interface_comparison is not None and selected_name == interface_comparison.name:
            ui.notify(f"Data interface {selected_name} in use for comparison.")
            return

        ConfigModel.remove_data_interface(user_id, selected_name)
        interface_table.remove_rows(selected_interface)
        ui.notify(f"Data interface {selected_name} removed.")

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
            {'name': 'admin', 'label': 'Admin', 'field': 'admin'}
        ]

        data_interfaces = ConfigModel.get_data_interfaces(user_id)
        if not admin:
            data_interfaces += ConfigModel.get_data_interfaces("ADMIN")

        rows: list[dict[str, any]] = [
            {
                'name': each_interface.name,
                'type': each_interface.provider,
                'admin': str(each_interface.from_admin)
            }
            for each_interface in data_interfaces
        ]

        def _toggle_remove() -> None:
            if len(interface_table.selected) == 1:
                remove_button.enable()
            else:
                remove_button.disable()

        interface_table = ui.table(columns, rows, row_key="name", selection="single").classes('w-full')
        remove_button = ui.button("Remove", on_click=_remove_data_interface).classes("m-4")
        remove_button.disable()
        if not (admin or AccessModel.get_remove_data()):
            with remove_button:
                ui.tooltip("User does not have access to remove this setting.")
        else:
            interface_table.on("selection", _toggle_remove)

        if admin:
            with Store(
                    ui.checkbox, AccessModel.set_remove_data,
                    AccessModel.get_remove_data(), text="User access") as checkbox:
                pass

    ui.element("div").classes('h-8')

    user_accessible = admin or AccessModel.get_add_data()

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
                    validation={"Name already in use": lambda x: x not in [x["name"] for x in interface_table.rows]},
                    on_change=_activate_add_button if user_accessible else None
                ) as name_input:
                    name_input.classes('w-full')

                default_parameters = ParametersGoogle(cx="", key="")
                with ui.json_editor({"content": {"json": dataclasses.asdict(default_parameters)}}) as editor:
                    editor.classes('w-full')

        with ui.markdown("Info: `cx` is the custom Google search engine ID, `key` is your Google API key.") as description:
            description.classes('w-full')

        reset_button = ui.button("Reset", on_click=_reset_parameters).classes("m-4")
        with ui.button("Add", on_click=_add_new_interface) as add_button:
            add_button.classes("m-4")
            if not user_accessible:
                ui.tooltip("User does not have access to change this setting.")

        add_button.disable()
        if admin:
            with Store(
                    ui.checkbox, AccessModel.set_add_data,
                    AccessModel.get_add_data(), text="User access") as checkbox:
                pass

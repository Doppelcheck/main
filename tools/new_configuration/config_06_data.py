from loguru import logger
from nicegui import ui

from tools.configuration.data.config_objects import ConfigModel, Store, AccessModel
from tools.plugins.implementation.data_sources.google_plugin.google_config import config_google


def get_section(user_id: str, admin: bool = False) -> None:

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

        tab_openai = tabs['Google']
        with ui.tab_panels(llm_tabs, value=tab_openai).classes('w-full'):
            with ui.tab_panel(tab_openai):
                config_google(user_id, interface_table, user_accessible, admin)

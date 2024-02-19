from loguru import logger
from nicegui import ui

from tools.configuration.data.config_objects import ConfigModel, Store, AccessModel
from tools.plugins.implementation.llm_interfaces.openai_plugin.configuration_page import openai_config


def get_section(user_id: str, admin: bool = False) -> None:
    def _remove_llm_interface() -> None:
        if len(interface_table.selected) != 1:
            ui.notify("Please select exactly one LLM interface to remove.")
            return

        selected_interface = interface_table.selected[0]
        selected_name = selected_interface['name']
        llm_interface = ConfigModel.get_llm_interface(user_id, selected_name)
        if llm_interface is None:
            logger.error(f"Removing LLM interface {selected_name} failed.")
            return

        if llm_interface.from_admin and not admin:
            ui.notify(f"LLM interface {selected_name} is from admin and cannot be removed by user.")
            return

        interface_extraction = ConfigModel.get_extraction_llm(user_id)
        if interface_extraction is not None and selected_name == interface_extraction.name:
            ui.notify(f"LLM interface {selected_name} in use for extraction.")
            return

        interface_retrieval = ConfigModel.get_retrieval_llm(user_id)
        if interface_retrieval is not None and selected_name == interface_retrieval.name:
            ui.notify(f"LLM interface {selected_name} in use for retrieval.")
            return

        interface_comparison = ConfigModel.get_comparison_llm(user_id)
        if interface_comparison is not None and selected_name == interface_comparison.name:
            ui.notify(f"LLM interface {selected_name} in use for comparison.")
            return

        ConfigModel.remove_llm_interface(user_id, selected_name)
        interface_table.remove_rows(selected_interface)
        ui.notify(f"LLM interface {selected_name} removed.")

    with ui.element("div").classes("w-full flex justify-end"):
        ui.label('Existing interfaces').classes('text-h5 p-4')
        columns = [
            {'name': 'name', 'label': 'Name', 'field': 'name'},
            {'name': 'type', 'label': 'Type', 'field': 'type'},
            {'name': 'admin', 'label': 'Admin', 'field': 'admin'}
        ]

        llm_interfaces = ConfigModel.get_llm_interfaces(user_id)
        if not admin:
            llm_interfaces += ConfigModel.get_llm_interfaces("ADMIN")

        rows: list[dict[str, any]] = [
            {
                'name': each_interface.name,
                'type': each_interface.provider,
                'admin': str(each_interface.from_admin)
            }
            for each_interface in llm_interfaces
        ]

        def _toggle_remove() -> None:
            if len(interface_table.selected) == 1:
                remove_button.enable()
            else:
                remove_button.disable()

        interface_table = ui.table(columns, rows, row_key="name", selection="single")
        interface_table.classes('w-full')
        remove_button = ui.button("Remove", on_click=_remove_llm_interface).classes("m-4")
        remove_button.disable()
        if not (admin or AccessModel.get_remove_llm()):
            with remove_button:
                ui.tooltip("User does not have access to remove this setting.")
        else:
            interface_table.on("selection", _toggle_remove)

        if admin:
            with Store(
                    ui.checkbox, AccessModel.set_remove_llm,
                    AccessModel.get_remove_llm(), text="User access") as checkbox:
                pass

    ui.element("div").classes('h-8')

    user_accessible = admin or AccessModel.get_add_llm()

    with ui.element("div").classes("w-full flex justify-end"):
        ui.label('New interface').classes('text-h5 p-4')
        with ui.tabs().classes('w-full') as llm_tabs:
            tabs = {each: ui.tab(each) for each in ["OpenAI"]}
            for each_name, each_tab in tabs.items():
                if each_name != 'OpenAI':
                    each_tab.disable()

        tab_openai = tabs['OpenAI']
        with ui.tab_panels(llm_tabs, value=tab_openai).classes('w-full'):
            with ui.tab_panel(tab_openai):
                openai_config(user_id, user_accessible, interface_table)

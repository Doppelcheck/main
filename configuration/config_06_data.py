from loguru import logger
from nicegui import ui

from model.storages import ConfigModel, AccessModel, Store
from plugins.abstract import InterfaceData


def get_section_data_sources(user_id: str, data_classes: list[type[InterfaceData]], is_admin: bool = False) -> None:
    def _remove_data_interface() -> None:
        if len(interface_table.selected) != 1:
            ui.notify("Please select exactly one data interface to remove.")
            return

        selected_interface = interface_table.selected[0]
        selected_name = selected_interface['name']
        data_interface = ConfigModel.get_data_interface(user_id, selected_name, is_admin)
        if data_interface is None:
            logger.error(f"Removing data interface '{selected_name}' failed.")
            return

        if data_interface.from_admin and not is_admin:
            ui.notify(f"Data interface '{selected_name}' is from admin and cannot be removed by user.")
            return

        interface_retrieval = ConfigModel.get_retrieval_data(user_id, is_admin)
        if interface_retrieval is not None and selected_name == interface_retrieval.name:
            ui.notify(f"Data interface '{selected_name}' in use for retrieval.")
            return

        interface_comparison = ConfigModel.get_comparison_data(user_id, is_admin)
        if interface_comparison is not None and selected_name == interface_comparison.name:
            ui.notify(f"Data interface '{selected_name}' in use for comparison.")
            return

        ConfigModel.remove_data_interface(user_id, selected_name, is_admin)
        interface_table.remove_rows(selected_interface)
        ui.notify(f"Data interface '{selected_name}' removed.")

    with ui.element("div").classes("w-full flex justify-end"):
        ui.label('Existing interfaces').classes('text-h5 p-4')
        columns = [
            {'name': 'name', 'label': 'Name', 'field': 'name'},
            {'name': 'type', 'label': 'Type', 'field': 'type'},
            {'name': 'admin', 'label': 'Admin', 'field': 'admin'}
        ]

        data_interfaces = ConfigModel.get_data_interfaces(user_id, is_admin)

        rows: list[dict[str, any]] = [
            {
                'name': each_interface.name,
                'type': type(each_interface).__qualname__,
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
        if not (is_admin or AccessModel.get_remove_data()):
            with remove_button:
                ui.tooltip("User does not have access to remove this setting.")
        else:
            interface_table.on("selection", _toggle_remove)

        if is_admin:
            with ui.checkbox(
                    text="User access", value=AccessModel.get_remove_data()
            ) as checkbox, Store(checkbox, AccessModel.set_remove_data):
                pass

    ui.element("div").classes('h-8')

    user_accessible = is_admin or AccessModel.get_add_data()

    callback_dict = dict()
    with ui.element("div").classes("w-full flex justify-end"):
        ui.label('New interface').classes('text-h5 p-4')
        with ui.tabs().classes('w-full') as llm_tabs:
            name_to_tabs = {each.name(): ui.tab(each.name()) for each in data_classes}
            # todo: add panel right away

        for each_class in data_classes:
            each_tab = name_to_tabs[each_class.name()]
            with ui.tab_panels(llm_tabs, value=each_tab).classes('w-full') as tab_panels:
                with ui.tab_panel(each_tab):
                    with ui.input(
                            label="Name", placeholder="name for interface",
                            validation={
                                "Name already in use, will overwrite!":
                                    lambda x: x not in [x["name"] for x in interface_table.rows]}
                    ) as name_input:
                        name_input.classes('w-full')

                    each_callbacks = each_class.configuration(user_id, user_accessible, is_admin)
                    callback_dict[each_tab] = each_callbacks

        async def _add_interface() -> None:
            _callbacks = callback_dict[llm_tabs.value]
            interface_config = await _callbacks.get_config()
            interface_config.name = name_input.value
            # todo: check if fine

            ConfigModel.add_data_interface(user_id, interface_config)
            interface_table.add_rows(
                {'name': interface_config.name, 'type': type(interface_config).__qualname__, 'admin': str(is_admin)}
            )
            name_input.value = ""

        with ui.row().classes('w-full justify-end'):
            ui.button("Reset", on_click=lambda: callback_dict[llm_tabs.value].reset()).classes("m-4")
            ui.button("Add", on_click=_add_interface).classes("m-4")
            if is_admin:
                with ui.checkbox(
                    text="User access", value=AccessModel.get_add_data()
                ) as checkbox, Store(checkbox, AccessModel.set_add_data):
                    pass

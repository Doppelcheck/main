from loguru import logger
from nicegui import ui

from model.storages import ConfigModel, AccessModel
from model.storage_tools import Store
from plugins.abstract import InterfaceLLM, ConfigurationCallbacks


def get_section_language_models(instance_id: str | None, llm_classes: list[type[InterfaceLLM]]) -> None:
    def _remove_llm_interface() -> None:
        if len(interface_table.selected) != 1:
            ui.notify("Please select exactly one LLM interface to remove.")
            return

        selected_interface = interface_table.selected[0]
        selected_name = selected_interface['name']
        llm_interface = ConfigModel.get_llm_interface(instance_id, selected_name)
        if llm_interface is None:
            logger.error(f"Removing LLM interface {selected_name} failed.")
            return

        if llm_interface.from_admin and instance_id is not None:
            ui.notify(f"LLM interface '{selected_name}' is from admin and cannot be removed by user.")
            return

        interface_extraction = ConfigModel.get_extraction_llm(instance_id)
        if interface_extraction is not None and selected_name == interface_extraction.name:
            ui.notify(f"LLM interface '{selected_name}' in use for extraction.")
            return

        interface_retrieval = ConfigModel.get_retrieval_llm(instance_id)
        if interface_retrieval is not None and selected_name == interface_retrieval.name:
            ui.notify(f"LLM interface '{selected_name}' in use for retrieval.")
            return

        interface_comparison = ConfigModel.get_comparison_llm(instance_id)
        if interface_comparison is not None and selected_name == interface_comparison.name:
            ui.notify(f"LLM interface '{selected_name}' in use for comparison.")
            return

        ConfigModel.remove_llm_interface(instance_id, selected_name)
        interface_table.remove_rows(selected_interface)
        ui.notify(f"LLM interface '{selected_name}' removed.")

    def _toggle_remove() -> None:
        if len(interface_table.selected) == 1:
            remove_button.enable()
        else:
            remove_button.disable()

    with ui.element("div").classes("w-full flex justify-end"):
        ui.label('Existing interfaces').classes('text-h5 p-4')
        columns = [
            {'name': 'name', 'label': 'Name', 'field': 'name'},
            {'name': 'type', 'label': 'Type', 'field': 'type'},
            {'name': 'admin', 'label': 'Admin', 'field': 'admin'}
        ]

        llm_interfaces = ConfigModel.get_llm_interfaces(instance_id)

        rows: list[dict[str, any]] = [
            {
                'name': each_name,
                'type': type(each_interface).__qualname__,
                'admin': str(each_interface.from_admin)
            }
            for each_name, each_interface in llm_interfaces.items()
        ]

        interface_table = ui.table(columns, rows, row_key="name", selection="single")
        interface_table.classes('w-full')
        remove_button = ui.button("Remove", on_click=_remove_llm_interface).classes("m-4")
        remove_button.disable()
        if not ((instance_id is None) or AccessModel.get_remove_llm()):
            with remove_button:
                ui.tooltip("User does not have access to remove this.")
        else:
            interface_table.on("selection", _toggle_remove)

        if instance_id is None:
            with ui.checkbox(
                text="User access", value=AccessModel.get_remove_llm()
            ) as checkbox, Store(checkbox, AccessModel.set_remove_llm):
                pass

    ui.element("div").classes('h-8')

    user_accessible = (instance_id is None) or AccessModel.get_add_llm()

    with ui.element("div").classes("w-full flex justify-end"):
        ui.label('New interface').classes('text-h5 p-4')

        # top tab header
        with ui.tabs().classes('w-full') as llm_tabs:
            tabs = {each.name(): ui.tab(each.name()) for each in llm_classes}
            # todo: add panel right away

        async def _add_interface(callbacks: ConfigurationCallbacks, name_input_field: ui.input) -> None:
            interface_config = await callbacks.get_config()
            interface_config.name = name_input_field.value
            # todo: check if fine

            ConfigModel.add_llm_interface(instance_id, interface_config)
            interface_table.add_rows(
                {
                    'name': interface_config.name,
                    'type': type(interface_config).__qualname__,
                    'admin': str(instance_id is None)
                }
            )

            name_input_field.value = ""

        for each_class in llm_classes:
            each_name = each_class.name()
            each_tab = tabs[each_name]
            with ui.tab_panels(llm_tabs, value=each_tab).classes('w-full'):
                with ui.tab_panel(each_tab):
                    with ui.input(
                        label="Name", placeholder="name for interface",
                        validation={
                            "Name already in use, will overwrite!":
                            lambda x: x not in [x["name"] for x in interface_table.rows]}
                    ) as name_input:
                        name_input.classes('w-full')

                    each_callbacks = each_class.configuration(instance_id, user_accessible)

                    def _make_add_handler(callbacks: ConfigurationCallbacks, name_input_field: ui.input) -> callable:
                        async def handler() -> None:
                            await _add_interface(callbacks, name_input_field)

                        return handler

                    with ui.row().classes('w-full justify-end'):
                        ui.button("Reset", on_click=each_callbacks.reset).classes("m-4")
                        add_handler = _make_add_handler(each_callbacks, name_input)
                        ui.button("Add", on_click=add_handler).classes("m-4")

                        if instance_id is None:
                            with ui.checkbox(
                                    text="User access", value=AccessModel.get_add_llm()
                            ) as checkbox, Store(checkbox, AccessModel.set_add_llm):
                                pass

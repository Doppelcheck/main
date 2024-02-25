from nicegui import ui

from model.storages import ConfigModel, Store, AccessModel


def get_section_crosschecker(user_id: str, is_admin: bool = False) -> None:
    llm_interfaces = ConfigModel.get_llm_interfaces(user_id, is_admin)
    data_interfaces = ConfigModel.get_data_interfaces(user_id, is_admin)

    def _update_llms() -> None:
        nonlocal llm_interfaces
        llm_interfaces = ConfigModel.get_llm_interfaces(user_id, is_admin)
        llm_select.options = [each_interface.name for each_interface in llm_interfaces]
        llm_select.update()

    def _update_data() -> None:
        nonlocal data_interfaces
        data_interfaces = ConfigModel.get_data_interfaces(user_id, is_admin)
        data_select.options = [each_interface.name for each_interface in data_interfaces]
        data_select.update()

    with ui.element("div").classes("w-full flex justify-end"):
        default_llm = ConfigModel.get_comparison_llm(user_id, is_admin)
        with ui.select(
            options=[each_interface.name for each_interface in llm_interfaces],
            value=None if default_llm is None else default_llm.name, label="LLM interface for comparison"
        ) as llm_select, Store(llm_select, lambda name: ConfigModel.set_comparison_llm(user_id, name)):
            llm_select.classes('w-full').on("click", _update_llms)
            if not is_admin and not AccessModel.get_comparison_llm():
                llm_select.disable()
                ui.tooltip("User does not have access to change this setting.")

        if is_admin:
            with ui.checkbox(
                text="User access", value=AccessModel.get_comparison_llm()
            ) as checkbox, Store(checkbox, AccessModel.set_comparison_llm):
                pass

        default_data = ConfigModel.get_comparison_data(user_id, is_admin)
        with ui.select(
            options=[each_interface.name for each_interface in data_interfaces],
            value=None if default_data is None else default_data.name, label="Data interface for comparison"
        ) as data_select, Store(data_select, lambda name: ConfigModel.set_comparison_data(user_id, name)):
            data_select.classes('w-full').on("click", _update_data)
            if not is_admin and not AccessModel.get_comparison_data():
                data_select.disable()
                ui.tooltip("User does not have access to change this setting.")

        if is_admin:
            with ui.checkbox(
                text="User access", value=AccessModel.get_comparison_data()
            ) as checkbox, Store(checkbox, AccessModel.set_comparison_data):
                pass

        # ===
        with ui.textarea(
                label="Comparison prompt", validation=None, value=ConfigModel.get_comparison_prompt(user_id, is_admin)
        ) as textarea, Store(textarea, lambda value: ConfigModel.set_comparison_prompt(user_id, value)):
            textarea.classes('w-full')
            if not is_admin and not AccessModel.get_comparison_prompt():
                textarea.disable()

        if is_admin:
            with ui.checkbox(
                text="User access", value=AccessModel.get_comparison_prompt()
            ) as checkbox, Store(checkbox, AccessModel.set_comparison_prompt):
                pass


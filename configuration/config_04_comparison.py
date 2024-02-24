from nicegui import ui

from model.storages import ConfigModel, Store, AccessModel


def get_section_crosschecker(user_id: str, admin: bool = False) -> None:
    llm_interfaces = ConfigModel.get_llm_interfaces(user_id)
    data_interfaces = ConfigModel.get_data_interfaces(user_id)

    def _update_llms() -> None:
        nonlocal llm_interfaces
        llm_interfaces = ConfigModel.get_llm_interfaces(user_id)
        llm_select.options = [each_interface.name for each_interface in llm_interfaces]
        llm_select.update()

    def _update_data() -> None:
        nonlocal data_interfaces
        data_interfaces = ConfigModel.get_data_interfaces(user_id)
        data_select.options = [each_interface.name for each_interface in data_interfaces]
        data_select.update()

    with ui.element("div").classes("w-full flex justify-end"):
        default_llm = ConfigModel.get_comparison_llm(user_id)
        with ui.select(
            options=[each_interface.name for each_interface in llm_interfaces],
            value=None if default_llm is None else default_llm.name, label="LLM interface for comparison"
        ) as llm_select, Store(llm_select, lambda name: ConfigModel.set_comparison_llm(user_id, name)):
            llm_select.classes('w-full').on("click", _update_llms)
            if not admin and not AccessModel.get_comparison_llm():
                llm_select.disable()
                ui.tooltip("User does not have access to change this setting.")

        if admin:
            with ui.checkbox(
                text="User access", value=AccessModel.get_comparison_llm()
            ) as checkbox, Store(checkbox, AccessModel.set_comparison_llm):
                pass

        default_data = ConfigModel.get_comparison_data(user_id)
        with ui.select(
            options=[each_interface.name for each_interface in data_interfaces],
            value=None if default_data is None else default_data.name, label="Data interface for comparison"
        ) as data_select, Store(data_select, lambda name: ConfigModel.set_comparison_data(user_id, name)):
            data_select.classes('w-full').on("click", _update_data)
            if not admin and not AccessModel.get_comparison_data():
                data_select.disable()
                ui.tooltip("User does not have access to change this setting.")

        if admin:
            with ui.checkbox(
                text="User access", value=AccessModel.get_comparison_data()
            ) as checkbox, Store(checkbox, AccessModel.set_comparison_data):
                pass

        with ui.textarea(label="Comparison prompt", validation=None) as textarea:
            # todo: add validation to make sure variables are included etc
            textarea.classes('w-full')
            textarea.disable()

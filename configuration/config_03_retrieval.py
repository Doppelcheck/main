from nicegui import ui

from model.storages import ConfigModel, Store, AccessModel


def get_section_sourcefinder(user_id: str, is_admin: bool = False) -> None:
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
        default_llm = ConfigModel.get_retrieval_llm(user_id, is_admin)
        with ui.select(
            options=[each_interface.name for each_interface in llm_interfaces],
            label="LLM interface for retrieval", value=None if default_llm is None else default_llm.name
        ) as llm_select, Store(llm_select, lambda name: ConfigModel.set_retrieval_llm(user_id, name)):
            llm_select.classes('w-full').on("click", _update_llms)
            if not is_admin and not AccessModel.get_retrieval_llm():
                llm_select.disable()
                ui.tooltip("User does not have access to change this setting.")

        if is_admin:
            with ui.checkbox(
                text="User access", value=AccessModel.get_retrieval_llm()
            ) as checkbox, Store(checkbox, AccessModel.set_retrieval_llm):
                pass

        default_data = ConfigModel.get_retrieval_data(user_id, is_admin)
        with ui.select(
            options=[each_interface.name for each_interface in data_interfaces],
            label="Data interface for retrieval", value=None if default_data is None else default_data.name
        ) as data_select, Store(data_select, lambda name: ConfigModel.set_retrieval_data(user_id, name)):
            data_select.classes('w-full').on("click", _update_data)
            if not is_admin and not AccessModel.get_retrieval_data():
                data_select.disable()
                ui.tooltip("User does not have access to change this setting.")

        if is_admin:
            with ui.checkbox(
                text="User access", value=AccessModel.get_retrieval_data()
            ) as checkbox, Store(checkbox, AccessModel.set_retrieval_data):
                pass

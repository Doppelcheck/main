from nicegui import ui

from tools.configuration.data.config_objects import ConfigModel, Store, AccessModel


def get_section(user_id: str, admin: bool = False) -> None:
    llm_interfaces = ConfigModel.get_llm_interfaces(user_id)
    llm_names = [each_interface.name for each_interface in llm_interfaces]

    data_interfaces = ConfigModel.get_data_interfaces(user_id)
    data_names = [each_interface.name for each_interface in data_interfaces]

    def _refresh() -> None:
        _llm_interfaces = ConfigModel.get_llm_interfaces(user_id)
        _llm_names = [each_interface.name for each_interface in _llm_interfaces]
        llm_select.options = _llm_names
        llm_select.update()

        _data_interfaces = ConfigModel.get_data_interfaces(user_id)
        _data_names = [each_interface.name for each_interface in _data_interfaces]
        data_select.options = _data_names
        data_select.update()

    with ui.element("div").classes("w-full flex justify-end"):
        default_llm = llm_names[0] if 0 < len(llm_names) else None
        with Store(
                ui.select, lambda name: ConfigModel.set_retrieval_llm(user_id, name),
                default_llm, label="LLM interface for retrieval", options=llm_names) as llm_select:
            llm_select.classes('w-full').on("click", _refresh)

        if not admin and not AccessModel.get_retrieval_llm():
            llm_select.disable()
            ui.tooltip("User does not have access to change this setting.")

        if admin:
            with Store(
                    ui.checkbox, AccessModel.set_retrieval_llm,
                    AccessModel.get_retrieval_llm(), text="User access") as checkbox:
                pass

        default_data = data_names[0] if 0 < len(data_names) else None
        with Store(
                ui.select, lambda name: ConfigModel.set_retrieval_data(user_id, name),
                default_data, label="Data interface for retrieval", options=data_names) as data_select:
            data_select.classes('w-full').on("click", _refresh)

        if not admin and not AccessModel.get_retrieval_data():
            data_select.disable()
            ui.tooltip("User does not have access to change this setting.")

        if admin:
            with Store(
                    ui.checkbox, AccessModel.set_retrieval_data,
                    AccessModel.get_retrieval_data(), text="User access") as checkbox:
                pass

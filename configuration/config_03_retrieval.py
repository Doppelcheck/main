from nicegui import ui

from model.storages import ConfigModel, AccessModel
from model.storage_tools import Store


def get_section_sourcefinder(user_id: str | None) -> None:
    llm_interfaces = ConfigModel.get_llm_interfaces(user_id)
    data_interfaces = ConfigModel.get_data_interfaces(user_id)

    def _update_llms() -> None:
        nonlocal llm_interfaces
        llm_interfaces = ConfigModel.get_llm_interfaces(user_id)
        llm_select.options = [each_name for each_name in llm_interfaces]
        llm_select.update()

    with ui.element("div").classes("w-full flex justify-end"):
        default_llm = ConfigModel.get_retrieval_llm(user_id)
        with ui.select(
            options=[each_name for each_name in llm_interfaces],
            label="LLM interface for retrieval", value=None if default_llm is None else default_llm.name
        ) as llm_select, Store(llm_select, lambda name: ConfigModel.set_retrieval_llm(user_id, name)):
            llm_select.classes('w-full').on("click", _update_llms)
            if (user_id is not None) and not AccessModel.get_retrieval_llm():
                llm_select.disable()
                ui.tooltip("User does not have access to change this setting.")

        if user_id is None:
            with ui.checkbox(
                text="User access", value=AccessModel.get_retrieval_llm()
            ) as checkbox, Store(checkbox, AccessModel.set_retrieval_llm):
                pass

from nicegui import ui

from tools.configuration.data.config_objects import ConfigModel, Store, AccessModel


def get_section(user_id: str, admin: bool = False) -> None:
    # todo: if locked by admin: https://nicegui.io/documentation/badge
    llm_interfaces = ConfigModel.get_llm_interfaces(user_id)
    names = [each_interface.name for each_interface in llm_interfaces]

    def refresh() -> None:
        _llm_interfaces = ConfigModel.get_llm_interfaces(user_id)
        _names = [each_interface.name for each_interface in _llm_interfaces]
        select.options = _names
        select.update()

    with ui.element("div").classes("w-full flex justify-end"):
        default = names[0] if 0 < len(names) else None
        with Store(
                ui.select, lambda name: ConfigModel.set_extraction_llm(user_id, name),
                default, label="LLM interface for extraction", options=names) as select:
            select.classes('w-full').on("click", refresh)

        if not admin and not AccessModel.get_extraction_llm():
            select.disable()
            ui.tooltip("User does not have access to change this setting.")

        if admin:
            with Store(
                    ui.checkbox, AccessModel.set_extraction_llm,
                    AccessModel.get_extraction_llm(), text="User access") as checkbox:
                pass

        with Store(
                ui.number, lambda count: ConfigModel.set_extraction_claims(user_id, count),
                ConfigModel.get_extraction_claims(user_id), label="Claim count",
                placeholder="number of claims", min=1, max=10) as text_input:
            text_input.classes('w-full')

        if not admin and not AccessModel.get_extraction_claims():
            text_input.disable()
            ui.tooltip("User does not have access to change this setting.")

        if admin:
            with Store(
                    ui.checkbox, AccessModel.set_extraction_claims,
                    AccessModel.get_extraction_claims(), text="User access") as checkbox:
                pass

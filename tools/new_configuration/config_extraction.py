from nicegui import ui

from tools.configuration.data.config_objects import ConfigModel, Store


def get_section(user_id: str, admin: bool = False) -> None:
    llm_interfaces = ConfigModel.get_llm_interfaces(user_id)
    names = [each_interface.name for each_interface in llm_interfaces]

    def refresh():
        _llm_interfaces = ConfigModel.get_llm_interfaces(user_id)
        _names = [each_interface.name for each_interface in _llm_interfaces]
        select.options = _names
        select.update()
        print(_names)

    with ui.element("div").classes("w-full flex justify-end"):
        default = names[0] if 0 < len(names) else None
        with Store(
                ui.select, lambda name: ConfigModel.set_extraction_llm(user_id, name),
                default, label="Select LLM Interface", options=names) as select:
            select.classes('w-full').on("click", refresh)

        if admin:
            with Store(
                    ui.checkbox, lambda access: ConfigModel.set_user_access(user_id, "select_llm", access),
                    ConfigModel.get_user_access(user_id, "select_llm"), text="User access") as checkbox:
                pass

        with Store(
                ui.number, lambda count: ConfigModel.set_extraction_claims(user_id, count),
                ConfigModel.get_extraction_claims(user_id), label="Claim Count",
                placeholder="number of claims", min=1, max=10) as text_input:
            text_input.classes('w-full')

        if admin:
            with Store(
                    ui.checkbox, lambda access: ConfigModel.set_user_access(user_id, "claim_count", access),
                    ConfigModel.get_user_access(user_id, "claim_count"), text="User access") as checkbox:
                pass

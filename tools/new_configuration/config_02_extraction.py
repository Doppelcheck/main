from nicegui import ui

from tools.configuration.data.config_objects import ConfigModel, AccessModel, Store


def get_section(user_id: str, admin: bool = False) -> None:
    # todo: if locked by admin: https://nicegui.io/documentation/badge
    llm_interfaces = ConfigModel.get_llm_interfaces(user_id)

    def _update() -> None:
        nonlocal llm_interfaces
        llm_interfaces = ConfigModel.get_llm_interfaces(user_id)
        select.options = [each_interface.name for each_interface in llm_interfaces]
        select.update()

    with ui.element("div").classes("w-full flex justify-end"):
        default_llm = ConfigModel.get_extraction_llm(user_id)

        with ui.select(
                options=[each_interface.name for each_interface in llm_interfaces], label="LLM interface for extraction",
                value=None if default_llm is None else default_llm.name
        ) as select, Store(select, lambda name: ConfigModel.set_extraction_llm(user_id, name)):
            select.classes('w-full').on("click", _update)
            if not admin and not AccessModel.get_extraction_llm():
                # select.tooltip("User does not have access to change this setting.")
                select.disable()

        if admin:
            with ui.checkbox(
                    text="User access", value=AccessModel.get_extraction_llm()
            ) as checkbox, Store(checkbox, AccessModel.set_extraction_llm):
                pass

        with ui.number(
            label="Claim count", placeholder="number of claims", min=1, max=10,
            value=ConfigModel.get_extraction_claims(user_id)
        ) as number, Store(number, lambda count: ConfigModel.set_extraction_claims(user_id, count)):
            number.classes('w-full')
            if not admin and not AccessModel.get_extraction_claims():
                number.disable()
                # ui.tooltip("User does not have access to change this setting.")

        if admin:
            with ui.checkbox(
                    text="User access", value=AccessModel.get_extraction_claims()
            ) as checkbox, Store(checkbox, AccessModel.set_extraction_claims):
                pass

        with ui.textarea(label="Extraction prompt", validation=None) as textarea:
            # todo: add validation to make sure variables are included etc
            textarea.classes('w-full')
            textarea.disable()

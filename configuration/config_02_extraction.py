from nicegui import ui

from model.storages import ConfigModel, AccessModel
from model.storage_tools import Store


DEFAULT_CUSTOM_EXTRACTION_PROMPT = (
    "The text is a news report. Extract its key factual claims, make absolute time and place references where "
    "possible. Exclude examples, questions, opinions, personal feelings, prose, advertisements, and other "
    "non-factual elements. IMPORTANT: Use telegram style (aka. \"telegraphese\")."
)


def get_section_keypoint(user_id: str | None) -> None:
    # todo: if locked by admin: https://nicegui.io/documentation/badge
    llm_interfaces = ConfigModel.get_llm_interfaces(user_id)

    def _update() -> None:
        nonlocal llm_interfaces
        llm_interfaces = ConfigModel.get_llm_interfaces(user_id)
        select.options = [each_name for each_name in llm_interfaces]
        select.update()

    with ui.element("div").classes("w-full flex justify-end"):
        default_llm = ConfigModel.get_extraction_llm(user_id)

        with ui.select(
                options=[each_name for each_name in llm_interfaces],
                label="LLM interface for extraction",
                value=None if default_llm is None else default_llm.name
        ) as select, Store(select, lambda name: ConfigModel.set_extraction_llm(user_id, name)):
            select.classes('w-full').on("click", _update)
            if user_id is not None and not AccessModel.get_extraction_llm():
                # select.tooltip("User does not have access to change this setting.")
                select.disable()

        if user_id is None:
            with ui.checkbox(
                    text="User access", value=AccessModel.get_extraction_llm()
            ) as checkbox, Store(checkbox, AccessModel.set_extraction_llm):
                pass

        with ui.select(
                options=["LLM only", "NLP supported"], label="Extraction mode",
                value=ConfigModel.get_extraction_mode(user_id)
        ) as mode_select, Store(
            mode_select, lambda mode: ConfigModel.set_extraction_mode(user_id, mode)
        ):
            mode_select.classes('w-full')
            if user_id is not None and not AccessModel.get_extraction_mode():
                mode_select.disable()
                # ui.tooltip("User does not have access to change this setting.")

        if user_id is None:
            with ui.checkbox(
                    text="User access", value=AccessModel.get_extraction_mode()
            ) as checkbox, Store(checkbox, AccessModel.set_extraction_mode):
                pass

        with ui.number(
            label="Claim count", placeholder="number of claims", min=1, max=10,
            value=ConfigModel.get_number_of_keypoints(user_id)
        ) as number, Store(number, lambda count: ConfigModel.set_extraction_claims(user_id, count)):
            number.classes('w-full')
            if user_id is not None and not AccessModel.get_extraction_claims():
                number.disable()
                # ui.tooltip("User does not have access to change this setting.")

        if user_id is None:
            with ui.checkbox(
                    text="User access", value=AccessModel.get_extraction_claims()
            ) as checkbox, Store(checkbox, AccessModel.set_extraction_claims):
                pass

        default_extraction_prompt = ConfigModel.get_extraction_prompt(user_id) or DEFAULT_CUSTOM_EXTRACTION_PROMPT

        with ui.textarea(
                label="Extraction prompt", validation=None, value=default_extraction_prompt
        ) as textarea, Store(textarea, lambda value: ConfigModel.set_extraction_prompt(user_id, value)):
            textarea.classes('w-full')
            if user_id is not None and not AccessModel.get_extraction_prompt():
                textarea.disable()

        if user_id is None:
            with ui.checkbox(
                text="User access", value=AccessModel.get_extraction_prompt()
            ) as checkbox, Store(checkbox, AccessModel.set_extraction_prompt):
                pass

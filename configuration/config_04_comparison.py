from nicegui import ui

from model.storages import ConfigModel, AccessModel
from model.storage_tools import Store


DEFAULT_CUSTOM_COMPARISON_PROMPT = (
            "Rate the keypoint based on the source by picking one of the following options:\n"
            "\n"
            "  \"🟩 Strong support\": source strongly supports keypoint\n"
            "  \"🟨 Some support\": source generally supports keypoint, with limitations or minor contradictions\n"
            "  \"⬜️ No mention\": source does not contain information about the keypoint, neither supports nor "
            "contradicts it, or is unclear\n"
            "  \"🟧​ Some contradiction\": source contradicts keypoint but not completely\n"
            "  \"🟥 Strong contradiction\": source is in strong opposition to keypoint\n"
            "\n"
            "IMPORTANT: Do not make assumptions or inferences. Do not assess the correctness of either keypoint or "
            "source, determine your rating only based on how well the keypoint holds up against the source "
            "information. No information about the keypoint means \"⬜️ No mention\"!\n"
        )


def get_section_crosschecker(user_id: str | None) -> None:
    llm_interfaces = ConfigModel.get_llm_interfaces(user_id)

    def _update_llms() -> None:
        nonlocal llm_interfaces
        llm_interfaces = ConfigModel.get_llm_interfaces(user_id)
        llm_select.options = [each_name for each_name in llm_interfaces]
        llm_select.update()

    with ui.element("div").classes("w-full flex justify-end"):
        default_llm = ConfigModel.get_comparison_llm(user_id)
        with ui.select(
            options=[each_name for each_name in llm_interfaces],
            value=None if default_llm is None else default_llm.name, label="LLM interface for comparison"
        ) as llm_select, Store(llm_select, lambda name: ConfigModel.set_comparison_llm(user_id, name)):
            llm_select.classes('w-full').on("click", _update_llms)
            if user_id is not None and not AccessModel.get_comparison_llm():
                llm_select.disable()
                ui.tooltip("User does not have access to change this setting.")

        if user_id is None:
            with ui.checkbox(
                text="User access", value=AccessModel.get_comparison_llm()
            ) as checkbox, Store(checkbox, AccessModel.set_comparison_llm):
                pass


        comparison_prompt = ConfigModel.get_comparison_prompt(user_id) or DEFAULT_CUSTOM_COMPARISON_PROMPT

        with ui.textarea(
                label="Comparison prompt", validation=None, value=comparison_prompt
        ) as textarea, Store(textarea, lambda value: ConfigModel.set_comparison_prompt(user_id, value)):
            textarea.classes('w-full')
            if user_id is not None and not AccessModel.get_comparison_prompt():
                textarea.disable()

        if user_id is None:
            with ui.checkbox(
                text="User access", value=AccessModel.get_comparison_prompt()
            ) as checkbox, Store(checkbox, AccessModel.set_comparison_prompt):
                pass


from nicegui import ui

from model.storages import ConfigModel, AccessModel
from model.storage_tools import Store


DEFAULT_CUSTOM_COMPARISON_PROMPT = (
            "The keypoint is a claim and the source reference is a news report. Now rate the claim based on the "
            "report by picking one of the following options:\n"
            "\n"
            "  \"🟩 Strong support\": report strongly supports claim\n"
            "  \"🟨 Some support\": report generally supports claim, with limitations or minor contradictions\n"
            "  \"⬜️ No mention\": report neither clearly supports nor contradicts claim, or is unclear\n"
            "  \"🟧​ Some contradiction\": report contradicts claim but not completely\n"
            "  \"🟥 Strong contradiction\": report is in strong opposition to claim\n"
            "\n"
            "IMPORTANT: Do not assess the correctness of either claim or report, determine your rating only based on "
            "how well the claim holds up against the news report.\n"
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


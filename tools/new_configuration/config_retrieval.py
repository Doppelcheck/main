from nicegui import ui

from tools.configuration.data.config_objects import ConfigModel


def get_section(config: ConfigModel, admin: bool = False) -> None:
    with ui.element("div").classes("w-full flex justify-end"):
        ui.select(
            label="Select LLM interface",
            options=["OpenAI", "Mistral", "Anthropic", "ollama", "llamafile"],
            value="OpenAI"
        ).classes('w-full')
        if admin:
            with ui.checkbox("User access") as checkbox:
                pass

        ui.select(
            label="Select data interface",
            options=["Google", "Bing", "DuckDuckGo", "gdelt", "twitter", "mbfc", "crossref",
                     "reuters connect", "local docs (vector db)", "sql"],
            value="Google"
        ).classes('w-full')
        if admin:
            with ui.checkbox("User access") as checkbox:
                pass

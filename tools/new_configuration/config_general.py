from nicegui import ui

from tools.configuration.data.config_objects import ConfigModel, store


def get_section(config: ConfigModel, admin: bool = False) -> None:
    with ui.element("div").classes("w-full flex justify-end"):
        ui.label('Settings').classes('text-h5')
        with store(
            ui.input, config.set_general_name, config.get_general_name,
            label="Name", placeholder="name for instance"
        ) as text_input:
            text_input.classes('w-full')
        if admin:
            with ui.checkbox("User access") as checkbox:
                pass

        with store(
            ui.select, config.set_general_language, config.get_general_language,
            label="Language", options=["default", "English", "German", "French", "Spanish"]
        ) as language_select:
            language_select.classes('w-full')
        if admin:
            with ui.checkbox("User access") as checkbox:
                pass

    with ui.element("div").classes("w-full flex justify-end"):
        ui.label('Information').classes('text-h5')
        ui.label("info stuff, user id, version, tokens used").classes('w-full')

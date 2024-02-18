from nicegui import ui

from tools.configuration.data.config_objects import ConfigModel, Store, AccessModel


def get_section(user_id: str, version: str, admin: bool = False) -> None:

    with ui.element("div").classes("w-full flex justify-end"):
        ui.label('Settings').classes('text-h5')
        with Store(
                ui.input,
                lambda name: ConfigModel.set_general_name(user_id, name),
                ConfigModel.get_general_name(user_id),
                label="Name", placeholder="name for instance"
        ) as text_input:
            text_input.classes('w-full')
            if not admin and not AccessModel.get_access_name():
                text_input.disable()
                ui.tooltip("User does not have access to change this setting.")

        if admin:
            with Store(
                    ui.checkbox, AccessModel.set_access_name,
                    AccessModel.get_access_name(), text="User access") as checkbox:
                pass

        with Store(
            ui.select,
            lambda language: ConfigModel.set_general_language(user_id, language),
            ConfigModel.get_general_language(user_id),
            label="Language", options=["default", "English", "German", "French", "Spanish"]
        ) as language_select:
            language_select.classes('w-full')
            if not admin and not AccessModel.get_access_language():
                language_select.disable()
                ui.tooltip("User does not have access to change this setting.")

        if admin:
            with Store(
                    ui.checkbox, AccessModel.set_access_language,
                    AccessModel.get_access_language(), text="User access") as checkbox:
                pass

    with ui.column() as column:
        column.classes("w-full grid justify-items-end")

        ui.label("Information").classes('text-h5')

        with ui.grid(columns=2).classes('justify-self-start'):
            ui.label('User ID:')
            ui.label(user_id).classes("text-italic")

            ui.label('Doppelcheck server version:')
            ui.label(version).classes("text-italic")

            ui.label('Tokens used:')
            ui.label("?").classes("text-italic")

            ui.label('other info stuff:')
            ui.label("other info stuff").classes("text-italic")

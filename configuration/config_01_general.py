from nicegui import ui

from configuration.config_install import get_section_install
from model.storages import ConfigModel, Store, AccessModel


def get_section_general(user_id: str, version: str, address: str, is_admin: bool = False) -> None:

    if not is_admin:
        get_section_install(user_id, address, version, title=False)

    with ui.element("div").classes("w-full flex justify-end"):
        ui.label('Settings').classes('text-h5')

        with ui.input(
                label="Name", placeholder="name for instance", value=ConfigModel.get_general_name(user_id, is_admin),
                validation={"Should not be empty": lambda v: len(v) >= 1}
        ) as new_text_input, Store(
            new_text_input, lambda value: ConfigModel.set_general_name(user_id, value)
        ):
            new_text_input.classes('w-full')
            if not is_admin and not AccessModel.get_access_name():
                new_text_input.disable()
                ui.tooltip("User does not have access to change the name.")
        if is_admin:
            with ui.checkbox(
                    text="User access", value=AccessModel.get_access_name()
            ) as checkbox, Store(checkbox, AccessModel.set_access_name) as checkbox:
                pass

        with ui.select(
                options=["default", "English", "German", "French", "Spanish"], label="Language",
                value=ConfigModel.get_general_language(user_id, is_admin)
        ) as language_select, Store(
            language_select, lambda language: ConfigModel.set_general_language(user_id, language)
        ):
            language_select.classes('w-full')
            if not is_admin and not AccessModel.get_access_language():
                language_select.disable()
                ui.tooltip("User does not have access to change the language.")
        if is_admin:
            with ui.checkbox(
                    text="User access", value=AccessModel.get_access_language()
            ) as checkbox, Store(checkbox, AccessModel.set_access_language) as checkbox:
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

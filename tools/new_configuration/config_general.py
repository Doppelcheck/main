from nicegui import ui

from tools.configuration.data.config_objects import ConfigModel, Store


def get_section(user_id: str, admin: bool = False) -> None:

    with ui.element("div").classes("w-full flex justify-end"):
        ui.label('Settings').classes('text-h5')
        with Store(
                ui.input,
                lambda name: ConfigModel.set_general_name(user_id, name),
                ConfigModel.get_general_name(user_id),
                label="Name", placeholder="name for instance"
        ) as text_input:
            text_input.classes('w-full')

        if admin:
            with Store(
                    ui.checkbox, lambda access: ConfigModel.set_user_access(user_id, "general_name", access),
                    ConfigModel.get_user_access(user_id, "general_name"), text="User access") as checkbox:
                pass

        with Store(
            ui.select,
            lambda language: ConfigModel.set_general_language(user_id, language),
            ConfigModel.get_general_language(user_id),
            label="Language", options=["default", "English", "German", "French", "Spanish"]
        ) as language_select:
            language_select.classes('w-full')

        if admin:
            with Store(
                    ui.checkbox, lambda access: ConfigModel.set_user_access(user_id, "general_language", access),
                    ConfigModel.get_user_access(user_id, "general_language"), text="User access") as checkbox:
                pass

    with ui.element("div").classes("w-full flex justify-end"):
        ui.label('Information').classes('text-h5')
        ui.label("info stuff, user id, version, tokens used").classes('w-full')

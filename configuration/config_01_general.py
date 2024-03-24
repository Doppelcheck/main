from nicegui import ui

from configuration.config_install import get_section_install
from model.storages import ConfigModel, AccessModel
from model.storage_tools import Store


def get_section_general(user_id: str | None, version: str, address: str) -> None:
    data_interfaces = ConfigModel.get_data_interfaces(user_id)

    def _update_data() -> None:
        nonlocal data_interfaces
        data_interfaces = ConfigModel.get_data_interfaces(user_id)
        data_select.options = [each_name for each_name in data_interfaces]
        data_select.update()

    if user_id is not None:
        get_section_install(user_id, address, version, title=False)

    with ui.element("div").classes("w-full flex justify-end"):
        ui.label('Settings').classes('text-h5')

        with ui.input(
                label="Name", placeholder="name for instance", value=ConfigModel.get_general_name(user_id),
                validation={"Should not be empty": lambda v: len(v) >= 1}
        ) as new_text_input, Store(
            new_text_input, lambda value: ConfigModel.set_general_name(user_id, value)
        ):
            new_text_input.classes('w-full')
            if user_id is not None and not AccessModel.get_access_name():
                new_text_input.disable()
                ui.tooltip("User does not have access to change the name.")
        if user_id is None:
            with ui.checkbox(
                    text="User access", value=AccessModel.get_access_name()
            ) as checkbox, Store(checkbox, AccessModel.set_access_name) as checkbox:
                pass

        with ui.select(
                options=["default", "English", "German", "French", "Spanish"], label="Language",
                value=ConfigModel.get_general_language(user_id)
        ) as language_select, Store(
            language_select, lambda language: ConfigModel.set_general_language(user_id, language)
        ):
            language_select.classes('w-full')
            if user_id is not None and not AccessModel.get_access_language():
                language_select.disable()
                ui.tooltip("User does not have access to change the language.")
        if user_id is None:
            with ui.checkbox(
                    text="User access", value=AccessModel.get_access_language()
            ) as checkbox, Store(checkbox, AccessModel.set_access_language) as checkbox:
                pass

    def toggle_chips() -> None:
        if len(data_select.value) < 2:
            data_select.props(remove='use-chips')
        else:
            data_select.props(add='use-chips')

    default_data = ConfigModel.get_selected_data_interfaces(user_id)
    with ui.select(
        options=[each_name for each_name in data_interfaces],
        label="Data interfaces", value=[each_data.name for each_data in default_data], multiple=True,
        on_change=toggle_chips
    ) as data_select, Store(data_select, lambda names: ConfigModel.set_selected_data_interfaces(user_id, names)):
        data_select.classes('w-full').on("click", _update_data)
        if (user_id is not None) and not AccessModel.get_select_data():
            data_select.disable()
            ui.tooltip("User does not have access to change this setting.")

    toggle_chips()
    if user_id is None:
        with ui.checkbox(
                text="User access", value=AccessModel.get_select_data()
        ) as checkbox, Store(checkbox, AccessModel.set_select_data):
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

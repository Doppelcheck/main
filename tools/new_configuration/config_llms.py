import dataclasses

from nicegui import ui

from tools.configuration.data.config_objects import ConfigModel, ProviderLLM, ParametersOpenAi, InterfaceOpenAi


def get_section(config: ConfigModel, admin: bool = False) -> None:
    async def _add_new_interface() -> None:
        api_key = api_key_input.value
        name = name_input.value
        editor_content = await editor.run_editor_method("get")
        parameters = ParametersOpenAi(**editor_content['json'])
        new_interface = InterfaceOpenAi(name=name, api_key=api_key, parameters=parameters)
        config.add_llm_interface(new_interface)
        interfaces.add_rows({'name': name, 'type': 'OpenAI'})
        name_input.validate()
        add_button.disable()

    def _remove_llm_interface() -> None:
        for each_row in interfaces.selected:
            _each_name = each_row['name']
            config.remove_llm_interface(_each_name)
            interfaces.remove_rows(each_row)

    def _activate_add_button() -> None:
        name_fine = all(each_validation(name_input.value) for each_validation in name_input.validation.values())
        key_fine = all(each_validation(api_key_input.value) for each_validation in api_key_input.validation.values())

        if name_fine and key_fine:
            add_button.enable()
        else:
            add_button.disable()

    with ui.element("div").classes("w-full flex justify-end"):
        ui.label('Existing interfaces').classes('text-h5 p-4')
        columns = [
            {'name': 'name', 'label': 'Name', 'field': 'name'},
            {'name': 'type', 'label': 'Type', 'field': 'type'},
        ]

        rows: list[dict[str, any]] = [
            {'name': each_interface.name, 'type': each_interface.provider}
            for each_interface in config.get_llm_interfaces()
        ]
        interfaces = ui.table(columns, rows, row_key="name", selection="single").classes('w-full')
        ui.button("Remove", on_click=_remove_llm_interface).classes("m-4")
        if admin:
            with ui.checkbox("User access") as checkbox:
                pass

    ui.element("div").classes('h-8')
    with ui.element("div").classes("w-full flex justify-end"):
        ui.label('New interface').classes('text-h5 p-4')
        with ui.tabs().classes('w-full') as llm_tabs:
            tabs = {each.value: ui.tab(each.value) for each in ProviderLLM}
            for each_name, each_tab in tabs.items():
                if each_name != 'OpenAI':
                    each_tab.disable()

        tab_openai = tabs['OpenAI']
        with ui.tab_panels(llm_tabs, value=tab_openai).classes('w-full'):
            with ui.tab_panel(tab_openai):
                with ui.input(
                    label="Name", placeholder="name for interface",
                    validation={"Name already in use": lambda x: x not in [x["name"] for x in interfaces.rows]},
                    on_change=_activate_add_button
                ) as name_input:
                    name_input.classes('w-full')

                with ui.input(
                    label="OpenAI API Key", placeholder="\"sk-\" + 48 alphanumeric characters",
                    password=True, validation={
                            "Must start with \"sk-\"": lambda v: v.startswith("sk-"),
                            "Must be 51 characters long": lambda v: len(v) == 51
                        },
                    on_change=_activate_add_button

                ) as api_key_input:
                    api_key_input.classes('w-full')

                default_parameters = ParametersOpenAi()
                with ui.json_editor({"content": {"json": dataclasses.asdict(default_parameters)}}) as editor:
                    editor.classes('w-full')

        add_button = ui.button("Add", on_click=_add_new_interface).classes("m-4")
        add_button.disable()
        if admin:
            with ui.checkbox("User access") as checkbox:
                pass

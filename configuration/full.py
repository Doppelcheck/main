from nicegui import ui

from configuration.config_01_general import get_section_general
from configuration.config_02_extraction import get_section_keypoint
from configuration.config_03_retrieval import get_section_sourcefinder
from configuration.config_04_comparison import get_section_crosschecker
from configuration.config_05_llms import get_section_language_models
from configuration.config_06_data import get_section_data_sources
from plugins.abstract import InterfaceLLM, InterfaceData
from plugins.parse_plugins import load_plugins, get_interfaces


async def full_configuration(user_id: str, address: str, version: str, is_admin: bool) -> None:
    plugin_directory = 'plugins/implementation'  # Update with the actual path
    loaded_plugins = load_plugins(plugin_directory)

    llm_subclasses = get_interfaces(loaded_plugins, InterfaceLLM)
    data_subclasses = get_interfaces(loaded_plugins, InterfaceData)

    with ui.header() as container:
        container.classes(add="min-h-fit bg-black")
        ui.label("Doppelcheck configuration").classes("w-full text-h2 text-white text-right p-4")

    with ui.element("div") as container:
        container.classes(add="w-full max-w-7xl ")

        with ui.splitter(value=20, limits=(20, 20)).classes('h-full ') as splitter:
            with splitter.before:
                with ui.tabs().props('vertical').classes("text-wrap") as tabs:
                    tab_settings = ui.tab('General', icon='settings')
                    tab_extract = ui.tab('Keypoint Assistant', icon='group_work')
                    tab_retrieve = ui.tab('Sourcefinder Assistant', icon='search')
                    tab_compare = ui.tab('Crosschecker Assistant', icon='scale')
                    tab_llms = ui.tab('Language Models', icon='psychology')
                    tab_data = ui.tab('Data Sources', icon='description')

            with splitter.after:
                with ui.tab_panels(tabs, value=tab_settings).props('vertical').classes('w-full'):
                    with ui.tab_panel(tab_settings):
                        ui.label('General').classes('text-h4')
                        get_section_general(user_id, version, address, is_admin=is_admin)

                    with ui.tab_panel(tab_extract):
                        ui.label('Keypoint Assistant').classes('text-h4')
                        get_section_keypoint(user_id, is_admin=is_admin)

                    with ui.tab_panel(tab_retrieve):
                        ui.label('Sourcefinder Assistant').classes('text-h4')
                        get_section_sourcefinder(user_id, is_admin=is_admin)

                    with ui.tab_panel(tab_compare):
                        ui.label('Crosschecker Assistant').classes('text-h4')
                        get_section_crosschecker(user_id, is_admin=is_admin)

                    with ui.tab_panel(tab_llms):
                        ui.label('Language Models').classes('text-h4')
                        get_section_language_models(user_id, llm_subclasses, is_admin=is_admin)

                    with ui.tab_panel(tab_data):
                        ui.label('Data Sources').classes('text-h4')
                        get_section_data_sources(user_id, data_subclasses, is_admin=is_admin)

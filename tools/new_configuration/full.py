from nicegui import ui

from tools.new_configuration.config_01_general import get_section as get_section_general
from tools.new_configuration.config_02_extraction import get_section as get_section_extraction
from tools.new_configuration.config_03_retrieval import get_section as get_section_retrieval
from tools.new_configuration.config_04_comparison import get_section as get_section_comparison
from tools.new_configuration.config_05_llms import get_section as get_section_llms
from tools.new_configuration.config_06_data import get_section as get_section_data
from tools.plugins.abstract import InterfaceLLM, InterfaceData
from tools.plugins.parse_plugins import load_plugins, get_interfaces


async def full_configuration(user_id: str, address: str, version: str) -> None:
    is_admin = user_id == "ADMIN"

    plugin_directory = 'tools/plugins/implementation'  # Update with the actual path
    loaded_plugins = load_plugins(plugin_directory)

    llm_subclasses = get_interfaces(loaded_plugins, InterfaceLLM)
    data_subclasses = get_interfaces(loaded_plugins, InterfaceData)

    with ui.element("div") as container:
        container.classes(add="w-full max-w-5xl m-auto")

        with ui.splitter(value=30, limits=(30, 30)).classes('w-full h-56 h-full ') as splitter:
            with splitter.before:
                with ui.tabs().props('vertical').classes('w-full') as tabs:
                    tab_settings = ui.tab('General', icon='settings')
                    tab_extract = ui.tab('Extraction', icon='group_work')
                    tab_retrieve = ui.tab('Retrieval', icon='search')
                    tab_compare = ui.tab('Comparison', icon='scale')
                    tab_llms = ui.tab('LLM Interfaces', icon='psychology')
                    tab_data = ui.tab('Data Interfaces', icon='description')

            with splitter.after:
                with ui.tab_panels(tabs, value=tab_settings).props('vertical').classes('w-full'):
                    with ui.tab_panel(tab_settings):
                        ui.label('General').classes('text-h4')
                        get_section_general(user_id, version, address, admin=is_admin)

                    with ui.tab_panel(tab_extract):
                        ui.label('Keypoint Assistant').classes('text-h4')
                        get_section_extraction(user_id, admin=is_admin)

                    with ui.tab_panel(tab_retrieve):
                        ui.label('Sourcefinder Assistant').classes('text-h4')
                        get_section_retrieval(user_id, admin=is_admin)

                    with ui.tab_panel(tab_compare):
                        ui.label('Crosschecker Assistant').classes('text-h4')
                        get_section_comparison(user_id, admin=is_admin)

                    with ui.tab_panel(tab_llms):
                        ui.label('LLM interfaces').classes('text-h4')
                        get_section_llms(user_id, llm_subclasses, admin=is_admin)

                    with ui.tab_panel(tab_data):
                        ui.label('Data Interfaces').classes('text-h4')
                        get_section_data(user_id, data_subclasses, admin=is_admin)

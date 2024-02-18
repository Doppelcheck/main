from nicegui import ui

from tools.new_configuration.config_comparison import get_section as get_section_comparison
from tools.new_configuration.config_extraction import get_section as get_section_extraction
from tools.new_configuration.config_general import get_section as get_section_general
from tools.new_configuration.config_install import get_section as get_section_install
from tools.new_configuration.config_llms import get_section as get_section_llms
from tools.new_configuration.config_data import get_section as get_section_data
from tools.new_configuration.config_retrieval import get_section as get_section_retrieval


async def full_configuration(user_id: str, address: str, version: str) -> None:
    is_admin = user_id == "ADMIN"

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
                    tab_install = ui.tab('Installation', icon='cloud_download')

            with splitter.after:
                with ui.tab_panels(tabs, value=tab_settings).props('vertical').classes('w-full'):
                    with ui.tab_panel(tab_settings):
                        ui.label('General').classes('text-h4')
                        get_section_general(user_id, version, admin=is_admin)

                    with ui.tab_panel(tab_extract):
                        ui.label('Extraction').classes('text-h4')
                        get_section_extraction(user_id, admin=is_admin)

                    with ui.tab_panel(tab_retrieve):
                        ui.label('Retrieval').classes('text-h4')
                        get_section_retrieval(user_id, admin=is_admin)

                    with ui.tab_panel(tab_compare):
                        ui.label('Comparison').classes('text-h4')
                        get_section_comparison(user_id, admin=is_admin)

                    with ui.tab_panel(tab_llms):
                        ui.label('LLM interfaces').classes('text-h4')
                        get_section_llms(user_id, admin=is_admin)

                    with ui.tab_panel(tab_data):
                        ui.label('Data Interfaces').classes('text-h4')
                        get_section_data(user_id, admin=is_admin)

                    with ui.tab_panel(tab_install):
                        ui.label('Installation').classes('text-h4')
                        get_section_install(user_id, address, version, title=False, admin=is_admin)



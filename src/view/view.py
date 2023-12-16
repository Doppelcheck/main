# coding=utf-8
from loguru import logger
from lxml import etree, html
from nicegui import ui, Client, app

from bs4 import BeautifulSoup, NavigableString

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import validators

from experiments.navi_str import XpathSlice
from experiments.text_extraction import readability_lxml_extract, readability_lxml_extract_from_html
from src.dataobjects import ViewCallbacks, Source
from src.view.landing_page import LandingPage
from src.view.processing_page import ProcessingPage
from src.view.test_page import TestPage

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


class View:
    def __init__(self, bookmarklet_template: str) -> None:
        self.callbacks: ViewCallbacks | None = None
        app.add_static_files(url_path="/assets", local_directory="assets")

        self.bookmarklet_template = bookmarklet_template
        self.source = None

    def set_callbacks(self, callback: ViewCallbacks) -> None:
        self.callbacks = callback

    def _get_target_url(self) -> str:
        return "process"

    def _callback_manual_process(self, text: str) -> None:
        if validators.url(text):
            source = Source(url=text)
        else:
            source = Source(url="[unknown]", text=text)

        self.source = source
        target_url = self._get_target_url()
        ui.open(target_url)

    def _highlight_slice(self, html_text: str, xslice: XpathSlice) -> str:
        tree = html.fromstring(html_text)
        for each_xpath, each_text in zip(xslice.xpaths, xslice.texts):
            nodes = tree.xpath(each_xpath)
            for each_node in nodes:
                # text_position = each_node.text.index(each_text)
                span_tag = etree.Element("span", **{"class": "doppelchecked"})
                span_tag.text = each_text
                node_text: str | None = each_node.text

                try:
                    if node_text == each_text:
                        each_node.text = None
                        each_node.append(span_tag)
                        continue

                    if node_text.startswith(each_text):
                        each_node.insert(0, span_tag)
                        each_node.tail = node_text[len(each_text):]
                        continue

                    if node_text.endswith(each_text):
                        each_node.text = node_text[:-len(each_text)]
                        each_node.append(span_tag)
                        continue

                    if each_text in node_text:
                        index = node_text.index(each_text)
                        each_node.text = node_text[:index]
                        each_node.append(span_tag)
                        each_node.tail = node_text[index + len(each_text):]
                        continue

                except ValueError:
                    continue

        return html.tostring(tree).decode("utf-8")

    def _highlight_text_section(self, soup: BeautifulSoup, marked_text: str) -> BeautifulSoup:
        for text_node in soup.find_all(text=True):
            if marked_text in text_node:
                new_content = list()
                parts = text_node.split(marked_text)

                for i, part in enumerate(parts):
                    new_content.append(NavigableString(part))
                    if i < len(parts) - 1:  # Don't add span after the last part
                        span_tag = soup.new_tag("span", **{"class": "doppelchecked"})
                        span_tag.string = marked_text
                        new_content.append(span_tag)

                # Replace the text node with the new content
                current = text_node
                for content in new_content:
                    current.insert_after(content)
                    current = content

                text_node.extract()

        return soup

    def setup_routes(self) -> None:
        @app.post("/pass_source/")
        async def pass_source(source: Source) -> Response:
            self.source = source
            target_url = self._get_target_url()
            return JSONResponse(content={"redirect_to": target_url})

        @app.post("/update_body/")
        async def pass_source(source: Source) -> Response:
            html_text = source.html
            soup = BeautifulSoup(html_text, "html.parser")

            # process
            extractor_agent = self.callbacks.get_extractor_agent()

            if source.selected_text is None:
                # take website
                main_content = html_text
                # main_content = readability_lxml_extract_from_html(body)
                sourced_statements = await extractor_agent.extract_statements_from_html(main_content)

                for each_indices, each_statement in sourced_statements:
                    logger.info(f"Statement: {each_statement}")
                    logger.info(f"Source: {each_indices}")
                    for each_index in each_indices:
                        html_text = self._highlight_slice(html_text, each_index)

                soup = BeautifulSoup(html_text, "html.parser")
                statements = [each_statement for _, each_statement in sourced_statements]

            else:
                # take selection (get html of selection?)
                text = source.selected_text
                sourced_statements = await extractor_agent.extract_statements_from_text(text)

                for each_statement, each_source in sourced_statements:
                    logger.info(f"Statement: {each_statement}")
                    logger.info(f"Source: {each_source}")
                    soup = self._highlight_text_section(soup, each_source)

                statements = [each_statement for each_statement, _ in sourced_statements]

            # add sidebar
            elements_statements = "\n".join(
                f'<li style="margin-bottom: 1em;">{each_statement}</li>'
                for each_statement in statements
            )
            sidebar_html = f"""
<div class="doppelcheck-sidebar" style="width: 200px; height: 100%; position: fixed; top: 0; right: 0; color: black; background: #f0f0f0; padding: 10px; z-index: 10000;">
    <div class="doppelcheck-sidebar-content">
        <h1>Side bar</h1>
        <ul>
            {elements_statements}
        </ul>
    </div>
</div>
            """

            sidebar = BeautifulSoup(sidebar_html, "html.parser")
            soup.body.insert(0, sidebar)

            # body_html = body_soup.prettify()
            body_html = str(soup.body)
            return JSONResponse(content={"body": body_html})

        @ui.page("/")
        async def index_page(client: Client) -> None:
            landing_page = LandingPage(client, self.callbacks)
            await landing_page.create_content()

        @ui.page("/_test")
        async def test_page(client: Client) -> None:
            testing_page = TestPage(client, self.callbacks)
            testing_page.bookmarklet_template = self.bookmarklet_template
            testing_page.manual_process = self._callback_manual_process
            await testing_page.create_content()

        @ui.page("/process")
        async def test_page(client: Client) -> None:
            processing_page = ProcessingPage(client, self.callbacks)
            processing_page.source = self.source
            await processing_page.create_content()

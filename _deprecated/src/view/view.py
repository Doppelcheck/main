# coding=utf-8
import asyncio
from urllib.parse import urlparse

from loguru import logger
from lxml import html
from nicegui import ui, Client, app

from bs4 import BeautifulSoup, NavigableString

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi import WebSocket
import validators

from _deprecated.src.agents.extraction import Extract
from _deprecated.src.dataobjects import ViewCallbacks, Source
from _deprecated.src.view.landing_page import LandingPage
from _deprecated.src.view.processing_page import ProcessingPage
from _deprecated.src.view.test_page import TestPage
from _experiments.navi_str import XpathSlice, index_html_new

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
        self.domain = "https://localhost:8000/"

    async def get_domain(self) -> None:
        js_url = await ui.run_javascript('window.location.href')
        parsed_url = urlparse(js_url)
        self.domain = f"{parsed_url.scheme}://{parsed_url.netloc}/"

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

    def _mark_slice(self, html_text: str, xslice: XpathSlice) -> str:
        tree = html.fromstring(html_text)
        for index_element, (each_xpath, each_text) in enumerate(zip(xslice.xpaths, xslice.texts)):
            nodes = tree.xpath(each_xpath)
            if len(nodes) >= 2:
                logger.warning(f"Xpath: {each_xpath} has more than one node.")

            each_node = nodes[0]
            if each_node.text is not None and each_text in each_node.text:
                each_node.text = each_node.text.replace(each_text, f"[xslice_{xslice.order}_{index_element}]")

            elif each_node.tail is not None and each_text in each_node.tail:
                each_node.tail = each_node.tail.replace(each_text, f"[xslice_{xslice.order}_{index_element}]")

            else:
                logger.warning(f"Node text is None: {each_xpath}")
                continue

        html_template = html.tostring(tree).decode("utf-8")
        return html_template

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

    def mark_extract_sources(self, extracts: list[Extract], html_template: str) -> str:
        for source_slices, each_statement in extracts:
            for each_slice in source_slices:
                html_template = self._mark_slice(html_template, each_slice)

        return html_template

    def insert_highlights(self, slices_per_extract: tuple[list[XpathSlice]], html_template: str) -> str:
        for index_extract, each_extract_slices in enumerate(slices_per_extract):
            for index_slice, each_slice in enumerate(each_extract_slices):
                for index_element, (each_xpath, each_text) in enumerate(zip(each_slice.xpaths, each_slice.texts)):
                    find_text = f"[xslice_{each_slice.order}_{index_element}]"
                    if index_slice < 1:
                        replace_text = f"""
                            <span id=\"doppelcheckextract{index_extract + 1:02d}\" class=\"doppelchecked claim{index_extract + 1:02d}\">
                                {each_text}
                            </span>
                            """

                    else:
                        replace_text = f"""
                            <span class=\"doppelchecked claim{index_extract + 1:02d}\">
                                {each_text}
                            </span>
                            """

                    html_template = html_template.replace(find_text, replace_text)

        return html_template

    def render_sidebar(self, soup: BeautifulSoup, claims: list[str]) -> str:
        # add sidebar

        # assets/images/android-chrome-512x512.png
        server_addresses = list(app.urls)  # todo: get [].href from javascript and add to anchor link, also for assets
        processing_src = f"{self.domain}assets/images/processing_small.gif"

        style_tag = soup.new_tag("style", **{"type": "text/css"})
        with open("assets/css/styles.css") as f:
            style_tag.string = f.read()
            # style in body, ugly but works
        soup.body.insert(0, style_tag)

        claim_element_list = tuple(
            f"""
            <li>
                <a href="#doppelcheckextract{i + 1:02d}">
                    <span class="extracted claim{i + 1:02d}" id="extractedClaim{i + 1:02d}">
                        {each_claim}
                    </span>
                </a>
                                            
                <button class="doppelcheck-button" id="loadButton{i + 1:02d}" 
                onclick="startStreaming('{i + 1:02d}')">🧐 Doppelcheck</button>
                
                <div class="doppelcheck-review">
                    <ul id="dataArea{i + 1:02d}">
                    </ul>
                    
                    <div id="processingIndicator{i + 1:02d}" style="display:none;">
                        <img src="{processing_src}" alt="Processing..." class="doppelcheck-processing" />
                    </div>
                </div>
                
            </li>
            """
            for i, each_claim in enumerate(claims)
        )

        claim_elements = "\n".join(claim_element_list)
        sidebar_html = f"""
        <div class="doppelcheck-sidebar">
            <div class="doppelcheck-sidebar-content">
                <h1>Doppelcheck Kernaussagen</h1>
                <div>
                    <ul>
                        {claim_elements}
                    </ul>
                <div>
            </div>
        </div>
        """

        # todo: sidebar not absolute but previous content and sidebar in columns
        sidebar = BeautifulSoup(sidebar_html, "html.parser")
        soup.body.insert(0, sidebar)

        # body_html = body_soup.prettify()
        body_html = str(soup.body)
        return body_html

    def setup_routes(self) -> None:
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            retrieval_agent = self.callbacks.get_retrieval_agent()
            #comparison_agent = self.callbacks.get_comparison_agent()

            claim = await websocket.receive_text()
            logger.info(f"Claim: {claim}")

            async for each_document in retrieval_agent.retrieve_documents(claim):
                logger.info(f"each_source: {each_document.source}")
                await websocket.send_text(each_document.source)

            await websocket.close()

        @app.post("/pass_source/")
        async def pass_source(source: Source) -> Response:
            self.source = source
            target_url = self._get_target_url()
            return JSONResponse(content={"redirect_to": target_url})

        @app.post("/update_body/")
        async def pass_source(source: Source) -> Response:
            html_template = source.html

            # process
            extractor_agent = self.callbacks.get_extractor_agent()

            if source.selected_text is None:
                # take website
                main_content = html_template
                # main_content = readability_lxml_extract_from_html(body)

                # todo:
                #  improve xslices
                #   do not include text segments but text ranges
                #   remove order from xslice
                #   by considering only text.strip()?
                #  text node segmentation introduces new .text and .tail nodes which are not highlighted

                xslices = list(index_html_new(main_content))
                extracts = await extractor_agent.extract_from_slices(xslices)
                logger.info(f"Extracts: {extracts}")
                html_template = self.mark_extract_sources(extracts, html_template)

                slices_referenced = tuple(sorted(source_slices, key=lambda x: x.order) for source_slices, _ in extracts)

                # replace tags with highlights original text
                html_text = self.insert_highlights(slices_referenced, html_template)

                soup = BeautifulSoup(html_text, "html.parser")
                claims = [each_statement for _, each_statement in extracts]

            else:
                # take selection (get html of selection?)
                # parse Article from source url
                soup = BeautifulSoup(html_template, "html.parser")

                text = source.selected_text
                extracts = await extractor_agent.extract_statements_from_text(text)

                for each_statement, each_source in extracts:
                    logger.info(f"Statement: {each_statement}")
                    logger.info(f"Source: {each_source}")
                    soup = self._highlight_text_section(soup, each_source)

                claims = [each_statement for each_statement, _ in extracts]

            body_html = self.render_sidebar(soup, claims)
            return JSONResponse(content={"body": body_html})

        @ui.page("/")
        async def index_page(client: Client) -> None:
            landing_page = LandingPage(client, self.callbacks)
            await landing_page.create_content()

        @ui.page("/_test")
        async def test_page(client: Client) -> None:
            await client.connected()
            await self.get_domain()
            testing_page = TestPage(client, self.domain, self.callbacks)
            testing_page.bookmarklet_template = self.bookmarklet_template
            testing_page.manual_process = self._callback_manual_process
            await testing_page.create_content()

        @ui.page("/process")
        async def test_page(client: Client) -> None:
            processing_page = ProcessingPage(client, self.callbacks)
            processing_page.source = self.source
            await processing_page.create_content()

# coding=utf-8
import dataclasses
from typing import Generator

import httpx

from lxml import etree

import asyncio
from playwright.async_api import async_playwright

from experiments.navi_str import get_text_xpaths
from src.tools.misc import generate_block, extract_code_block
from src.tools.prompt_openai import PromptOpenAI


class ReceiveGoogleResultsException(Exception):
    pass


class RetrieveDocumentException(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class Document:
    source: str
    content: str


class AgentRetrieval:
    def __init__(self, retrieval_config: dict[str, any], google_config: dict[str, any], openai_config: dict[str, any]) -> None:
        # todo: switch to httpx sessions?
        self._max_text_length = retrieval_config["max_text_length"]

        self._google_api_key = google_config["custom_search_api_key"]
        self._search_engine_id = google_config["custom_search_engine_id"]
        _target_language = retrieval_config.get("target_language", "")

        self.agent_extraction = PromptOpenAI(openai_config)
        self._context_instruction = (
            " Refine your query according to the provided context."
        )
        if len(_target_language) < 1:
            _language_instruction = " Answer in the language of the claim."
        else:
            _language_instruction = f" Answer in {_target_language}."

        self.prompt = (
            f"```claim\n"
            f"{{claim}}\n"
            f"```\n"
            f"\n"
            f"{{context_block}}"
            f"Generate the optimal Google search query to get results that allow for the verification of the claim "
            f"above. Use the language of the claim. Make use of any special Google search operators you deem necessary "
            f"to improve result precision and recall."
            f"{{context_instruction}}{_language_instruction}\n"
            f"\n"
            f"Respond exactly and only with the one search query requested."
        )

    async def _make_query(self, claim: str, context: str | None = None) -> str:
        if context is None:
            context_block = ""
            context_instruction = ""
        else:
            context = await self.agent_extraction.summarize(context, max_len_summary=5_000)
            context_block = generate_block(context, "context")
            context_instruction = self._context_instruction

        claim = await self.agent_extraction.summarize(claim, max_len_summary=1_000)

        prompt = self.prompt.format(
            claim=claim.strip(),
            context_block=context_block,
            context_instruction=context_instruction,
        )

        response = await self.agent_extraction.reply_to_prompt(prompt)
        return response.strip()

    def _get_urls_from_google_query(self, search_query: str) -> list[str]:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "q": search_query,
            "key": self._google_api_key,
            "cx": self._search_engine_id,
        }
        response = httpx.get(url, params=params)

        if response.status_code != 200:
            raise ReceiveGoogleResultsException(
                f"Request failed with status code {response.status_code}: {response.text}"
            )

        result = response.json()

        items = result.get("items")
        if items is None or len(items) < 1:
            return list()

        return [each_item['link'] for each_item in items]

    def _get_text(self, html_content: str) -> str:
        parser = etree.HTMLParser()
        tree = etree.fromstring(html_content, parser=parser)

        text_node_contents = list[str]()

        for node_text, xpath in get_text_xpaths(tree):
            text_node_contents.append(node_text.strip())

        return " ".join(text_node_contents)

    async def get_html_code(self, context, url: str) -> Document:
        page = await context.new_page()
        await page.goto(url)
        html = await page.content()
        relevant_content = self._get_text(html)
        await page.close()
        return Document(source=url, content=relevant_content)

    async def _open_new_pages(self, context, urls: list[str]) -> Generator[Document, None, None]:
        tasks = [asyncio.create_task(self.get_html_code(context, each_url)) for each_url in urls]
        for task in asyncio.as_completed(tasks):
            yield await task

    async def retrieve_documents(self, claim: str, information_context: str | None = None) -> Generator[Document, None, None]:
        query = await self._make_query(claim, context=information_context)

        urls = self._get_urls_from_google_query(query)
        async with async_playwright() as driver:
            browser = await driver.firefox.launch(headless=False)
            context = await browser.new_context()
            async for document in self._open_new_pages(context, urls):
                yield document

            await asyncio.sleep(1)
            await context.close()
            await browser.close()

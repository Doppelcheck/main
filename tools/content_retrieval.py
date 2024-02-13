import asyncio
from dataclasses import dataclass
from typing import Callable

import bs4

import newspaper
from loguru import logger
from playwright import async_api
from playwright._impl._errors import Error as PlaywrightError

header = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/W.X.Y.Z Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
}


async def parse_url(input_html: str, url: str, detect_language: Callable[[str], str]) -> newspaper.Article:
    article = newspaper.Article(url, fetch_images=False)
    article.download(input_html=input_html)

    article.parse()
    language = detect_language(article.text)
    article.config.set_language(language)
    article.nlp()

    """
    ui.label("Title:")
    ui.label(article.title)

    ui.label("Text:")
    ui.label(article.text)

    ui.label("Authors:")
    ui.label(", ".join(article.authors))

    ui.label("Language:")
    ui.label(article.meta_lang)
    ui.label(article.config.get_language())

    ui.label("Publish date:")
    ui.label(article.publish_date)

    ui.label("Tags:")
    ui.label(", ".join(article.tags))

    ui.label("Keywords:")
    ui.label(", ".join(article.keywords))

    ui.label("Meta keywords:")
    ui.label(", ".join(article.meta_keywords))

    ui.label("Summary:")
    ui.label(article.summary)
    """

    return article


def remove_images(html: str) -> str:
    soup = bs4.BeautifulSoup(html, 'html.parser')
    for each_element in soup.find_all('img'):
        each_element.decompose()

    for each_element in soup.find_all('svg'):
        each_element.decompose()

    return str(soup)


async def get_context(input_html: str, original_url: str, detect_language: Callable[[str], str]) -> str | None:
    article = await parse_url(input_html, original_url, detect_language)
    context = f"{article.title.upper()}\n\n{article.summary}"
    if len(context.strip()) < 20:
        return None
    if article.publish_date is not None:
        context += f"\n\npublished on {article.publish_date}"
    return context


@dataclass(frozen=True)
class Source:
    url: str
    content: str | None
    error: str | None


class PlaywrightBrowser:
    def __init__(self) -> None:
        self.active_tasks = 0
        self.all_tasks_done = asyncio.Event()

        self.playwright: async_api.PlaywrightContextManager | None = None
        self.browser: async_api.Browser | None = None
        self.context: async_api.BrowserContext | None = None

        self.callbacks = dict()

    async def init_browser(self) -> None:
        if self.playwright is None:
            self.playwright = await async_api.async_playwright().start()

        if self.browser is None:
            self.browser = await self.playwright.firefox.launch(headless=True)

        if self.context is None:
            self.context = await self.browser.new_context(ignore_https_errors=True)

    async def get_html_content_from_playwright(self, document_uri: str) -> Source:
        await self.init_browser()

        event_loop = asyncio.get_event_loop()

        start_time = event_loop.time()

        self.active_tasks += 1
        self.all_tasks_done.clear()

        page = await self.context.new_page()
        try:
            await page.goto(document_uri)
            await page.wait_for_load_state("domcontentloaded")
            # await page.wait_for_load_state("networkidle")
            content = await page.content()
            return Source(url=document_uri, content=content, error=None)

        except PlaywrightError as e:
            print(f"Failed to load page: {e}")
            return Source(url=document_uri, content=None, error=str(e))

        finally:
            await page.close()
            self.active_tasks -= 1
            if 0 >= self.active_tasks:
                self.all_tasks_done.set()

            end_time = event_loop.time()

            logger.info(f"Time taken to fetch content from {document_uri}: {end_time - start_time:.2f} seconds")

    async def close_browser(self):
        await asyncio.sleep(1)
        await self.all_tasks_done.wait()
        if self.context:
            await self.context.close()
            print("Context closed")

        if self.browser:
            await self.browser.close()

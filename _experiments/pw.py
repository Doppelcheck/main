import asyncio
import random
import time
from dataclasses import dataclass

from loguru import logger
from playwright import async_api
from playwright._impl._errors import Error as PlaywrightError


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


async def fetch_url_content(url: str, pb: PlaywrightBrowser) -> None:
    content = await pb.get_html_content_from_playwright(url)
    print(f"Content from {content.url}")


async def main():
    url_list_a = [
        "https://www.google.com",
        "https://www.bing.com",
        "https://www.yahoo.com",
        "https://www.duckduckgo.com",
        "https://www.ecosia.com"
    ]

    url_list_b = [
        "https://www.wikipedia.org",
        "https://www.bbc.co.uk",
        "https://www.cnn.com",
        "https://www.aljazeera.com",
        "https://www.rt.com"
    ]

    pb = PlaywrightBrowser()
    await pb.init_browser()

    start_time = time.time()
    tasks = (fetch_url_content(url, pb) for url in url_list_a)
    await asyncio.gather(*tasks)
    end_time = time.time()
    print(f"Time taken to fetch content from url_list_a: {end_time - start_time:.2f} seconds")

    # await asyncio.sleep(10)

    start_time = time.time()
    tasks = (fetch_url_content(url, pb) for url in url_list_b)
    await asyncio.gather(*tasks)
    end_time = time.time()

    await pb.close_browser()


async def process(pid: int) -> str:
    delay = random.randint(1, 5)
    await asyncio.sleep(delay)
    return f"Process {pid} has completed after {delay} seconds"


async def _main():
    print(await process(0))
    print(await process(1))
    print(await process(2))
    print(await process(3))


if __name__ == "__main__":
    asyncio.run(main())

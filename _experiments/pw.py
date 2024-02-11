import asyncio
from typing import Callable

from playwright import async_api
from playwright._impl._errors import Error as PlaywrightError


class PlaywrightBrowser:
    def __init__(self, callback: Callable[[str, str | None], None]) -> None:
        self.active_tasks = 0
        self.all_tasks_done = asyncio.Event()

        self.playwright: async_api.PlaywrightContextManager | None = None
        self.browser: async_api.Browser | None = None
        self.context: async_api.BrowserContext | None = None

        self.callback = callback

    async def init_browser(self) -> None:
        self.playwright = await async_api.async_playwright().start()
        self.browser = await self.playwright.firefox.launch(headless=False)
        self.context = await self.browser.new_context(ignore_https_errors=True)

    async def get_html_content_from_playwright(self, document_uri: str) -> None:
        self.active_tasks += 1
        self.all_tasks_done.clear()

        page = await self.context.new_page()
        try:
            await page.goto(document_uri)
            # await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_load_state("networkidle")
            content = await page.content()
            self.callback(document_uri, content)

        except PlaywrightError as e:
            print(f"Failed to load page: {e}")
            self.callback(document_uri, None)

        finally:
            await page.close()
            self.active_tasks -= 1
            if 0 >= self.active_tasks:
                self.all_tasks_done.set()

    async def close_browser(self):
        await asyncio.sleep(1)
        await self.all_tasks_done.wait()
        await self.context.close()
        print("Context closed")
        await self.browser.close()

    async def fetch_url_content(self, url: str) -> asyncio.Task:
        get_content_task = self.get_html_content_from_playwright(url)
        return asyncio.create_task(get_content_task)


# Define the callback function
def content_loaded_callback(url: str, content: str | None) -> None:
    if content is None:
        print(f"Failed to retrieve content from {url}")
    else:
        print(f"Content from {url} retrieved")
    # Here, you can process the content further if needed


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

    pb = PlaywrightBrowser(content_loaded_callback)
    await pb.init_browser()

    for each_url in url_list_a:
        await pb.fetch_url_content(each_url)

    await asyncio.sleep(10)

    for each_url in url_list_b:
        await pb.fetch_url_content(each_url)

    await pb.close_browser()


if __name__ == "__main__":
    asyncio.run(main())

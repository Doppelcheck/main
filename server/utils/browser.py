import asyncio
import dataclasses

import bs4
from loguru import logger
from playwright import async_api
from playwright._impl._errors import Error as PlaywrightError



@dataclasses.dataclass(frozen=True)
class HTMLResponse:
    uri: str
    content: str | None
    error: str | None = None


class PlaywrightBrowser:
    def __init__(self, headless: bool = True) -> None:
        self.headless = headless

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
            self.browser = await self.playwright.firefox.launch(headless=self.headless)

        if self.context is None:
            self.context = await self.browser.new_context(ignore_https_errors=True)

    def remove_images(self, html: str) -> str:
        soup = bs4.BeautifulSoup(html, 'html.parser')
        for each_element in soup.find_all('img'):
            each_element.decompose()

        for each_element in soup.find_all('svg'):
            each_element.decompose()

        return str(soup)

    async def get_html_content(self, document_uri: str, scroll: bool = False, remove_images: bool = True) -> HTMLResponse:
        await self.init_browser()

        event_loop = asyncio.get_event_loop()

        start_time = event_loop.time()

        self.active_tasks += 1
        self.all_tasks_done.clear()

        page = await self.context.new_page()
        try:
            await page.goto(document_uri, wait_until="domcontentloaded")
            await page.wait_for_load_state("domcontentloaded")
            # await page.wait_for_load_state("networkidle")

            if scroll:
                async def scroll_to_bottom() -> bool:
                    previous_position = await page.evaluate("window.scrollY")
                    await page.keyboard.press('End')
                    await asyncio.sleep(2)  # Adjust delay as necessary
                    current_position = await page.evaluate("window.scrollY")
                    return current_position <= previous_position

                while not await scroll_to_bottom():
                    pass

            content = await page.content()
            if not remove_images:
                return HTMLResponse(uri=document_uri, content=content, error=None)

            content_no_images = self.remove_images(content)
            return HTMLResponse(uri=document_uri, content=content_no_images, error=None)

        except PlaywrightError as e:
            print(f"Failed to load page: {e}")
            return HTMLResponse(uri=document_uri, content=None, error=str(e))

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


async def main():
    browser = PlaywrightBrowser()
    url = "https://www.tagesschau.de/wirtschaft/warnstreik-flughafen-frankfurt-102.html"
    html_response = await browser.get_html_content(url)
    print(html_response)

    await browser.close_browser()


if __name__ == "__main__":
    asyncio.run(main())

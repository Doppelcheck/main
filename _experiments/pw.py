import asyncio
import random
import time

from tools.content_retrieval import PlaywrightBrowser


async def fetch_url_content(url: str, pb: PlaywrightBrowser) -> None:
    content = await pb.get_html_content(url)
    print(f"Content from {content.uri}")


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


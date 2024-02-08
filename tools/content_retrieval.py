import asyncio
from typing import Callable
from urllib.parse import quote, urlparse

import httpx
import newspaper
import requests
from loguru import logger
from newspaper import network
from newspaper.article import ArticleDownloadState
from newspaper.utils import extract_meta_refresh

header = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/W.X.Y.Z Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
}


class AsyncArticle(newspaper.Article):
    async def async_download(self, session: httpx.AsyncClient, input_html=None, title=None, recursion_counter=0) -> None:
        """Downloads the link's HTML content asynchronously, don't use if you are batch async
        downloading articles

        recursion_counter (currently 1) stops refreshes that are potentially
        infinite
        """
        if input_html is None:
            try:
                html = await bypass_paywall_session(self.url, session)
            except httpx.HTTPError as e:
                self.download_state = ArticleDownloadState.FAILED_RESPONSE
                self.download_exception_msg = str(e)
                logger.warning(f"Download failed on URL %s because of {(self.url, self.download_exception_msg)}")
                return
        else:
            html = input_html

        if self.config.follow_meta_refresh:
            meta_refresh_url = extract_meta_refresh(html)
            if meta_refresh_url and recursion_counter < 1:
                return self.download(
                    input_html=network.get_html(meta_refresh_url),
                    recursion_counter=recursion_counter + 1)

        self.set_html(html)
        self.set_title(title)


async def parse_url(url: str, detect_language: Callable[[str], str]) -> newspaper.Article:
    # article = newspaper.Article(url, fetch_images=False)
    article = AsyncArticle(url, fetch_images=False)
    # article.download()
    session = httpx.AsyncClient()
    await article.async_download(session)

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


def outline_outlinetts(url: str) -> str:
    """
    Generates a proxy URL for the clean version of a website using the Outline TTS service.

    :param url: Original URL of the website
    :return: Proxy URL for the clean version
    """
    service_url = 'https://outlinetts.com/article'
    parsed_url = urlparse(url)
    protocol = parsed_url.scheme
    netloc_and_path = url.split("://", 1)[1] if "://" in url else url
    return f"{service_url}/{protocol}/{netloc_and_path}"


def outline_12ft(url: str) -> str:
    """
    Generates a proxy URL for the clean version of a website using the 12ft service.

    :param url: Original URL of the website
    :return: Proxy URL for the clean version
    """
    service_url = 'https://12ft.io'
    return f"{service_url}/{url}"


def outline_printfriendly(url: str) -> str:
    """
    Generates a proxy URL for the clean version of a website using the Print Friendly service.

    :param url: Original URL of the website
    :return: Proxy URL for the clean version
    """
    service_url = 'https://www.printfriendly.com/print'
    encoded_url = quote(url, safe='')
    return f"{service_url}/?source=homepage&url={encoded_url}"


async def outline_darkread(url: str) -> str:
    """
    Generates a proxy URL for the clean version of a website using the Darkread service.

    :param url: Original URL of the website
    :return: Proxy URL for the clean version or an error message if something goes wrong
    """
    try:
        proxy = 'https://outliner-proxy-darkread.rodrigo-828.workers.dev/cors-proxy'
        proxy_url = f"{proxy}/{url}"

        response = httpx.get(proxy_url)
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code

        data = response.json()
        uid = data.get('uid')
        if uid:
            service_website = 'https://www.darkread.io'
            return f"{service_website}/{uid}"
        else:
            return "Error: UID not found in the response."
    except httpx.HTTPError as e:
        return f"HTTP Request failed: {e}"


async def async_outline_darkread(url: str) -> str:
    """
    Generates a proxy URL for the clean version of a website using the Darkread service, asynchronously.

    :param url: Original URL of the website
    :return: Proxy URL for the clean version or an error message if something goes wrong
    """
    try:
        proxy = 'https://outliner-proxy-darkread.rodrigo-828.workers.dev/cors-proxy'
        proxy_url = f"{proxy}/{url}"

        async with httpx.AsyncClient() as client:
            response = await client.get(proxy_url)
            response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code

            data = response.json()
            uid = data.get('uid')
            if uid:
                service_website = 'https://www.darkread.io'
                return f"{service_website}/{uid}"
            else:
                return "Error: UID not found in the response."
    except httpx.HTTPError as e:
        return f"HTTP Request failed: {e}"


def bypass_paywall(url: str) -> str:
    response = requests.get(url, headers=header)
    response.encoding = response.apparent_encoding
    return response.text


async def bypass_paywall_session(url: str, session: httpx.AsyncClient) -> str:
    response = await session.get(url, headers=header)
    # new_url = outline_12ft(url)
    # response = await session.get(new_url)
    return response.text


async def get_context(original_url: str, detect_language: Callable[[str], str]) -> str | None:
    article = await parse_url(original_url, detect_language)
    context = f"{article.title.upper()}\n\n{article.summary}"
    if len(context.strip()) < 20:
        return None
    if article.publish_date is not None:
        context += f"\n\npublished on {article.publish_date}"
    return context

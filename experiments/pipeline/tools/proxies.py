from typing import Optional
from urllib.parse import quote, urlparse

import httpx


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

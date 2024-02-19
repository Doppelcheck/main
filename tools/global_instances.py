import httpx

from tools.content_retrieval import PlaywrightBrowser

BROWSER_INSTANCE = PlaywrightBrowser()
HTTPX_SESSION = httpx.AsyncClient()

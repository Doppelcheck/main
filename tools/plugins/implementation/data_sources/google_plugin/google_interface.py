import dataclasses
from typing import AsyncGenerator

from tools.content_retrieval import Document
from tools.global_instances import BROWSER_INSTANCE, HTTPX_SESSION
from tools.plugins.abstract import InterfaceData, Uri
from tools.plugins.implementation.data_sources.google_plugin.google_dataclasses import ParametersGoogle


class ReceiveGoogleResultsException(Exception):
    pass


class QueryGoogle(InterfaceData):
    async def get_uris(self, query: str, doc_count: int, parameters: ParametersGoogle) -> AsyncGenerator[Uri, None]:
        url = "https://www.googleapis.com/customsearch/v1"
        # https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list#response
        # todo: use llm to craft parameter dict

        params = {k: v for k, v in dataclasses.asdict(parameters).items() if v is not None}
        params["q"] = query
        params["num"] = doc_count

        # async with httpx.AsyncClient() as httpx_session:
        #    response = await httpx_session.get(url, params=params)

        response = await HTTPX_SESSION.get(url, params=params)

        if response.status_code != 200:
            raise ReceiveGoogleResultsException(
                f"Request failed with status code {response.status_code}: {response.text}"
            )

        # https://developers.google.com/custom-search/v1/reference/rest/v1/Search
        result = response.json()

        items = result.get("items")
        if items is None:
            raise ReceiveGoogleResultsException(f"Google did not return results for {query}")

        # https://developers.google.com/custom-search/v1/reference/rest/v1/Search#Result
        for each_item in items:
            yield Uri(uri_string=each_item['link'])

    async def get_document_content(self, uri: str) -> Document:
        return await BROWSER_INSTANCE.get_html_content(uri)

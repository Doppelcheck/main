"""
Search query generation and results retrieval service.
Simple, modular approach to search across different engines with fallback mechanisms.
"""
import asyncio
import time
from urllib.parse import urlparse, quote_plus, unquote
import re

from loguru import logger
from pydantic import HttpUrl

from googlesearch import search
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import requests
from bs4 import BeautifulSoup

from server.models import SearchResult
from server.services.llm_ollama import get_search_query
from server.utils import config


class SearchEngineNotSupported(Exception):
    """Raised when an unsupported search engine is requested."""
    pass


def normalize_url(url: str) -> str:
    """Normalize a URL to ensure it has a scheme."""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url


def extract_domain(url: str) -> str:
    """Extract domain from a URL."""
    parsed = urlparse(normalize_url(url))
    return parsed.netloc


def is_domain_match(url: str, domain: str) -> bool:
    """Check if a URL belongs to the specified domain or subdomain."""
    if not url or not domain:
        return False

    # Normalize domain for comparison
    domain = domain.lower()
    if not domain.startswith(('http://', 'https://')):
        domain_to_check = domain
    else:
        domain_to_check = extract_domain(domain)

    # Get the domain from the URL
    url_domain = extract_domain(url).lower()

    # Check if the URL's domain matches or is a subdomain
    return url_domain == domain_to_check or url_domain.endswith('.' + domain_to_check)


class SearchProvider:
    """Base class for search providers."""

    def __init__(self, max_results: int = 5, timeout: int = 10, retry_count: int = 2, delay: float = 1.0):
        self.max_results = max_results
        self.timeout = timeout
        self.retry_count = retry_count
        self.delay = delay
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': 'https://www.google.com/'
        }

    async def search(self, query: str, domain: str | None = None) -> list[SearchResult]:
        """Search for the query, optionally restricted to a domain."""
        raise NotImplementedError("Subclasses must implement search")

    def name(self) -> str:
        """Return the name of the search provider."""
        return self.__class__.__name__.replace("SearchProvider", "").lower()

    def filter_results_by_domain(self, results: list[SearchResult], domain: str) -> list[SearchResult]:
        """Filter search results to only include those matching the domain."""
        if not domain:
            return results

        filtered_results = []
        for result in results:
            if is_domain_match(str(result.url), domain):
                filtered_results.append(result)

        return filtered_results


class OfficialGoogleSearchProvider(SearchProvider):
    """Provider for Google search using the official Google Custom Search API."""

    def __init__(self, max_results: int = 5, timeout: int = 10, retry_count: int = 2, delay: float = 1.0):
        super().__init__(max_results, timeout, retry_count, delay)

        self.api_key = config.get("google_custom_search_api_key")
        self.search_engine_id = config.get("google_custom_search_engine_id")

        if not self.api_key or not self.search_engine_id:
            logger.warning("Google API Key or Search Engine ID not provided. These must be set before searching.")

    async def search(self, query: str, domain: str | None = None) -> list[SearchResult]:
        """Perform Google search using the official Google Custom Search API."""
        results = list()

        if not self.api_key or not self.search_engine_id:
            logger.error("Google API Key and Search Engine ID must be set for OfficialGoogleSearchProvider")
            return results

        if domain:
            query = f"{query} site:{extract_domain(domain)} -filetype:pdf"

        logger.info(f"Performing official Google API search for: '{query}'")

        # Import here to avoid requiring the library for users who don't use this provider
        for attempt in range(self.retry_count):
            try:
                # Create a service object
                service = build("customsearch", "v1", developerKey=self.api_key)

                # https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list
                # Prepare search parameters
                search_params = {
                    'q': query,
                    'cx': self.search_engine_id,
                    'num': self.max_results,
                    # 'siteSearchFilter': 'i',
                    # 'siteSearch': "news.google.com",
                    # 'siteSearch': extract_domain(domain),
                }

                # Execute the search
                search_instance = service.cse().list(**search_params)
                response = search_instance.execute()

                # Process the results
                if 'items' in response:
                    for item in response['items']:
                        try:
                            result = SearchResult(
                                url=HttpUrl(item.get('link')),
                                title=item.get('title', ''),
                                snippet=item.get('snippet', '')
                            )
                            results.append(result)
                        except Exception as e:
                            logger.error(f"Error creating search result: {e}")
                            continue
                else:
                    logger.info(f"No search results found for query: '{query}'")

                break  # If we get here without exception, break the retry loop

            except HttpError as e:
                logger.error(f"Google API HTTP error: {e}")
                if e.resp.status in [429, 500, 503]:  # Rate limit or server error
                    if attempt < self.retry_count - 1:
                        wait_time = self.delay * (2 ** attempt)  # Exponential backoff
                        logger.info(f"Retrying in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                        continue
                break  # For other HTTP errors, don't retry

            except Exception as e:
                logger.error(f"Google API search error: {e}")
                if attempt < self.retry_count - 1:
                    await asyncio.sleep(self.delay)
                    continue
                break

        # Double-check domain filtering
        if domain and results:
            results = self.filter_results_by_domain(results, domain)

        return results


class GoogleSearchProvider(SearchProvider):
    """Provider for Google search."""

    async def search(self, query: str, domain: str | None = None) -> list[SearchResult]:
        """Perform Google search."""
        results = []

        if domain:
            query = f"{query} site:{extract_domain(domain)}"

        logger.info(f"Performing Google search for: '{query}'")

        try:
            for each_result in search(query, lang="de", num_results=self.max_results, advanced=True):
                if not each_result.url or not each_result.title:
                    logger.warning(f"Skipping incomplete search result: {each_result}")
                    continue

                try:
                    result = SearchResult(
                        url=HttpUrl(each_result.url),
                        title=each_result.title,
                        snippet=each_result.description
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error creating search result: {e}")
                    continue

        except Exception as e:
            logger.error(f"Google search error: {e}")

        # Double-check domain filtering
        if domain and results:
            results = self.filter_results_by_domain(results, domain)

        return results


class DuckDuckGoSearchProvider(SearchProvider):
    """Provider for DuckDuckGo search."""

    async def search(self, query: str, domain: str | None = None) -> list[SearchResult]:
        """Perform DuckDuckGo search."""
        results = []
        original_query = query

        if domain:
            query = f"{query} site:{extract_domain(domain)}"

        logger.info(f"Performing DuckDuckGo search for: '{query}'")

        for attempt in range(self.retry_count):
            try:
                url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
                response = requests.get(url, headers=self.headers, timeout=self.timeout)

                # DuckDuckGo sometimes returns 202 for valid requests, we'll consider it as successful
                if response.status_code == 202:
                    logger.info(f"DuckDuckGo returned status code 202, retrying in {self.delay} seconds...")
                    time.sleep(self.delay)
                    continue

                if response.status_code != 200:
                    logger.warning(f"DuckDuckGo returned status code {response.status_code}")
                    if attempt < self.retry_count - 1:
                        time.sleep(self.delay)
                        continue
                    else:
                        return results

                soup = BeautifulSoup(response.text, 'html.parser')

                # Check if the page contains results
                if "No results found" in response.text:
                    logger.info("DuckDuckGo returned no results")
                    return results

                if not soup.select('.result'):
                    logger.warning("No result elements found in DuckDuckGo response")
                    if attempt < self.retry_count - 1:
                        time.sleep(self.delay)
                        continue
                    else:
                        return results

                for result in soup.select('.result'):
                    try:
                        title_elem = result.select_one('.result__title')
                        if not title_elem:
                            continue

                        link_elem = title_elem.select_one('a')
                        if not link_elem:
                            continue

                        raw_url = link_elem.get('href', '')
                        if not raw_url:
                            continue

                        # Extract actual URL from DuckDuckGo redirect URL
                        actual_url = raw_url
                        if '/uddg=' in raw_url:
                            url_match = re.search(r'/uddg=([^&]+)', raw_url)
                            if url_match:
                                actual_url = unquote(url_match.group(1))

                        title = title_elem.get_text(strip=True)
                        snippet_elem = result.select_one('.result__snippet')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                        try:
                            result = SearchResult(
                                url=HttpUrl(normalize_url(actual_url)),
                                title=title,
                                snippet=snippet
                            )
                            results.append(result)
                        except Exception as e:
                            logger.error(f"Error creating search result: {e}")
                            continue

                        if len(results) >= self.max_results:
                            break

                    except Exception as e:
                        logger.error(f"Error processing DuckDuckGo result: {e}")
                        continue

                # If we got here successfully, break out of retry loop
                if results:
                    break
                else:
                    logger.warning("No valid results found in DuckDuckGo response")
                    if attempt < self.retry_count - 1:
                        time.sleep(self.delay)
                        continue

            except Exception as e:
                logger.error(f"DuckDuckGo search error: {e}")
                if attempt < self.retry_count - 1:
                    time.sleep(self.delay)
                else:
                    break

        # Apply manual domain filtering regardless of "site:" operator
        if domain and results:
            filtered_results = self.filter_results_by_domain(results, domain)
            # If we get no results after filtering, try a broader search
            if not filtered_results and len(results) > 0:
                logger.info(f"No results match domain {domain} after filtering. Trying broader search.")
                return await self.search(original_query, None)
            results = filtered_results

        return results


class BingSearchProvider(SearchProvider):
    """Provider for Bing search."""

    async def search(self, query: str, domain: str | None = None) -> list[SearchResult]:
        """Perform Bing search."""
        results = []
        original_query = query

        # For Bing, we'll still include the site: operator but will also
        # implement post-filtering since Bing doesn't respect the operator reliably
        if domain:
            query = f"{query} site:{extract_domain(domain)}"

        logger.info(f"Performing Bing search for: '{query}'")

        for attempt in range(self.retry_count):
            try:
                url = f"https://www.bing.com/search?q={quote_plus(query)}"
                response = requests.get(url, headers=self.headers, timeout=self.timeout)

                if response.status_code != 200:
                    logger.warning(f"Bing returned status code {response.status_code}")
                    if attempt < self.retry_count - 1:
                        time.sleep(self.delay)
                        continue
                    else:
                        return results

                soup = BeautifulSoup(response.text, 'html.parser')

                # Process the results
                for result in soup.select('.b_algo'):
                    try:
                        title_elem = result.select_one('h2 a')
                        if not title_elem:
                            continue

                        title = title_elem.get_text(strip=True)
                        url = title_elem.get('href', '')

                        if not url or not title:
                            continue

                        snippet_elem = result.select_one('.b_caption p')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                        try:
                            result = SearchResult(
                                url=HttpUrl(normalize_url(url)),
                                title=title,
                                snippet=snippet
                            )
                            results.append(result)
                        except Exception as e:
                            logger.error(f"Error creating search result: {e}")
                            continue

                        if len(results) >= self.max_results * 2:  # Get more results for filtering
                            break

                    except Exception as e:
                        logger.error(f"Error processing Bing result: {e}")
                        continue

                if results:
                    break
                else:
                    logger.warning("No valid results found in Bing response")
                    if attempt < self.retry_count - 1:
                        time.sleep(self.delay)
                        continue

            except Exception as e:
                logger.error(f"Bing search error: {e}")
                if attempt < self.retry_count - 1:
                    time.sleep(self.delay)
                else:
                    break

        # Apply strict domain filtering
        if domain and results:
            logger.info(f"Filtering Bing results to match domain: {domain}")
            filtered_results = self.filter_results_by_domain(results, domain)

            # If we filtered out all results, try a broader search
            if not filtered_results and len(results) > 0:
                logger.info(f"No results match domain {domain} after filtering. Returning unfiltered results for reference.")
                # Return the original results but limited to max_results
                return results[:self.max_results]

            results = filtered_results

        return results[:self.max_results]  # Limit to requested max_results


def get_search_provider(engine: str = "google_api", max_results: int = 5, timeout: int = 10) -> SearchProvider:
    """Factory function to get the appropriate search provider."""
    engines = {
        "google_api": OfficialGoogleSearchProvider,
        "google": GoogleSearchProvider,
        "duckduckgo": DuckDuckGoSearchProvider,
        "bing": BingSearchProvider,
    }

    provider_class = engines.get(engine.lower())
    if not provider_class:
        supported = ", ".join(engines.keys())
        raise SearchEngineNotSupported(f"Engine '{engine}' not supported. Choose from: {supported}")

    return provider_class(max_results=max_results, timeout=timeout)


async def search_urls(
        query: str, domain: str | None = None, engine: str = "google", max_results: int = 5, fallback: bool = True
) -> list[SearchResult]:
    """
    Unified search function that works with any supported search engine.

    Args:
        query: Search query string
        domain: Optional domain to restrict the search to
        engine: Search engine to use (google, duckduckgo, bing)
        max_results: Maximum number of results to return
        fallback: Whether to try other engines if the primary engine fails

    Returns:
        List of search results
    """
    # Try the requested engine first
    provider = get_search_provider(engine, max_results)
    logger.info(f"Using search engine: {engine}")

    results = await provider.search(query, domain)

    # If no results and fallback is enabled, try other engines
    if not results and fallback:
        logger.info(f"No results from {engine}, trying fallback engines")

        # Get a list of alternative engines to try (all except the one we just tried)
        fallback_engines = ["google", "duckduckgo", "bing"]
        if engine.lower() in fallback_engines:
            fallback_engines.remove(engine.lower())

        # Try each fallback engine until we get results
        for fallback_engine in fallback_engines:
            logger.info(f"Trying fallback engine: {fallback_engine}")
            fallback_provider = get_search_provider(fallback_engine, max_results)
            fallback_results = await fallback_provider.search(query, domain)

            if fallback_results:
                logger.info(f"Got {len(fallback_results)} results from fallback engine: {fallback_engine}")
                return fallback_results

    if not results:
        domain_str = f" on domain: '{domain}'" if domain else ""
        logger.warning(f"No results found for query: '{query}'{domain_str} using engine: '{engine}' (with fallback: {fallback})")
    else:
        logger.info(f"Found {len(results)} results from {engine}")

    return results


# Test functionality
async def test_search():
    engines = ["google_api", "google", "duckduckgo", "bing"]
    queries = ["python programming language", "python programming language tutorial"]
    domains = [None, "wikipedia.org", "tutorialspoint.com"]

    for engine in engines:
        print(f"\n--- TESTING {engine.upper()} SEARCH ENGINE ---")

        for query in queries:
            for domain in domains:
                domain_str = f"on '{domain}'" if domain else ""
                print(f"\nSearch query: '{query}' {domain_str}")

                try:
                    # Don't use fallback here to test each engine independently
                    results = await search_urls(query, domain, engine, fallback=False)

                    if results:
                        print(f"Found {len(results)} results:")
                        for i, result in enumerate(results, 1):
                            print(f"{i}. {result.title}")
                            print(f"   URL: {result.url}")
                            print(f"   Snippet: {result.snippet[:100]}..." if result.snippet else "   No snippet")
                    else:
                        print("No results found")

                except Exception as e:
                    print(f"Error during search: {e}")


async def main():
    await test_search()


if __name__ == "__main__":
    asyncio.run(main())
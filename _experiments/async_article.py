import httpx
import newspaper

from loguru import logger
from newspaper import network
from newspaper.article import ArticleDownloadState
from newspaper.utils import extract_meta_refresh

from tools.content_retrieval import PlaywrightBrowser


class AsyncArticle(newspaper.Article):
    async def async_download(self, browser: PlaywrightBrowser, input_html=None, title=None, recursion_counter=0) -> None:
        """Downloads the link's HTML content asynchronously, don't use if you are batch async
        downloading articles

        recursion_counter (currently 1) stops refreshes that are potentially
        infinite
        """
        if input_html is None:
            try:
                source = await browser.get_html_content(self.url)
                html = source.content

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


if __name__ == "__main__":
    url = "https://www.spiegel.de/ausland/israels-verteidigungsminister-gallant-nennt-geiselbefreiung-im-gazastreifen-wendepunkt-militaereinsatz-in-rafah-a-dc6b2c8d-5af5-4ee7-b468-13ef20ed441d"
    article = newspaper.Article(url)
    article.download()
    article.parse()
    article.nlp()

    print(article.publish_date)
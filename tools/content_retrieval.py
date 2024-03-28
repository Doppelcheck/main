import bs4
import newspaper

from tools.global_instances import DETECTOR_BUILT

header = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/W.X.Y.Z Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
}


async def parse_url(url: str, input_html: str | None = None) -> newspaper.Article:
    article = newspaper.Article(url, fetch_images=False)
    article.download(input_html=input_html)

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


def remove_images(html: str) -> str:
    soup = bs4.BeautifulSoup(html, 'html.parser')
    for each_element in soup.find_all('img'):
        each_element.decompose()

    for each_element in soup.find_all('svg'):
        each_element.decompose()

    return str(soup)


def detect_language(text: str) -> str:
    language = DETECTOR_BUILT.detect_language_of(text)
    if language is None:
        return "en"

    return language.iso_code_639_1.name.lower()

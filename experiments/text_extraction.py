import newspaper
import nltk
import readabilipy
import readability
import requests


def readabilipy_extract(url: str) -> str:
    # https://github.com/alan-turing-institute/ReadabiliPy
    response = requests.get(url)
    article = readabilipy.simple_json_from_html_string(response.text, use_readability=True)
    return article['content']


def readability_lxml_extract_from_html(html: str) -> str:
    # https://github.com/buriy/python-readability
    doc = readability.Document(html)

    # cleaned = doc.get_clean_html()
    summary = doc.summary()

    return summary


def readability_lxml_extract(url: str) -> str:
    # https://github.com/buriy/python-readability
    response = requests.get(url)
    return readability_lxml_extract_from_html(response.text)


def newspaper_extract(url: str) -> str:
    # https://github.com/codelucas/newspaper/
    article = newspaper.Article(url)
    article.download()
    article.parse()

    """
    article.nlp()

    keywords = article.keywords
    summary = article.summary
    """

    text = article.text
    return article.title + "\n\n" + text


def main() -> None:
    url = "https://www.tagesschau.de/ausland/europa/eu-gipfel-blcokade-ungarn-100.html"

    distilled_readabilipy = readabilipy_extract(url)
    print(
        f"=== Readabilipy\n"
        f"{distilled_readabilipy}\n"
    )

    distilled_readability = readability_lxml_extract(url)
    print(
        f"=== Readability\n"
        f"{distilled_readability}\n"
    )

    nltk.download('punkt')
    distilled_newspaper = newspaper_extract(url)
    print(
        f"=== Newspaper\n"
        f"{distilled_newspaper}\n"
    )


if __name__ == "__main__":
    main()

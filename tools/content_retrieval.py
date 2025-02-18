import math
import re
from dataclasses import dataclass
from typing import Sequence

import bs4
import markdownify
import readabilipy
import newspaper
import trafilatura

from markdown_it import MarkdownIt
from mdit_plain.renderer import RendererPlain

from tools.global_instances import DETECTOR_BUILT

from spacy.tokens.span import Span as Entity
import spacy

from semantic_text_splitter import semantic_text_splitter

from bs4 import BeautifulSoup
from markdown import markdown


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


def get_article(url: str, html: None | str = None) -> newspaper.Article:
    article = newspaper.Article(url)
    if html is None:
        article.download()
    else:
        article.set_html(html)
    article.parse()
    article.nlp()
    return article


@dataclass
class EntityWordInfo:
    entities: set[Entity]
    frequency: int


def entity_extraction(text: str) -> tuple[Entity, ...]:
    # nlp = spacy.load("de_core_news_sm")
    nlp = spacy.load("de_core_news_lg")
    doc = nlp(text)
    # displacy.serve(doc, style="ent")
    return tuple(doc.ents)


def extract_entities(text: str) -> dict[str, EntityWordInfo]:
    entities = entity_extraction(text)
    entity_word_info = dict()
    for each_entity in entities:
        entity_text = each_entity.text.lower()
        if entity_text in entity_word_info:
            entity_word_info[entity_text].frequency += 1
        else:
            entity_word_info[entity_text] = EntityWordInfo({each_entity}, 1)
    return entity_word_info


def segmentation(markdown_text: str, max_size: int = 500, min_size: int = 100) -> tuple[str, ...]:
# def segmentation(markdown_text: str, max_size: int = 1_000, min_size: int = 200) -> tuple[str, ...]:
    splitter = semantic_text_splitter.MarkdownSplitter(max_size)
    chunks = splitter.chunks(markdown_text)

    # join chunks that are too short
    chunks = list(chunks)
    for i in range(len(chunks) - 1):
        if len(chunks[i]) < min_size:
            chunks[i] += chunks[i + 1]
            chunks[i + 1] = ""
    chunks = [each_chunk for each_chunk in chunks if 0 < len(each_chunk)]
    return tuple(chunks)


def get_markdown_segments(markdown_text: str) -> tuple[str, ...]:
    chunks = segmentation(markdown_text)
    return tuple(chunks)


def markdown_to_text(markdown_text: str) -> str:
    html = markdown(markdown_text)
    soup = BeautifulSoup(html, "html.parser")
    plain_text = soup.get_text()
    return plain_text


def calculate_tf(entity_text: str, chunk_text: str) -> float:
    """Calculate term frequency of entity in chunk."""
    # Simple frequency-based TF
    return chunk_text.lower().count(entity_text.lower())


def calculate_idf(entity_text: str, chunks: Sequence[str]) -> float:
    """Calculate inverse document frequency of entity across chunks."""
    # Count in how many chunks the entity appears
    doc_frequency = sum(1 for chunk in chunks if entity_text.lower() in chunk.lower())
    # Add 1 for smoothing to avoid division by zero
    return math.log(len(chunks) / (doc_frequency + 1)) + 1


@dataclass
class ChunkScore:
    chunk_index: int
    score: float
    contributing_entities: dict[str, float]  # entity text -> contribution to score


def calculate_chunk_tfidf_scores(
        chunks: Sequence[str], entity_info: dict[str, EntityWordInfo], min_chunk_length: int = -1,
        min_global_frequency: int = -1, top_k: int = None
) -> list[ChunkScore]:
    """
    Calculate TF-IDF scores for each chunk based on named entities.

    Args:
        chunks: List of text chunks to analyze
        entity_info: Dictionary mapping entity text to EntityWordInfo
        min_chunk_length: Minimum length of a chunk to consider
        min_global_frequency: Minimum global frequency for an entity to be considered
        top_k: Number of top-scoring chunks to return, or None to return all

    Returns:
        List of ChunkScore objects containing scores and contributing entities
    """
    chunk_scores = list()

    # Filter entities by minimum global frequency
    relevant_entities = {
        entity_text: info
        for entity_text, info in entity_info.items()
        if min_global_frequency < 0 or info.frequency >= min_global_frequency
    }

    # Calculate IDF for each entity once
    entity_idfs = {
        entity_text: calculate_idf(entity_text, chunks)
        for entity_text in relevant_entities
    }

    # Calculate scores for each chunk
    for chunk_idx, chunk_text in enumerate(chunks):
        # Skip chunks that are too short
        if min_chunk_length >= 0 and len(chunk_text) < min_chunk_length:
            continue

        chunk_score = 0.0
        contributing_entities = dict()

        for entity_text, entity_info in relevant_entities.items():
            # Get entity type(s) for weighting
            entity_types = {e.label_ for e in entity_info.entities}

            # Optional: Apply weight based on entity type
            type_weight = 1.0
            if 'PER' in entity_types:  # Person names
                type_weight = 1.2
            elif 'ORG' in entity_types:  # Organizations
                type_weight = 1.1

            # Calculate TF-IDF with entity type weighting
            tf = calculate_tf(entity_text, chunk_text)
            idf = entity_idfs[entity_text]
            entity_score = tf * idf * type_weight

            if entity_score > 0:
                contributing_entities[entity_text] = entity_score
                chunk_score += entity_score

        chunk_scores.append(ChunkScore(
            chunk_index=chunk_idx,
            score=chunk_score,
            contributing_entities=contributing_entities
        ))

    # Sort chunks by score in descending order
    chunk_scores.sort(key=lambda x: x.score, reverse=True)

    if top_k is None:
        return chunk_scores

    return chunk_scores[:top_k]

def get_as_markdown(url: str) -> str:
    downloaded = trafilatura.fetch_url(url)
    md = trafilatura.extract(downloaded, output_format="markdown")
    return md

def get_relevant_chunks(markdown_text: str) -> tuple[str]:
    plain_text = markdown_to_plain_text(markdown_text)
    mapped_entities = extract_entities(plain_text)

    md_chunks = get_markdown_segments(markdown_text)
    chunk_scores = calculate_chunk_tfidf_scores(
        md_chunks, mapped_entities, top_k=5
    )

    return tuple(md_chunks[each_chunk_score.chunk_index] for each_chunk_score in chunk_scores)


def normalize_emphasis(markdown_text: str) -> str:
    # Normalize strong emphasis by stripping spaces inside the markers.
    # This regex finds **, optional whitespace, some text, optional whitespace, and **.
    # It then re-inserts the text without the extra spaces.
    return re.sub(r'\*\*\s*(.*?)\s*\*\*', r'**\1**', markdown_text)


def markdown_to_plain_text(markdown_text: str) -> str:
    normalized_text = normalize_emphasis(markdown_text)
    md = MarkdownIt(renderer_cls=RendererPlain)
    return md.render(normalized_text)


if __name__ == "__main__":
    test_text = """**analyse**# Ampelkoalition in der Krise Habecks Botschaft, Habecks Angebot
**Der Ampel-Regierung droht ein vorzeitiges Aus. Vizekanzler Habeck versucht noch einmal, das Bündnis zu retten. Mit einem Angebot an die FDP. Und nicht ganz ohne Eigennutz. **
Tagelang hat Vizekanzler Robert Habeck wenig bis gar nichts zur aktuellen Ampel-Krise gesagt. Nun also dieser Auftritt am Montagnachmittag, nur wenige Minuten lang."""

    plain = markdown_to_plain_text(test_text)
    print(plain)

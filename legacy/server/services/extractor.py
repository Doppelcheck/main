"""
HTML content extraction and chunking service.
"""
import re

import trafilatura
from rapidfuzz import fuzz


from server.services.llm_ollama import generate_summary
from server.utils.nlp import markdown_to_plain_text


def extract_content(html: str) -> str:
    """
    Extract main text content from HTML.

    Args:
        html: Raw HTML content

    Returns:
        Extracted markdown content
    """
    return trafilatura.extract(html, output_format="markdown")


def calculate_entity_relevance(entity_text: str, content: str, normalize: bool = False) -> float:
    """
    Berechnet die Relevanz einer Entität für einen Textinhalt basierend auf:
    1. Aufteilung des Inhalts in Sätze/Absätze
    2. Berechnung des Fuzzy-Matchings für jeden Teilbereich
    3. Summierung der Scores

    Args:
        entity_text: Text der Entität
        content: Textinhalt des Chunks
        normalize: Flag, um den Text zu normalisieren (Standard: False)

    Returns:
        Aggregierter Relevanz-Score
    """
    # Text in Sätze aufteilen
    segments = re.split(r'[.!?]\s+', content.lower())

    # Entity-Text normalisieren
    entity_lower = entity_text.lower()

    # Scores für jeden Satz berechnen und summieren
    total_score = 0
    for each_segment in segments:
        if len(each_segment) < 1:  # Leere Segmente überspringen
            continue
        # Fuzzy-Matching berechnen
        partial_score = fuzz.partial_ratio(entity_lower, each_segment) / 100.
        if partial_score >= .5:
            total_score += partial_score

    if normalize:
        return total_score / len(segments)

    return total_score


async def complete_chunks(
        chunks: list[dict[str, any]], context: dict[str, any],
        model: str, ollama_host: str, top_n_entities: int = 5
) -> list[dict[str, any]]:
    """
    Generate summaries for relevant chunks using LLM.

    Args:
        chunks: List of relevant chunks
        context: Additional context
        model: Name of the LLM model
        ollama_host: URL of the Ollama API
        top_n_entities: Anzahl der relevantesten Entitäten pro Chunk

    Returns:
        Chunks with added summaries and relevant entities
    """

    summaries = list()
    for each_chunk in chunks:
        each_content = markdown_to_plain_text(each_chunk["content"])

        entity_relevance = dict(each_chunk["entities"])
        max_relevance = max(entity_relevance.values(), default=1)
        for each_entity in entity_relevance:
            entity_relevance[each_entity] /= max_relevance
            
        summary = await generate_summary(each_content, model, ollama_host, context=context)
        each_chunk["summary"] = summary
        summaries.append(dict(each_chunk))

    return summaries
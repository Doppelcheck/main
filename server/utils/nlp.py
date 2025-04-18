import math
import re
from typing import Sequence, Collection

from spacy.tokens.span import Span as Entity
import spacy
from dataclasses import dataclass

from markdown_it import MarkdownIt
from mdit_plain.renderer import RendererPlain


@dataclass
class EntityWordInfo:
    entities: list[str]

    @property
    def frequency(self):
        return len(self.entities)


def cluster_german_entities(entities: Collection[Entity]) -> dict[str, EntityWordInfo]:
    """
    Cluster similar entities and return a dictionary with the shortest entity text
    as key and an EntityWordInfo object as value.

    Args:
        entities (list[Entity]): List of Entity objects extracted from text

    Returns:
        dict[str, EntityWordInfo]: Dictionary with shortest entity string as key
                                   and EntityWordInfo object as value
    """

    # Clean a string for comparison purposes
    def clean_text(text: str) -> str:
        return ' '.join(text.lower().split())

    # Calculate Jaccard similarity between two strings
    def jaccard_similarity(str1: str, str2: str) -> float:
        set1: set[str] = set(str1.lower().split())
        set2: set[str] = set(str2.lower().split())

        if not set1 or not set2:
            return 0.0

        intersection: int = len(set1.intersection(set2))
        union: int = len(set1) + len(set2) - intersection

        return intersection / union if union > 0 else 0.0

    # Build adjacency list for the similarity graph
    graph = {i: list() for i in range(len(entities))}
    entity_list = list(entities)

    # Connect similar entities in the graph
    for i in range(len(entity_list)):
        for j in range(i + 1, len(entity_list)):
            text1 = clean_text(entity_list[i].text)
            text2 = clean_text(entity_list[j].text)

            is_substring = text1.lower() in text2.lower() or text2.lower() in text1.lower()
            similarity = jaccard_similarity(text1, text2)

            if is_substring or similarity > 0.5:
                graph[i].append(j)
                graph[j].append(i)

    # Find connected components (clusters)
    visited = set()
    clusters = list()

    def dfs(_node: int, _component: list[Entity]) -> None:
        visited.add(_node)
        _component.append(entity_list[_node])
        for neighbor in graph[_node]:
            if neighbor not in visited:
                dfs(neighbor, _component)

    for i in range(len(entity_list)):
        if i not in visited:
            component = list()
            dfs(i, component)
            clusters.append(component)

    # Build result dictionary as before
    result = dict()
    for cluster in clusters:
        shortest = min([clean_text(entity.text) for entity in cluster], key=len)
        info = EntityWordInfo(entities=cluster)
        result[shortest] = info

    return result


def entity_extraction(text: str) -> tuple[Entity, ...]:
    # nlp = spacy.load("de_core_news_sm")
    nlp = spacy.load("de_core_news_lg")
    doc = nlp(text)
    # displacy.serve(doc, style="ent")
    return tuple(doc.ents)


def normalize_emphasis(markdown_text: str) -> str:
    # Normalize strong emphasis by stripping spaces inside the markers.
    # This regex finds **, optional whitespace, some text, optional whitespace, and **.
    # It then re-inserts the text without the extra spaces.
    return re.sub(r'\*\*\s*(.*?)\s*\*\*', r'**\1**', markdown_text)


def markdown_to_plain_text(markdown_text: str) -> str:
    normalized_text = normalize_emphasis(markdown_text)
    md = MarkdownIt(renderer_cls=RendererPlain)
    return md.render(normalized_text)


def get_top_chunks(md_chunks: list[str], mapped_entities: dict[str, EntityWordInfo], top_k: int = 5) -> list[dict[str, any]]:
    chunk_scores = calculate_chunk_tfidf_scores(
        md_chunks, mapped_entities, top_k=top_k, min_global_frequency=2
    )

    ranked_chunks = list()
    for each_chunk_score in chunk_scores:
        each_chunk = dict()
        each_index = int(each_chunk_score.chunk_index)
        each_chunk["content"] = md_chunks[each_index]
        each_chunk["importance"] = each_chunk_score.score
        each_chunk["entities"] = each_chunk_score.contributing_entities
        ranked_chunks.append(each_chunk)

    return ranked_chunks


@dataclass
class ChunkScore:
    chunk_index: int
    score: float
    contributing_entities: dict[str, float]  # entity text -> contribution to score


def calculate_tf(entity_text: str, chunk_text: str) -> float:
    """Calculate term frequency of entity in chunk."""
    # Simple frequency-based TF
    return chunk_text.lower().count(entity_text.lower())


def calculate_idf(entity_text: str, chunks: Sequence[str]) -> float:
    """Calculate inverse document frequency of entity across chunks."""
    # Count in how many chunks the entity appears
    doc_frequency = sum(1 for each_chunk in chunks if entity_text.lower() in each_chunk.lower())
    # Add 1 for smoothing to avoid division by zero
    return math.log(len(chunks) / (doc_frequency + 1)) + 1


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
    text_chunks = tuple(markdown_to_plain_text(each_chunk) for each_chunk in chunks)
    entity_idfs = {
        entity_text: calculate_idf(entity_text, text_chunks)
        for entity_text in relevant_entities
    }

    # Calculate scores for each chunk
    for chunk_idx, each_chunk in enumerate(chunks):
        chunk_text = markdown_to_plain_text(each_chunk)

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
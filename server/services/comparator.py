"""
Semantic comparison of chunks with search result content.
"""

from typing import Dict, Any, Optional, Sequence
from pydantic import HttpUrl

from server.retrievers.e5_semantic_retrieval import retrieve_similar_chunks as retrieve_similar_chunks_embedding
from server.retrievers.smith_waterman_retriever import retrieve_similar_chunks as retrieve_similar_chunks_smith
from server.services.extractor import extract_content
from server.services.llm_ollama import compare_text_segments
from server.utils.alignment import calculate_semantic_alignment
from server.utils.chunker import extract_complete_sentences, chunk_markdown
from server.utils.globals import BROWSER
from server.utils.nlp import markdown_to_plain_text

from loguru import logger


async def fetch_url_content(url: HttpUrl) -> Optional[str]:
    """
    Fetch content from a URL asynchronously.

    Args:
        url: URL to fetch

    Returns:
        HTML content or None if failed
    """
    url_str = f"{url}"
    html_response = await BROWSER.get_html_content(url_str)
    return html_response.content


def get_similarity_score(original_chunk: str, chunks: Sequence[str]) -> tuple[str, float]:
    """
    Calculate similarity score between original chunk and source content.
    
    Args:
        original_chunk: Original chunk content
        chunks: List of relevant chunks to compare against
        
    Returns:
        Tuple of most relevant content and similarity score
    
    """

    scores = list[float]()
    for each_chunk in chunks[:10]:
        each_score = calculate_semantic_alignment(original_chunk, each_chunk)
        scores.append(each_score)

    # max_abs_score < -.2:    "Contradiction"
    # max_abs_score < .2:     "Irrelevant")
    # else:                   "Support"
    max_abs_score_index, max_abs_score = max(enumerate(scores), key=lambda x: abs(x[1]))
    most_relevant_content = chunks[max_abs_score_index]
    return most_relevant_content, max_abs_score


async def calculate_alignment(
        original_chunk_plain: str,
        query: str,
        url: HttpUrl,
        context: Dict[str, Any],
        model: str,
        ollama_host: str
) -> Dict[str, Any]:
    """
    Calculate semantic alignment between original chunk and URL content.

    Args:
        original_chunk_plain: Original chunk content
        query: Search query
        url: URL to fetch content from
        context: Page context (url, title, etc.)
        model: Name of the LLM model
        ollama_host: URL of the Ollama API

    Returns:
        Dictionary with alignment score, matching content, and explanation
    """

    source_content_html = await fetch_url_content(url)
    source_cleaned_content_md = extract_content(source_content_html)
    if source_cleaned_content_md is None or len(source_cleaned_content_md) < 10:
        logger.warning(f"Failed to extract content from {url}")
        return {
            "score": 0.0,
            "matching_content": None,
            "explanation": None
        }
    source_chunks_md = chunk_markdown(source_cleaned_content_md)
    source_chunks_plain = [
        extract_complete_sentences(markdown_to_plain_text(each_chunk))
        for each_chunk in source_chunks_md
        if len(each_chunk) > 250
    ]

    keywords = query.split()
    # todo: use keywords to filter relevant chunks


    n = 3
    # relevant_chunks = retrieve_similar_chunks_embedding(original_chunk_plain, list(source_chunks_plain), n=n)
    relevant_chunks = retrieve_similar_chunks_smith(original_chunk_plain, list(source_chunks_plain), n=n)

    most_relevant_content, score = get_similarity_score(original_chunk_plain, relevant_chunks[:n])

    logger.info(f"=== Most relevant content ===\n{most_relevant_content}\n===")

    # use llm to generate explanation from original content, most relevant content, and score
    score_explanation = await compare_text_segments(
        original_chunk_plain,
        most_relevant_content,
        model=model,
        ollama_host=ollama_host
    )

    return {
        "score": score,
        "matching_content": most_relevant_content,
        "explanation": score_explanation
    }
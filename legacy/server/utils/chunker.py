"""
Text chunking utilities for semantic segmentation.
"""

from semantic_text_splitter import semantic_text_splitter
from loguru import logger

from server.utils.globals import NLP


def chunk_markdown(text: str, min_chunk_size: int = 250, max_chunk_size: int = 500) -> list[str]:
    """
    Chunk text into semantic segments.

    Args:
        text: Text to chunk
        min_chunk_size: Minimum characters per chunk
        max_chunk_size: Maximum characters per chunk

    Returns:
        List of chunk objects with IDs and content
    """
    splitter = semantic_text_splitter.MarkdownSplitter(max_chunk_size)
    chunks = splitter.chunks(text)

    return [
        chunk for i, chunk in enumerate(chunks)
        if len(chunk) >= min_chunk_size
    ]

def extract_complete_sentences(text: str) -> str:
    """
    Extract complete sentences from text.

    Args:
        text: Text to analyze

    Returns:
        String of complete sentences
    """
    doc = NLP(text)
    sentences = list()
    for each_sentence in doc.sentences:
        has_noun = any(word.upos in ['NOUN', 'PRON'] for word in each_sentence.words)
        has_verb = any(word.upos == 'VERB' for word in each_sentence.words)

        if has_noun and has_verb:
            sentences.append(each_sentence.text.strip())

    return " ".join(sentences)


def is_grammatical_text(text: str, min_sentences:int = 2) -> bool:
    """
    Uses Stanza's multilingual model to determine if text consists of grammatical sentences.

    Args:
        text (str): Text to analyze
        min_sentences (int): Minimum number of sentences required

    Returns:
        bool: True if text appears to consist of grammatical sentences
    """
    if not text or len(text.strip()) < 20:
        return False

    try:
    # Process the text
        doc = NLP(text)

        # Count complete sentences (with subject and predicate)
        complete_sentences = 0

        for sentence in doc.sentences:
            # Check if sentence has both noun/pronoun and verb
            has_noun = any(word.upos in ['NOUN', 'PRON'] for word in sentence.words)
            has_verb = any(word.upos == 'VERB' for word in sentence.words)

            if has_noun and has_verb:
                complete_sentences += 1

        return complete_sentences >= min_sentences

    except Exception as e:
        # If processing fails, likely not well-formed text
        logger.error(f"Error processing text with Stanza: {e}")
        return False
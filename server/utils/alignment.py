"""
Semantic alignment calculation utilities.
"""

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch


def calculate_semantic_alignment(premise: str, hypothesis: str) -> float:
    """
    Calculate the semantic alignment between two texts using a pre-trained model.

    Args:
        premise: Source text segment
        hypothesis: Original text segment

    Returns:
        Semantic alignment score
    """

    model_name = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)

    inputs = tokenizer.encode_plus(
        premise, hypothesis, return_tensors="pt", truncation=True)

    with torch.no_grad():
        logits = model(**inputs).logits

    probs = torch.softmax(logits, dim=1)[0].tolist()

    total_prob = sum(probs)
    normalized_probs = [prob / total_prob for prob in probs]
    return normalized_probs[0] - normalized_probs[2]


def find_best_matching_segment(original: str, comparison: str) -> tuple[float, str | None]:
    """
    Find the best matching segment between original and comparison texts.

    Args:
        original: Original text
        comparison: Text to compare with

    Returns:
        Tuple of (similarity_score, matching_segment)
    """
    pass


def extract_sentences(text: str) -> list[str]:
    """
    Extract sentences from text.

    Args:
        text: Text to process

    Returns:
        List of sentences
    """
    pass


def normalize_score(score: float) -> float:
    """
    Normalize a similarity score to 0-1 range with a curve.

    Args:
        score: Raw similarity score

    Returns:
        Normalized score between 0 and 1
    """
    pass
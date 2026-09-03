"""
BankSathi — NLP Package

Exposes text normalization, language detection, financial entity preservation,
and intent classification for Indian conversational banking queries.
"""

from nlp.language import detect_language
from nlp.preprocessing import (
    extract_preserved_financials,
    normalize_text,
    preprocess_query,
    tokenize,
)

__all__ = [
    "detect_language",
    "extract_preserved_financials",
    "normalize_text",
    "preprocess_query",
    "tokenize",
    "IntentClassifier",
]


def __getattr__(name: str):
    if name == "IntentClassifier":
        from nlp.intent_classifier import IntentClassifier
        return IntentClassifier
    raise AttributeError(f"module 'nlp' has no attribute '{name}'")

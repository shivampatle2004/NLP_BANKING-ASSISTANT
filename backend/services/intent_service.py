"""
BankSathi — Intent Service

Provides in-memory caching and singleton lifecycle management for the
BankSathi Intent Classifier within the FastAPI backend.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from nlp.intent_classifier import (
    DEFAULT_META_PATH,
    DEFAULT_MODEL_PATH,
    IntentClassifier,
)

# In-memory singleton instance
_intent_classifier: Optional[IntentClassifier] = None


def get_intent_classifier() -> IntentClassifier:
    """
    Get or initialize the shared IntentClassifier singleton.

    If a saved model exists on disk, it is loaded; otherwise it is trained
    on-the-fly and cached.
    """
    global _intent_classifier
    if _intent_classifier is None:
        classifier = IntentClassifier()
        if Path(DEFAULT_MODEL_PATH).exists():
            classifier.load(model_path=DEFAULT_MODEL_PATH, meta_path=DEFAULT_META_PATH)
        else:
            classifier.train()
            classifier.save(model_path=DEFAULT_MODEL_PATH, meta_path=DEFAULT_META_PATH)
        _intent_classifier = classifier

    return _intent_classifier


def classify_intent(
    query: str,
    top_k: int = 3,
    threshold: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Classify a user query and return prediction results.

    Parameters
    ----------
    query : str
        User's natural language question.
    top_k : int
        Number of top ranking candidate intents to return.
    threshold : float, optional
        Custom confidence threshold override.

    Returns
    -------
    dict
        Structured classification result payload.
    """
    clf = get_intent_classifier()
    return clf.predict(query, top_k=top_k, threshold=threshold)


def get_intent_service_status() -> Dict[str, Any]:
    """Return runtime metadata for the intent classification service."""
    clf = get_intent_classifier()
    return {
        "status": "loaded" if clf.pipeline is not None else "uninitialized",
        "num_classes": len(clf.classes_),
        "classes": clf.classes_,
        "metadata": clf.metadata,
    }

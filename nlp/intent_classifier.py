"""
BankSathi — Intent Classification Module

Train, evaluate, serialize, and serve an explainable ML intent classification
pipeline for Indian conversational banking queries across 29 intents in English,
Hindi (Devanagari), and Hinglish.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.pipeline import Pipeline

from nlp.preprocessing import normalize_text, preprocess_query

# ---------------------------------------------------------------------------
# Project Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_PATH = PROJECT_ROOT / "evaluation" / "training_intents.json"
DEFAULT_TEST_PATH = PROJECT_ROOT / "evaluation" / "test_queries.json"
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "intent_classifier.joblib"
DEFAULT_META_PATH = PROJECT_ROOT / "models" / "intent_metadata.json"

# Default confidence threshold for out-of-domain / ambiguous queries
DEFAULT_CONFIDENCE_THRESHOLD = 0.25


class IntentClassifier:
    """
    Explainable ML Intent Classifier for banking queries.

    Uses domain-normalized text representations with TF-IDF vectorization
    and logistic regression to predict query intent and confidence.
    """

    def __init__(
        self,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        c_param: float = 10.0,
        max_iter: int = 1000,
        random_state: int = 42,
    ):
        self.confidence_threshold = confidence_threshold
        self.c_param = c_param
        self.max_iter = max_iter
        self.random_state = random_state

        self.pipeline: Optional[Pipeline] = None
        self.classes_: List[str] = []
        self.metadata: Dict[str, Any] = {}

    def _build_pipeline(self) -> Pipeline:
        """Construct the scikit-learn TF-IDF + LogisticRegression pipeline."""
        return Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        ngram_range=(1, 1),
                        sublinear_tf=True,
                        min_df=1,
                    ),
                ),
                (
                    "clf",
                    LogisticRegression(
                        C=self.c_param,
                        max_iter=self.max_iter,
                        random_state=self.random_state,
                    ),
                ),
            ]
        )

    def train(
        self,
        data_path: Path | str = DEFAULT_DATA_PATH,
    ) -> Dict[str, Any]:
        """
        Train the intent classification model from training JSON.

        Parameters
        ----------
        data_path : Path | str
            Path to training_intents.json.

        Returns
        -------
        dict
            Training summary statistics.
        """
        data_path = Path(data_path)
        if not data_path.exists():
            raise FileNotFoundError(f"Training data not found at {data_path}")

        with open(data_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        intents_data = raw_data.get("intents", [])
        if not intents_data:
            raise ValueError("No intents found in training data.")

        X_train: List[str] = []
        y_train: List[str] = []

        for item in intents_data:
            intent_label = item["intent"]
            for example in item.get("examples", []):
                norm_text = normalize_text(example)
                if norm_text:
                    X_train.append(norm_text)
                    y_train.append(intent_label)

        if not X_train:
            raise ValueError("Training dataset has no valid non-empty examples.")

        # Build and train pipeline
        self.pipeline = self._build_pipeline()
        self.pipeline.fit(X_train, y_train)
        self.classes_ = sorted(list(self.pipeline.classes_))

        self.metadata = {
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "data_source": str(data_path),
            "num_samples": len(X_train),
            "num_classes": len(self.classes_),
            "classes": self.classes_,
            "c_param": self.c_param,
            "sublinear_tf": True,
            "ngram_range": [1, 1],
            "confidence_threshold": self.confidence_threshold,
        }

        return self.metadata

    def save(
        self,
        model_path: Path | str = DEFAULT_MODEL_PATH,
        meta_path: Path | str = DEFAULT_META_PATH,
    ) -> None:
        """Serialize the trained pipeline and metadata."""
        if self.pipeline is None:
            raise RuntimeError("Cannot save model: Pipeline is not trained.")

        model_path = Path(model_path)
        meta_path = Path(meta_path)

        model_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.parent.mkdir(parents=True, exist_ok=True)

        joblib.dump(self.pipeline, model_path)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)

    def load(
        self,
        model_path: Path | str = DEFAULT_MODEL_PATH,
        meta_path: Path | str = DEFAULT_META_PATH,
    ) -> None:
        """Deserialize a trained pipeline and its metadata."""
        model_path = Path(model_path)
        meta_path = Path(meta_path)

        if not model_path.exists():
            raise FileNotFoundError(f"Model artifact not found at {model_path}")

        self.pipeline = joblib.load(model_path)
        self.classes_ = sorted(list(self.pipeline.classes_))

        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
                self.confidence_threshold = self.metadata.get(
                    "confidence_threshold", self.confidence_threshold
                )
        else:
            self.metadata = {
                "num_classes": len(self.classes_),
                "classes": self.classes_,
            }

    def predict_proba(self, text: str) -> Dict[str, float]:
        """Compute probability distribution across all intents."""
        if self.pipeline is None:
            raise RuntimeError("Model is not loaded or trained.")

        norm_text = normalize_text(text)
        if not norm_text:
            return {c: 0.0 for c in self.classes_}

        probs = self.pipeline.predict_proba([norm_text])[0]
        return {c: float(probs[i]) for i, c in enumerate(self.pipeline.classes_)}

    def predict(
        self,
        text: str,
        top_k: int = 3,
        threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Classify user query intent with confidence score and extracted entities.

        Parameters
        ----------
        text : str
            Raw user query in English, Hindi, or Hinglish.
        top_k : int
            Number of top intent candidates to return.
        threshold : float, optional
            Custom confidence threshold override.

        Returns
        -------
        dict
            Prediction payload with intent, confidence, top alternatives,
            fallback status, and NLP preprocessing details.
        """
        if self.pipeline is None:
            raise RuntimeError("Model is not loaded or trained.")

        active_threshold = threshold if threshold is not None else self.confidence_threshold

        # Run preprocessing
        prep = preprocess_query(text)
        norm_text = prep["normalized_query"]

        # Handle empty or whitespace input
        if not norm_text:
            return {
                "intent": "GENERAL_BANKING",
                "confidence": 0.0,
                "is_fallback": True,
                "top_intents": [],
                "language": prep["language"],
                "language_confidence": prep["language_confidence"],
                "preserved_financials": prep["preserved_financials"],
                "tokens": prep["tokens"],
                "raw_query": text,
                "normalized_query": "",
            }

        probs = self.pipeline.predict_proba([norm_text])[0]
        classes = list(self.pipeline.classes_)

        # Sort indices by probability descending
        sorted_indices = probs.argsort()[::-1]
        top_indices = sorted_indices[:top_k]

        top_intents = [
            {
                "intent": classes[i],
                "confidence": round(float(probs[i]), 4),
            }
            for i in top_indices
        ]

        top_prediction = top_intents[0]
        top_intent = top_prediction["intent"]
        confidence = top_prediction["confidence"]
        is_fallback = confidence < active_threshold

        return {
            "intent": top_intent,
            "confidence": confidence,
            "is_fallback": is_fallback,
            "top_intents": top_intents,
            "language": prep["language"],
            "language_confidence": prep["language_confidence"],
            "preserved_financials": prep["preserved_financials"],
            "tokens": prep["tokens"],
            "raw_query": text,
            "normalized_query": norm_text,
        }

    def predict_batch(
        self,
        texts: List[str],
        top_k: int = 3,
        threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Run batch predictions on multiple queries."""
        return [self.predict(t, top_k=top_k, threshold=threshold) for t in texts]

    def evaluate(
        self,
        test_path: Path | str = DEFAULT_TEST_PATH,
    ) -> Dict[str, Any]:
        """
        Evaluate model performance against held-out benchmark test cases.

        Parameters
        ----------
        test_path : Path | str
            Path to test_queries.json.

        Returns
        -------
        dict
            Evaluation metrics including Top-1 accuracy, Top-3 accuracy,
            and per-class classification report.
        """
        test_path = Path(test_path)
        if not test_path.exists():
            raise FileNotFoundError(f"Test dataset not found at {test_path}")

        with open(test_path, "r", encoding="utf-8") as f:
            test_data = json.load(f)

        test_cases = test_data.get("test_cases", [])
        if not test_cases:
            raise ValueError("No test cases found in test dataset.")

        y_true: List[str] = []
        y_pred: List[str] = []
        top1_hits = 0
        top3_hits = 0
        mismatches: List[Dict[str, Any]] = []

        for tc in test_cases:
            query = tc["query"]
            expected = tc["expected_intent"]
            res = self.predict(query, top_k=3)

            top_intent = res["intent"]
            top3_candidates = [item["intent"] for item in res["top_intents"]]

            y_true.append(expected)
            y_pred.append(top_intent)

            if top_intent == expected:
                top1_hits += 1
            else:
                mismatches.append(
                    {
                        "query": query,
                        "normalized": res["normalized_query"],
                        "expected": expected,
                        "predicted": top_intent,
                        "confidence": res["confidence"],
                        "top_intents": res["top_intents"],
                    }
                )

            if expected in top3_candidates:
                top3_hits += 1

        total = len(test_cases)
        top1_acc = round(top1_hits / total, 4)
        top3_acc = round(top3_hits / total, 4)

        report = classification_report(
            y_true,
            y_pred,
            output_dict=True,
            zero_division=0,
        )

        return {
            "total_queries": total,
            "top1_hits": top1_hits,
            "top1_accuracy": top1_acc,
            "top3_hits": top3_hits,
            "top3_accuracy": top3_acc,
            "num_mismatches": len(mismatches),
            "mismatches": mismatches,
            "classification_report": report,
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="BankSathi Intent Classifier CLI")
    parser.add_argument("--train", action="store_true", help="Train model from dataset")
    parser.add_argument("--eval", action="store_true", help="Evaluate model on test queries")
    parser.add_argument("--save", action="store_true", help="Save model to models directory")
    parser.add_argument("--predict", type=str, help="Predict intent for a given query")
    parser.add_argument("--data-path", type=str, default=str(DEFAULT_DATA_PATH))
    parser.add_argument("--test-path", type=str, default=str(DEFAULT_TEST_PATH))
    parser.add_argument("--model-path", type=str, default=str(DEFAULT_MODEL_PATH))

    args = parser.parse_args()

    classifier = IntentClassifier()

    if args.train:
        print(f"[BankSathi] Training intent classifier from {args.data_path}...")
        meta = classifier.train(data_path=args.data_path)
        print(f"[BankSathi] Training complete: {meta['num_samples']} samples, {meta['num_classes']} intents.")
        if args.save:
            classifier.save(model_path=args.model_path)
            print(f"[BankSathi] Model saved to {args.model_path}.")

    if args.eval:
        if classifier.pipeline is None:
            if Path(args.model_path).exists():
                print(f"[BankSathi] Loading model from {args.model_path}...")
                classifier.load(model_path=args.model_path)
            else:
                print("[BankSathi] No trained model in memory or file. Training first...")
                classifier.train(data_path=args.data_path)

        print(f"[BankSathi] Evaluating against {args.test_path}...")
        results = classifier.evaluate(test_path=args.test_path)
        print(f"Total Test Cases: {results['total_queries']}")
        print(f"Top-1 Accuracy:   {results['top1_accuracy']*100:.2f}% ({results['top1_hits']}/{results['total_queries']})")
        print(f"Top-3 Accuracy:   {results['top3_accuracy']*100:.2f}% ({results['top3_hits']}/{results['total_queries']})")
        print(f"Mismatches:       {results['num_mismatches']}")

    if args.predict:
        if classifier.pipeline is None:
            if Path(args.model_path).exists():
                classifier.load(model_path=args.model_path)
            else:
                classifier.train(data_path=args.data_path)

        res = classifier.predict(args.predict)
        print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

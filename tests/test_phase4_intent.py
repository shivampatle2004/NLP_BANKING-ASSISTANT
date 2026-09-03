"""
Phase 4 — Intent Classification Tests

Verifies:
  1. IntentClassifier train, save, and load lifecycle
  2. Prediction output schema and key fields
  3. Multilingual inference: English, Hindi, and Hinglish queries
  4. Preserved financial extraction alongside intent prediction
  5. Top-K probability distribution ordering
  6. Out-of-domain and gibberish fallback thresholding
  7. Held-out benchmark evaluation meets accuracy threshold (>= 88% Top-1, >= 93% Top-3)
  8. FastAPI backend endpoints: /api/intent/predict, /api/intent/status, and /health
"""

import tempfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import _load_knowledge, app
from backend.services.intent_service import get_intent_classifier
from nlp.intent_classifier import (
    DEFAULT_DATA_PATH,
    DEFAULT_TEST_PATH,
    IntentClassifier,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def classifier():
    """Shared trained classifier fixture."""
    clf = IntentClassifier()
    clf.train(data_path=DEFAULT_DATA_PATH)
    return clf


@pytest.fixture(autouse=True)
def init_backend():
    """Ensure backend state is warmed up before tests."""
    _load_knowledge()
    get_intent_classifier()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# 1. Model Lifecycle Tests
# ---------------------------------------------------------------------------

class TestModelLifecycle:
    """Test training, serialization, and deserialization of the model."""

    def test_training_metadata(self, classifier):
        assert classifier.metadata["num_classes"] == 29
        assert classifier.metadata["num_samples"] >= 200
        assert len(classifier.classes_) == 29
        assert "ZERO_BALANCE_ACCOUNT" in classifier.classes_
        assert "FIXED_DEPOSIT" in classifier.classes_
        assert "COMPLAINT" in classifier.classes_

    def test_save_and_load(self, classifier):
        with tempfile.TemporaryDirectory() as tmpdir:
            model_file = Path(tmpdir) / "model.joblib"
            meta_file = Path(tmpdir) / "meta.json"

            classifier.save(model_path=model_file, meta_path=meta_file)
            assert model_file.exists()
            assert meta_file.exists()

            new_clf = IntentClassifier()
            new_clf.load(model_path=model_file, meta_path=meta_file)
            assert len(new_clf.classes_) == 29

            pred = new_clf.predict("I need a zero balance account")
            assert pred["intent"] == "ZERO_BALANCE_ACCOUNT"


# ---------------------------------------------------------------------------
# 2. Prediction Schema & Multilingual Inference Tests
# ---------------------------------------------------------------------------

class TestIntentInference:
    """Test intent predictions across languages and response structure."""

    def test_prediction_payload_schema(self, classifier):
        res = classifier.predict("What is the interest rate on SBI fixed deposit?")
        assert "intent" in res
        assert "confidence" in res
        assert "is_fallback" in res
        assert "top_intents" in res
        assert "language" in res
        assert "language_confidence" in res
        assert "preserved_financials" in res
        assert "tokens" in res
        assert "raw_query" in res
        assert "normalized_query" in res

        assert res["intent"] == "FIXED_DEPOSIT"
        assert res["confidence"] > 0.3
        assert res["is_fallback"] is False
        assert len(res["top_intents"]) == 3

    def test_hindi_devanagari_query(self, classifier):
        query = "मुझे अपनी दुकान के लिए मुद्रा लोन चाहिए"
        res = classifier.predict(query)
        assert res["language"] == "HINDI"
        assert res["intent"] in ["BUSINESS_SCHEME", "BUSINESS_LOAN"]

    def test_hinglish_banking_query(self, classifier):
        query = "Mujhe zero balance khata kholna hai bina kisi charge ke"
        res = classifier.predict(query)
        assert res["language"] == "HINGLISH"
        assert res["intent"] == "ZERO_BALANCE_ACCOUNT"

    def test_atm_failure_query(self, classifier):
        query = "ATM se cash nahi nikla but account se paisa kat gaya"
        res = classifier.predict(query)
        assert res["intent"] == "ATM_TRANSACTION_PROBLEM"

    def test_fraud_safety_query(self, classifier):
        query = "Someone called and asked for my OTP saying bank account is blocked"
        res = classifier.predict(query)
        assert res["intent"] == "OTP_SAFETY"

    def test_financial_entities_preserved_in_prediction(self, classifier):
        query = "Calculate monthly installment for ₹5 lakh loan for 3 years at 11% interest"
        res = classifier.predict(query)
        assert res["intent"] == "EMI_CALCULATION"
        fin = res["preserved_financials"]
        assert fin["amount"] == 500000
        assert fin["tenure_years"] == 3
        assert fin["interest_rate"] == 11.0

        res2 = classifier.predict("I need urgent ₹5 lakh personal loan for medical hospital bills")
        assert res2["intent"] == "PERSONAL_LOAN"
        assert res2["preserved_financials"]["amount"] == 500000

    def test_top_k_candidates_ordering(self, classifier):
        res = classifier.predict("How to apply for education loan for college?", top_k=5)
        top_candidates = res["top_intents"]
        assert len(top_candidates) == 5
        # Ensure confidences are monotonically descending
        confidences = [c["confidence"] for c in top_candidates]
        assert confidences == sorted(confidences, reverse=True)
        assert res["intent"] == top_candidates[0]["intent"]

    def test_batch_prediction(self, classifier):
        queries = [
            "Tell me about Jan Dhan account",
            "Calculate EMI for 10 lakh loan",
        ]
        results = classifier.predict_batch(queries)
        assert len(results) == 2
        assert results[0]["intent"] == "ZERO_BALANCE_ACCOUNT"
        assert results[1]["intent"] == "EMI_CALCULATION"


# ---------------------------------------------------------------------------
# 3. Fallback and Edge Cases
# ---------------------------------------------------------------------------

class TestFallbackAndEdgeCases:
    """Test handling of empty, whitespace, and out-of-domain inputs."""

    def test_empty_string(self, classifier):
        res = classifier.predict("")
        assert res["is_fallback"] is True
        assert res["confidence"] == 0.0
        assert res["intent"] == "GENERAL_BANKING"

    def test_whitespace_only(self, classifier):
        res = classifier.predict("   \n\t  ")
        assert res["is_fallback"] is True
        assert res["confidence"] == 0.0

    def test_gibberish_query_fallback(self, classifier):
        query = "xyzqwerty asdfghjk zxcvbnm12345"
        res = classifier.predict(query, threshold=0.20)
        # Random gibberish with no banking vocabulary should trigger fallback
        assert res["is_fallback"] is True

    def test_predict_proba_distribution(self, classifier):
        probs = classifier.predict_proba("Kisan credit card apply karna hai")
        assert len(probs) == 29
        assert all(isinstance(v, float) for v in probs.values())
        assert sum(probs.values()) == pytest.approx(1.0, rel=1e-2)


# ---------------------------------------------------------------------------
# 4. Held-out Benchmark Accuracy Verification
# ---------------------------------------------------------------------------

class TestBenchmarkAccuracy:
    """Assert performance standards on evaluation/test_queries.json."""

    def test_test_queries_accuracy(self, classifier):
        results = classifier.evaluate(test_path=DEFAULT_TEST_PATH)
        assert results["total_queries"] == 45
        # Minimum acceptable standards for deployment
        assert results["top1_accuracy"] >= 0.88, f"Top-1 accuracy {results['top1_accuracy']} < 0.88"
        assert results["top3_accuracy"] >= 0.93, f"Top-3 accuracy {results['top3_accuracy']} < 0.93"
        assert results["num_mismatches"] <= 5


# ---------------------------------------------------------------------------
# 5. Backend HTTP Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
class TestBackendIntegration:
    """Test FastAPI integration with the intent service."""

    async def test_health_includes_intent_model(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "intent_model" in data
        assert data["intent_model"]["status"] == "loaded"
        assert data["intent_model"]["num_classes"] == 29

    async def test_intent_status_endpoint(self, client):
        response = await client.get("/api/intent/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "loaded"
        assert data["num_classes"] == 29
        assert "SAVINGS_ACCOUNT" in data["classes"]

    async def test_predict_endpoint_success(self, client):
        payload = {
            "query": "Beti ke liye Sukanya Samriddhi account kholna hai",
            "top_k": 3,
        }
        response = await client.post("/api/intent/predict", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] in ["WOMEN_SCHEME", "SAVINGS_ACCOUNT", "ZERO_BALANCE_ACCOUNT"]
        assert data["confidence"] > 0.0
        assert "is_fallback" in data
        assert len(data["top_intents"]) == 3
        assert data["language"] in ["HINGLISH", "HINDI"]

    async def test_predict_endpoint_empty_query_400(self, client):
        payload = {"query": "   "}
        response = await client.post("/api/intent/predict", json=payload)
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

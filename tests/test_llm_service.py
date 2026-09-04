"""
Tests for LLM Service & AI Grounding in BankSathi
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.llm_service import (
    get_llm_config,
    _get_grounding_context,
    generate_llm_response,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_llm_config():
    config = get_llm_config()
    assert "provider" in config
    assert "model" in config
    assert "url" in config
    assert isinstance(config["is_configured"], bool)


def test_grounding_context_build():
    context = _get_grounding_context("Compare SBI vs HDFC FD", ["sbi", "hdfc"])
    assert "State Bank of India" in context or "HDFC" in context
    assert "DICGC" in context
    assert "1930" in context


def test_llm_status_endpoint(client):
    response = client.get("/api/llm/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "provider" in data
    assert "model" in data


def test_intent_predict_with_ai_response(client):
    response = client.post(
        "/api/intent/predict",
        json={"query": "SBI 1 year FD rate kitna hai?", "top_k": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert "intent" in data
    assert "matched_banks" in data
    assert "ai_response" in data

"""
Bank API Endpoints Integration Tests

Verifies:
  1. GET /api/banks returns 8 banks with summary stats
  2. GET /api/banks/{bank_id} returns detailed bank profile
  3. GET /api/banks/invalid returns 404
  4. POST /api/banks/compare returns side-by-side matrix
  5. GET /api/rates/best returns ranked banks
  6. POST /api/intent/predict returns enriched bank response when bank names are present
"""

import pytest
from httpx import ASGITransport, AsyncClient
from backend.main import app, _load_knowledge
from backend.services.intent_service import get_intent_classifier


@pytest.fixture(autouse=True)
def init_app():
    _load_knowledge()
    get_intent_classifier()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_get_all_banks_api(client):
    response = await client.get("/api/banks")
    assert response.status_code == 200
    data = response.json()
    assert data["total_banks"] == 18
    assert len(data["banks"]) == 18
    bank_ids = [b["id"] for b in data["banks"]]
    assert "sbi" in bank_ids
    assert "hdfc" in bank_ids
    assert "union" in bank_ids
    assert "ausfb" in bank_ids


@pytest.mark.anyio
async def test_get_single_bank_api(client):
    response = await client.get("/api/banks/sbi")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "sbi"
    assert data["name"] == "State Bank of India"
    assert data["savings"]["minBalance"]["metro"] == 0


@pytest.mark.anyio
async def test_get_single_bank_not_found(client):
    response = await client.get("/api/banks/unknown_bank_xyz")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_compare_banks_api(client):
    payload = {
        "bank_ids": ["sbi", "hdfc", "icici"],
        "product_type": "all",
    }
    response = await client.post("/api/banks/compare", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_compared"] == 3
    assert len(data["banks"]) == 3
    assert data["banks"][0]["id"] == "sbi"


@pytest.mark.anyio
async def test_best_rates_api(client):
    response = await client.get("/api/rates/best?product=fd&senior_citizen=true")
    assert response.status_code == 200
    data = response.json()
    assert data["product"] == "fd"
    assert data["is_senior_citizen"] is True
    assert len(data["ranked_banks"]) == 18


@pytest.mark.anyio
async def test_intent_predict_with_bank_enrichment(client):
    payload = {
        "query": "What is the 1 year fixed deposit rate at SBI?",
        "top_k": 3,
    }
    response = await client.post("/api/intent/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "sbi" in data["matched_banks"]
    assert data["bank_response"] is not None
    assert data["bank_response"]["type"] == "bank_detail"
    assert "State Bank of India" in data["bank_response"]["title"]

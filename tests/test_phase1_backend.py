"""
Phase 1 — Backend Foundation Test

Verifies:
  1. FastAPI app starts correctly
  2. /health endpoint returns expected structure
  3. /api/knowledge/status returns loaded knowledge base info
  4. / root endpoint works
  5. Knowledge base loads 18 entries from data/banking-knowledge.json
"""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app, _load_knowledge


@pytest.fixture(autouse=True)
def load_kb():
    """Ensure the knowledge base is loaded before tests run.

    ASGITransport does not trigger lifespan events, so we call the
    loader directly to simulate the startup behaviour.
    """
    _load_knowledge()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_root(client):
    """Root endpoint should return a welcome message with docs link."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "BankSathi" in data["message"]
    assert data["docs"] == "/docs"
    assert data["health"] == "/health"


@pytest.mark.anyio
async def test_health(client):
    """Health endpoint should confirm service is OK with knowledge stats."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()

    # Required fields
    assert data["status"] == "ok"
    assert data["service"] == "BankSathi"
    assert data["version"] == "1.0.0"
    assert "timestamp" in data

    # Knowledge base info
    kb = data["knowledge_base"]
    assert kb["entries_loaded"] == 28
    assert kb["last_verified"] == "2026-09-04"


@pytest.mark.anyio
async def test_knowledge_status(client):
    """Knowledge status should list all categories and entry IDs."""
    response = await client.get("/api/knowledge/status")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "loaded"
    assert data["total_entries"] == 28

    # Check some expected categories exist
    cats = data["categories"]
    assert "Loan" in cats
    assert "Insurance" in cats
    assert "Pension" in cats

    # Check some expected IDs exist
    ids = data["entry_ids"]
    assert "pmjdy" in ids
    assert "education_loan" in ids
    assert "mudra" in ids
    assert "cyber_security" in ids

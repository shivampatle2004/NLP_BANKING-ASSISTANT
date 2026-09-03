"""
BankSathi — FastAPI Backend Application

An NLP-Based Conversational Banking Information and Decision Support Assistant.

This is the main entry point for the backend server.
Run with: uvicorn backend.main:app --reload --port 8000
"""

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.services.intent_service import (
    classify_intent,
    get_intent_classifier,
    get_intent_service_status,
)

# ---------------------------------------------------------------------------
# Resolve project paths
# ---------------------------------------------------------------------------

# backend/ is one level inside the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_PATH = PROJECT_ROOT / "data" / "banking-knowledge.json"

# ---------------------------------------------------------------------------
# In-memory knowledge store (loaded once at startup)
# ---------------------------------------------------------------------------

knowledge_store: dict = {}


def _load_knowledge():
    """Load the banking knowledge JSON into the in-memory store."""
    global knowledge_store
    if KNOWLEDGE_PATH.exists():
        with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as fh:
            knowledge_store = json.load(fh)
        entry_count = len(knowledge_store.get("entries", []))
        print(f"[BankSathi] Loaded {entry_count} knowledge entries from {KNOWLEDGE_PATH}")
    else:
        print(f"[BankSathi] WARNING: Knowledge file not found at {KNOWLEDGE_PATH}")
        knowledge_store = {"metadata": {}, "entries": []}


# ---------------------------------------------------------------------------
# Lifespan — runs on startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: load knowledge and warm up ML models on startup."""
    _load_knowledge()
    # Warm up intent classifier singleton
    clf = get_intent_classifier()
    print(f"[BankSathi] Intent classifier ready with {len(clf.classes_)} intents.")
    yield
    # Shutdown: nothing to clean up currently


# ---------------------------------------------------------------------------
# Application setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="BankSathi API",
    description=(
        "NLP-Based Conversational Banking Information "
        "and Decision Support Assistant"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: Allow the frontend (served from file:// or a local dev server)
# to call this backend. In production, restrict origins appropriately.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic Schemas for API Endpoints
# ---------------------------------------------------------------------------

class IntentCandidate(BaseModel):
    intent: str
    confidence: float


class IntentPredictRequest(BaseModel):
    query: str = Field(..., description="User query in English, Hindi, or Hinglish")
    top_k: int = Field(default=3, ge=1, le=10, description="Top candidates to return")
    threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for fallback detection",
    )


class IntentPredictResponse(BaseModel):
    intent: str
    confidence: float
    is_fallback: bool
    top_intents: List[IntentCandidate]
    language: str
    language_confidence: float
    preserved_financials: Dict[str, Any]
    tokens: List[str]
    raw_query: str
    normalized_query: str


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    """
    Basic health check.

    Returns service status, knowledge base stats, ML model readiness, and timestamp.
    """
    entries = knowledge_store.get("entries", [])
    metadata = knowledge_store.get("metadata", {})
    intent_status = get_intent_service_status()

    return {
        "status": "ok",
        "service": "BankSathi",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "knowledge_base": {
            "entries_loaded": len(entries),
            "last_verified": metadata.get("lastVerified", "unknown"),
        },
        "intent_model": {
            "status": intent_status["status"],
            "num_classes": intent_status["num_classes"],
        },
    }


# ---------------------------------------------------------------------------
# Knowledge status endpoint
# ---------------------------------------------------------------------------

@app.get("/api/knowledge/status")
async def knowledge_status():
    """
    Detailed knowledge base status.

    Returns entry count, categories, and metadata for developer inspection.
    """
    entries = knowledge_store.get("entries", [])
    metadata = knowledge_store.get("metadata", {})

    # Collect unique categories
    categories = {}
    for entry in entries:
        cat = entry.get("category", "Uncategorized")
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "status": "loaded" if entries else "empty",
        "title": metadata.get("title", ""),
        "disclaimer": metadata.get("disclaimer", ""),
        "last_verified": metadata.get("lastVerified", "unknown"),
        "total_entries": len(entries),
        "categories": categories,
        "entry_ids": [e.get("id") for e in entries],
    }


# ---------------------------------------------------------------------------
# Intent classification endpoints
# ---------------------------------------------------------------------------

@app.post("/api/intent/predict", response_model=IntentPredictResponse)
async def predict_intent_endpoint(payload: IntentPredictRequest):
    """
    Predict banking intent for a conversational user query.

    Handles English, Hindi (Devanagari), and romanized Hinglish.
    Preserves financial numbers, rates, and entities alongside classified intent.
    """
    if not payload.query or not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    result = classify_intent(
        query=payload.query,
        top_k=payload.top_k,
        threshold=payload.threshold,
    )
    return result


@app.get("/api/intent/status")
async def intent_status_endpoint():
    """Returns runtime status and classes for the intent classification service."""
    return get_intent_service_status()


# ---------------------------------------------------------------------------
# Root redirect (developer convenience)
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    """Root endpoint — points developers to docs and health check."""
    return {
        "message": "BankSathi API is running",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "health": "/health",
            "knowledge_status": "/api/knowledge/status",
            "intent_predict": "/api/intent/predict",
            "intent_status": "/api/intent/status",
        },
    }


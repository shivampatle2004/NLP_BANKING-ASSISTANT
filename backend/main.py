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

from backend.services.bank_service import (
    compare_banks,
    generate_bank_conversational_response,
    get_all_banks,
    get_bank_by_id,
    get_best_rates,
    resolve_bank_ids_from_text,
)
from backend.services.intent_service import (
    classify_intent,
    get_intent_classifier,
    get_intent_service_status,
)
from backend.services.llm_service import (
    async_generate_llm_response,
    generate_llm_response,
    get_llm_config,
)

# ---------------------------------------------------------------------------
# Resolve project paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_PATH = PROJECT_ROOT / "data" / "banking-knowledge.json"
BANKS_PATH = PROJECT_ROOT / "data" / "banks-data.json"

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
    # Warm up intent classifier singleton & banks
    clf = get_intent_classifier()
    banks = get_all_banks()
    print(f"[BankSathi] Intent classifier ready with {len(clf.classes_)} intents.")
    print(f"[BankSathi] Bank intelligence ready with {len(banks)} major banks.")
    yield


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

# CORS: Allow frontend to communicate with backend
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
    matched_banks: List[str] = Field(default_factory=list)
    bank_response: Optional[Dict[str, Any]] = None
    ai_response: Optional[str] = Field(default=None, description="Generative AI response grounded in bank data")
    execution_mode: str = Field(default="offline_local", description="online_ai or offline_local")


class BankCompareRequest(BaseModel):
    bank_ids: List[str] = Field(default=["sbi", "hdfc", "icici"], description="Bank IDs to compare")
    product_type: str = Field(default="all", description="all, savings, fixed_deposit, loans, cards, support")


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    """
    Health check.
    Returns service status, knowledge base stats, bank data stats, and ML model status.
    """
    entries = knowledge_store.get("entries", [])
    metadata = knowledge_store.get("metadata", {})
    intent_status = get_intent_service_status()
    banks = get_all_banks()

    return {
        "status": "ok",
        "service": "BankSathi",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "knowledge_base": {
            "entries_loaded": len(entries),
            "last_verified": metadata.get("lastVerified", "unknown"),
        },
        "banks_database": {
            "total_banks": len(banks),
            "banks": [b.get("id") for b in banks],
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
    """Returns entry count, categories, and metadata for knowledge entries."""
    entries = knowledge_store.get("entries", [])
    metadata = knowledge_store.get("metadata", {})

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
# Bank Intelligence & Comparison Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/banks")
async def list_all_banks():
    """List all supported banks with their core details."""
    banks = get_all_banks()
    return {
        "status": "ok",
        "total_banks": len(banks),
        "banks": [
            {
                "id": b["id"],
                "name": b["name"],
                "shortName": b["shortName"],
                "type": b["type"],
                "headquarters": b["headquarters"],
                "tagline": b.get("tagline", ""),
                "logoColor": b.get("logoColor", "#1A4F8A"),
                "savingsRate": f"{b['savings']['interestRate']['upTo10Lakh']:.2f}%",
                "fd1YrRate": f"{b['fixedDeposit']['rate1Year']['general']:.2f}%",
                "homeLoanRate": f"{b['loans']['homeLoan']['startingRate']:.2f}%",
                "tollFree": b["customerSupport"]["tollFree"][0] if b["customerSupport"]["tollFree"] else "",
            }
            for b in banks
        ],
    }


@app.get("/api/banks/{bank_id}")
async def get_single_bank(bank_id: str):
    """Retrieve full profile, rate sheets, loan tiers, and contacts for a specific bank."""
    bank = get_bank_by_id(bank_id)
    if not bank:
        raise HTTPException(status_code=404, detail=f"Bank with ID '{bank_id}' not found.")
    return bank


@app.post("/api/banks/compare")
async def compare_banks_endpoint(payload: BankCompareRequest):
    """Compare multiple banks side-by-side across products."""
    result = compare_banks(bank_ids=payload.bank_ids, product_type=payload.product_type)
    return result


@app.get("/api/rates/best")
async def get_best_rates_endpoint(
    product: str = "fd",
    senior_citizen: bool = False,
):
    """
    Rank banks dynamically to highlight the best offers.
    Product: 'fd', 'savings', 'home_loan'
    """
    return get_best_rates(product=product, senior_citizen=senior_citizen)


# ---------------------------------------------------------------------------
# Intent classification endpoints
# ---------------------------------------------------------------------------

@app.post("/api/intent/predict", response_model=IntentPredictResponse)
async def predict_intent_endpoint(payload: IntentPredictRequest):
    """
    Predict banking intent for a conversational user query.
    Enriches prediction with matched bank entities and conversational bank answers.
    """
    if not payload.query or not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    result = classify_intent(
        query=payload.query,
        top_k=payload.top_k,
        threshold=payload.threshold,
    )

    # Detect any mentioned banks in query
    matched_banks = resolve_bank_ids_from_text(payload.query)
    bank_resp = generate_bank_conversational_response(
        query=payload.query,
        intent=result.get("intent", ""),
        bank_ids=matched_banks,
    )

    # If confidence is low and no domain handler caught it, mark as no_match_found
    if result.get("confidence", 0) < 0.20 and bank_resp is None:
        bank_resp = {
            "type": "no_match_found",
            "query": payload.query,
            "title": "No Direct Banking Match Found",
            "suggestions": [
                "Compare SBI vs HDFC FD rates",
                "Which bank offers the highest FD rate?",
                "Bank account opening age guidelines",
                "Best savings account with zero balance",
                "How to report ATM cash deduction issue",
            ]
        }

    # Generate generative AI grounded response (non-blocking async)
    ai_resp = await async_generate_llm_response(
        query=payload.query,
        intent=result.get("intent", "general_banking_query"),
        matched_banks=matched_banks,
        language=result.get("language", "en"),
    )

    # If AI responded, clear any no_match_found fallback
    if ai_resp and ai_resp.strip():
        if bank_resp and bank_resp.get("type") == "no_match_found":
            bank_resp = None

    result["matched_banks"] = matched_banks
    result["bank_response"] = bank_resp
    result["ai_response"] = ai_resp
    result["execution_mode"] = "online_ai" if (ai_resp and ai_resp.strip()) else "offline_local"
    return result


@app.get("/api/intent/status")
async def intent_status_endpoint():
    """Returns runtime status and classes for the intent classification service."""
    return get_intent_service_status()


@app.get("/api/llm/status")
async def llm_status_endpoint():
    """Returns LLM status and active model information."""
    config = get_llm_config()
    return {
        "status": "ready" if config["is_configured"] else "unconfigured",
        "provider": config["provider"],
        "model": config["model"],
        "is_configured": config["is_configured"],
    }


# ---------------------------------------------------------------------------
# Root redirect
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
            "banks_list": "/api/banks",
            "banks_compare": "/api/banks/compare",
            "rates_best": "/api/rates/best",
            "intent_predict": "/api/intent/predict",
            "intent_status": "/api/intent/status",
        },
    }


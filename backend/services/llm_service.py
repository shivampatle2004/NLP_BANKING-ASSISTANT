"""
BankSathi — LLM Intelligence Service (RAG Augmented Banking Assistant)

Supports Google Gemini, Groq, OpenRouter, OpenAI, and Ollama.
Grounds responses in verified Indian bank rate sheets and government schemes.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
BANKS_DATA_PATH = PROJECT_ROOT / "data" / "banks-data.json"
KNOWLEDGE_PATH = PROJECT_ROOT / "data" / "banking-knowledge.json"


def _load_env_file():
    """Load key-value pairs from .env into os.environ if not already present."""
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("\"'")
                    if k and k not in os.environ:
                        os.environ[k] = v


_load_env_file()

# Provider configuration presets
PROVIDER_ENDPOINTS = {
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "default_model": "gemini-3.5-flash-lite",
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "default_model": "llama-3.3-70b-versatile",
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "default_model": "meta-llama/llama-3.3-70b-instruct:free",
    },
    "openai": {
        "url": "https://api.openai.com/v1/chat/completions",
        "default_model": "gpt-4o-mini",
    },
    "ollama": {
        "url": "http://localhost:11434/v1/chat/completions",
        "default_model": "llama3",
    },
}


def get_llm_config() -> Dict[str, str]:
    """Retrieve current LLM provider configuration."""
    _load_env_file()
    provider = os.getenv("LLM_PROVIDER", "gemini").lower().strip()
    api_key = os.getenv("LLM_API_KEY", "").strip()
    preset = PROVIDER_ENDPOINTS.get(provider, PROVIDER_ENDPOINTS["gemini"])
    model = os.getenv("LLM_MODEL", preset["default_model"]).strip()
    url = preset["url"]
    return {
        "provider": provider,
        "api_key": api_key,
        "model": model,
        "url": url,
        "is_configured": bool(api_key or provider == "ollama"),
    }


def _get_grounding_context(query: str, matched_bank_ids: List[str]) -> str:
    """Retrieve verified rate sheets and scheme guidelines relevant to query."""
    context_parts = []

    # 1. Banks context
    if BANKS_DATA_PATH.exists():
        try:
            with open(BANKS_DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                banks = data.get("banks", [])
                
                # If specific banks matched, prioritize them; else summarize key major banks
                target_banks = [b for b in banks if b.get("id") in matched_bank_ids] if matched_bank_ids else banks[:5]
                
                bank_summaries = []
                for b in target_banks:
                    summary = (
                        f"• {b.get('name')} ({b.get('type')}): "
                        f"Savings Rate: {b.get('savings', {}).get('interestRate', {}).get('upTo10Lakh', 'N/A')}%, "
                        f"Min Balance (Metro): ₹{b.get('savings', {}).get('minimumBalance', {}).get('metro', 'N/A')}, "
                        f"1-Yr FD Rate: {b.get('fixedDeposit', {}).get('rate1Year', {}).get('general', 'N/A')}% "
                        f"(Senior Citizen: {b.get('fixedDeposit', {}).get('rate1Year', {}).get('seniorCitizen', 'N/A')}%), "
                        f"Home Loan Starting Rate: {b.get('loans', {}).get('homeLoan', {}).get('startingRate', 'N/A')}%, "
                        f"Personal Loan: {b.get('loans', {}).get('personalLoan', {}).get('startingRate', 'N/A')}%, "
                        f"Toll Free: {', '.join(b.get('customerSupport', {}).get('tollFree', []))}"
                    )
                    bank_summaries.append(summary)
                
                if bank_summaries:
                    context_parts.append("### Verified Bank Rates & Information:\n" + "\n".join(bank_summaries))
        except Exception as e:
            print(f"[LLMService] Error reading banks context: {e}")

    # 2. Curated Schemes & RBI Rules context
    if KNOWLEDGE_PATH.exists():
        try:
            with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
                kdata = json.load(f)
                entries = kdata.get("entries", [])
                q_lower = query.lower()
                
                matched_entries = []
                for e in entries:
                    title = e.get("title", "").lower()
                    cat = e.get("category", "").lower()
                    tags = " ".join(e.get("tags", [])).lower()
                    if any(word in q_lower for word in (title + " " + cat + " " + tags).split() if len(word) > 3):
                        matched_entries.append(
                            f"• Scheme: {e.get('title')} ({e.get('category')}): {e.get('summary', '')} "
                            f"Details: {json.dumps(e.get('details', {}))}"
                        )
                
                if matched_entries:
                    context_parts.append("### Government Schemes & Regulations:\n" + "\n".join(matched_entries[:3]))
        except Exception as e:
            print(f"[LLMService] Error reading knowledge context: {e}")

    # 3. Essential RBI Security Guardrails
    context_parts.append(
        "### Key Safety Facts:\n"
        "• DICGC Deposit Insurance: Deposits up to ₹5,00,000 (Principal + Interest) per depositor per bank are 100% insured.\n"
        "• National Cyber Crime Helpline: 1930 | Portal: cybercrime.gov.in\n"
        "• RBI Zero Liability Rule: If unauthorized electronic banking transaction is reported within 3 working days, customer has zero liability.\n"
        "• Never share OTP, UPI PIN, ATM PIN, or CVV with anyone including bank officials."
    )

    return "\n\n".join(context_parts)


def generate_llm_response(
    query: str,
    intent: str = "general_banking_query",
    matched_banks: Optional[List[str]] = None,
    language: str = "en",
    custom_api_key: Optional[str] = None,
) -> Optional[str]:
    """
    Generate an intelligent, grounded conversational response using configured LLM.
    Returns markdown-formatted response string, or None if service unavailable.
    """
    config = get_llm_config()
    api_key = custom_api_key.strip() if custom_api_key else config["api_key"]

    if not api_key and config["provider"] != "ollama":
        return None

    matched_bank_ids = matched_banks or []
    grounding_data = _get_grounding_context(query, matched_bank_ids)

    system_prompt = (
        "You are BankSathi (बैंक साथी) — an expert, polite, and explainable Indian Banking and Financial Assistant.\n"
        "Your mission is to provide 100% accurate, helpful, and transparent advice on banking, finance, schemes, and economy.\n\n"
        "GUIDELINES:\n"
        "1. ALL FINANCIAL & GENERAL QUERIES:\n"
        "   • Answer any query asked by the user — including Indian banks, global financial institutions (e.g. BlackRock, Vanguard, IMF, World Bank), "
        "mutual funds, stocks, RBI regulations, taxes, budgeting, credit scores, etc. Always give direct, informative, and insightful answers.\n"
        "2. COMPREHENSIVE BANKING & IFSC INTELLIGENCE:\n"
        "   • When users ask for IFSC codes, branch addresses, MICR codes, SWIFT codes, or branch information (e.g. 'Bank of India Hudkeshwar Road Nagpur IFSC', 'SBI Main Branch IFSC'):\n"
        "     - Provide the exact IFSC code (e.g. for Bank of India Hudkeshwar Road, Nagpur it is BKID0008745).\n"
        "     - Provide the branch address, district, state, pin code, and MICR code if known.\n"
        "     - Explain the IFSC structure (First 4 letters bank code e.g. BKID, 5th character '0', last 6 characters branch code).\n"
        "3. VERIFIED RATES & DATA GROUNDING: For interest rates (FD, Savings, Loans, EMIs) and government schemes, use the verified benchmarks provided below.\n"
        "4. LANGUAGE MATCHING: If the user queries in Hindi or romanized Hinglish (e.g., 'Mujhe loan chahiye', 'IFSC code kya hai'), "
        "reply in natural, warm Hinglish/Hindi with clear numbers. If they ask in English, reply in clean professional English.\n"
        "5. FORMATTING: Use markdown bolding for key codes, rates, and amounts, bullet points for comparisons, and short readable paragraphs.\n"
        "6. FRAUD SAFETY: For lost cards, fraud, or deductions, immediately provide emergency action steps and the 1930 Cyber helpline.\n\n"
        f"VERIFIED BANKING KNOWLEDGE BASE:\n{grounding_data}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": config["model"],
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 800,
    }

    # Resilient timeout: connect 3s, read 20s
    timeout_cfg = httpx.Timeout(connect=3.0, read=20.0, write=5.0, pool=3.0)

    try:
        with httpx.Client(timeout=timeout_cfg) as client:
            response = client.post(config["url"], headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                choices = data.get("choices", [])
                if choices and "message" in choices[0]:
                    return choices[0]["message"].get("content", "").strip()
            else:
                print(f"[LLMService] API returned {response.status_code}, falling back to local engine.")
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.NetworkError):
        print("[LLMService] No internet connection detected. Seamlessly using local bank engine.")
    except Exception as exc:
        print(f"[LLMService] LLM exception: {exc}, using local bank engine fallback.")

    return None


async def async_generate_llm_response(
    query: str,
    intent: str = "general_banking_query",
    matched_banks: Optional[List[str]] = None,
    language: str = "en",
    custom_api_key: Optional[str] = None,
) -> Optional[str]:
    """
    Asynchronous non-blocking LLM generation for FastAPI async routes.
    """
    config = get_llm_config()
    api_key = custom_api_key.strip() if custom_api_key else config["api_key"]

    if not api_key and config["provider"] != "ollama":
        return None

    matched_bank_ids = matched_banks or []
    grounding_data = _get_grounding_context(query, matched_bank_ids)

    system_prompt = (
        "You are BankSathi (बैंक साथी) — an expert, polite, and explainable Indian Banking and Financial Assistant.\n"
        "Your mission is to provide 100% accurate, helpful, and transparent advice on banking, finance, schemes, and economy.\n\n"
        "GUIDELINES:\n"
        "1. ALL FINANCIAL & GENERAL QUERIES:\n"
        "   • Answer any query asked by the user — including Indian banks, global financial institutions (e.g. BlackRock, Vanguard, IMF, World Bank), "
        "mutual funds, stocks, RBI regulations, taxes, budgeting, credit scores, etc. Always give direct, informative, and insightful answers.\n"
        "2. COMPREHENSIVE BANKING & IFSC INTELLIGENCE:\n"
        "   • When users ask for IFSC codes, branch addresses, MICR codes, SWIFT codes, or branch information (e.g. 'Bank of India Hudkeshwar Road Nagpur IFSC', 'SBI Main Branch IFSC'):\n"
        "     - Provide the exact IFSC code (e.g. for Bank of India Hudkeshwar Road, Nagpur it is BKID0008745).\n"
        "     - Provide the branch address, district, state, pin code, and MICR code if known.\n"
        "     - Explain the IFSC structure (First 4 letters bank code e.g. BKID, 5th character '0', last 6 characters branch code).\n"
        "3. VERIFIED RATES & DATA GROUNDING: For interest rates (FD, Savings, Loans, EMIs) and government schemes, use the verified benchmarks provided below.\n"
        "4. LANGUAGE MATCHING: If the user queries in Hindi or romanized Hinglish (e.g., 'Mujhe loan chahiye', 'IFSC code kya hai'), "
        "reply in natural, warm Hinglish/Hindi with clear numbers. If they ask in English, reply in clean professional English.\n"
        "5. FORMATTING: Use markdown bolding for key codes, rates, and amounts, bullet points for comparisons, and short readable paragraphs.\n"
        "6. FRAUD SAFETY: For lost cards, fraud, or deductions, immediately provide emergency action steps and the 1930 Cyber helpline.\n\n"
        f"VERIFIED BANKING KNOWLEDGE BASE:\n{grounding_data}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": config["model"],
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 800,
    }

    timeout_cfg = httpx.Timeout(connect=3.0, read=20.0, write=5.0, pool=3.0)

    try:
        async with httpx.AsyncClient(timeout=timeout_cfg) as client:
            response = await client.post(config["url"], headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                choices = data.get("choices", [])
                if choices and "message" in choices[0]:
                    return choices[0]["message"].get("content", "").strip()
            else:
                print(f"[LLMService] API returned {response.status_code}, falling back to local engine.")
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.NetworkError):
        print("[LLMService] No internet connection detected. Seamlessly using local bank engine.")
    except Exception as exc:
        print(f"[LLMService] LLM exception: {exc}, using local bank engine fallback.")

    return None

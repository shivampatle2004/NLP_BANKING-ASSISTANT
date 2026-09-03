"""
BankSathi — NLP Preprocessing Module

Provides explainable text preprocessing for Indian conversational banking queries:
  - Text normalization (case, whitespace, punctuation cleaning)
  - Financial number, currency, and tenure preservation
  - Banking abbreviation / acronym normalization
  - Hindi/Hinglish banking synonym normalization
  - Multi-word banking phrase canonicalization
  - Banking-specific tokenization

Controlled, domain-specific vocabulary tailored for Indian banking.
"""

import re
from typing import Dict, List, Any, Tuple
from nlp.language import detect_language


# ---------------------------------------------------------------------------
# Controlled Multi-Word Banking Phrase Mappings (Processed FIRST)
# ---------------------------------------------------------------------------
PHRASE_NORMALIZATION: List[Tuple[re.Pattern, str]] = [
    # Zero balance phrases
    (re.compile(r"\b(minimum\s+balance\s+nahi|zero\s+balance|no\s+minimum\s+balance|bina\s+balance|balance\s+maintain\s+nahi|जीरो\s+बैलेंस|बिना\s+बैलेंस)\b", re.IGNORECASE), "zero_minimum_balance"),
    
    # Loan requirement phrases
    (re.compile(r"\b(loan\s+chahiye|karz\s+chahiye|udhaar\s+chahiye|loan\s+lena\s+hai|paise\s+chahiye|लोन\s+चाहिए|कर्ज\s+चाहिए|उधार\s+चाहिए|ऋण\s+चाहिए)\b", re.IGNORECASE), "loan_required"),
    
    # Specific loan types in English/Hinglish/Devanagari
    (re.compile(r"\b(education\s+loan|padhai\s+(ke\s+liye\s+)?loan|study\s+loan|college\s+(ke\s+liye\s+)?loan|पढ़ाई\s+(के\s+लिए\s+)?लोन|शिक्षा\s+ऋण)\b", re.IGNORECASE), "education_loan"),
    (re.compile(r"\b(home\s+loan|ghar\s+(ke\s+liye\s+)?loan|makaan\s+(ke\s+liye\s+)?loan|house\s+loan|होम\s+लोन|घर\s+(के\s+लिए\s+)?लोन)\b", re.IGNORECASE), "home_loan"),
    (re.compile(r"\b(personal\s+loan|personal\s+kharch|पर्सनल\s+लोन)\b", re.IGNORECASE), "personal_loan"),
    (re.compile(r"\b(business\s+loan|karobar\s+(ke\s+liye\s+)?loan|vyapar\s+(ke\s+liye\s+)?loan|dukaan\s+(ke\s+liye\s+)?loan|दुकान\s+(के\s+लिए\s+)?लोन|व्यापार\s+(के\s+लिए\s+)?लोन)\b", re.IGNORECASE), "business_loan"),
    (re.compile(r"\b(agriculture\s+loan|kisan\s+loan|kheti\s+(ke\s+liye\s+)?loan|crop\s+loan|किसान\s+लोन|कृषि\s+ऋण)\b", re.IGNORECASE), "agriculture_loan"),
    
    # ATM / UPI problem phrases
    (re.compile(r"\b(paisa\s+kat\s+gaya|paise\s+kat\s+gaye|amount\s+debited|money\s+deducted|paisa\s+cut\s+gaya|पैसे\s+कट\s+गए|पैन\s+कट\s+गया)\b", re.IGNORECASE), "amount_debited"),
    (re.compile(r"\b(cash\s+nahi\s+nikla|paise\s+nahi\s+nikle|cash\s+not\s+dispensed|cash\s+nahi\s+mila|कैश\s+नहीं\s+निकला)\b", re.IGNORECASE), "cash_not_dispensed"),
    (re.compile(r"\b(upi\s+(failed|fail|error|phas\s+gaya|problem)|transaction\s+failed)\b", re.IGNORECASE), "upi_problem"),
    (re.compile(r"\b(unauthori[sz]ed\s+transaction|fraud\s+transaction|anadhikrit\s+len\s*den|धोखाधड़ी)\b", re.IGNORECASE), "unauthorized_transaction"),

    # Deposits & Savings
    (re.compile(r"\b(fixed\s+deposit|term\s+deposit|फिक्स्ड\s+डिपॉजिट)\b", re.IGNORECASE), "fixed_deposit"),
    (re.compile(r"\b(recurring\s+deposit|monthly\s+saving|रिकरिंग\s+डिपॉजिट)\b", re.IGNORECASE), "recurring_deposit"),
    (re.compile(r"\b(savings?\s+account|bachat\s+khata|बचत\s+खाता)\b", re.IGNORECASE), "savings_account"),
    (re.compile(r"\b(current\s+account|chalu\s+khata|चालू\s+खाता)\b", re.IGNORECASE), "current_account"),

    # Beneficiary profiles
    (re.compile(r"\b(small\s+shop|choti\s+dukaan|chhota\s+vyapar|small\s+business|छोटी\s+दुकान|छोटा\s+व्यापार)\b", re.IGNORECASE), "small_business"),
    (re.compile(r"\b(girl\s+child|beti\s+(ke\s+liye)?|kanya\s+(ke\s+liye)?|बेटी\s+(के\s+लिए)?|कन्या\s+(के\s+लिए)?)\b", re.IGNORECASE), "girl_child"),
    (re.compile(r"\b(senior\s+citizen|buzurg|vridhha?|वरिष्ठ\s+नागरिक|बुजुर्ग)\b", re.IGNORECASE), "senior_citizen"),
    (re.compile(r"\b(woman\s+entrepreneur|mahila\s+udyami|महिला\s+उद्यमी)\b", re.IGNORECASE), "woman_entrepreneur"),
]


# ---------------------------------------------------------------------------
# Controlled Banking Abbreviations & Acronyms
# ---------------------------------------------------------------------------
BANKING_ABBREVIATIONS: Dict[str, str] = {
    "fd": "fixed_deposit",
    "rd": "recurring_deposit",
    "kcc": "kisan_credit_card",
    "pmjdy": "pmjdy",
    "pmmy": "mudra",
    "apy": "atal_pension_yojana",
    "pmsby": "pmsby",
    "pmjjby": "pmjjby",
    "ppf": "public_provident_fund",
    "nps": "national_pension_system",
    "emi": "emi",
    "roi": "interest_rate",
    "kyc": "kyc",
    "otp": "otp",
    "pin": "pin",
    "cvv": "cvv",
    "atm": "atm",
    "upi": "upi",
    "dicgc": "deposit_insurance",
    "sbi": "sbi",
    "pnb": "pnb",
    "hdfc": "hdfc",
    "icici": "icici",
    "rbi": "rbi",
    "dbt": "direct_benefit_transfer",
}


# ---------------------------------------------------------------------------
# Controlled Single-Word Hindi/Hinglish Banking Term Mappings
# ---------------------------------------------------------------------------
SINGLE_WORD_SYNONYMS: Dict[str, str] = {
    # Business & Entrepreneurship
    "dukaan": "small_business",
    "dukan": "small_business",
    "shop": "small_business",
    "vyapar": "small_business",
    "karobar": "small_business",
    "startup": "small_business",
    "दुकान": "small_business",
    "व्यापार": "small_business",
    "कारोबार": "small_business",
    "मुद्रा": "mudra",

    # Education
    "padhai": "education",
    "shiksha": "education",
    "study": "education",
    "college": "education",
    "पढ़ाई": "education",
    "शिक्षा": "education",
    "कॉलेज": "education",

    # Agriculture
    "kheti": "agriculture",
    "krishi": "agriculture",
    "kisan": "farmer",
    "खेती": "agriculture",
    "कृषि": "agriculture",
    "किसान": "farmer",

    # Banking Accounts & Deposits
    "khata": "bank_account",
    "khate": "bank_account",
    "bachat": "savings",
    "nivesh": "investment",
    "खाता": "bank_account",
    "खाते": "bank_account",
    "बचत": "savings",
    "निवेश": "investment",

    # Loans & Credit
    "udhaar": "loan",
    "karz": "loan",
    "rin": "loan",
    "borrow": "loan",
    "लोन": "loan",
    "ऋण": "loan",
    "कर्ज": "loan",
    "उधार": "loan",

    # Interest & Insurance
    "byaj": "interest",
    "byaaj": "interest",
    "bima": "insurance",
    "suraksha": "protection",
    "ब्याज": "interest",
    "बीमा": "insurance",
    "सुरक्षा": "protection",

    # Pension & Retirement
    "pension": "pension",
    "retirement": "retirement",
    "budhapa": "pension",
    "पेंशन": "pension",
    "बुढ़ापा": "pension",

    # Fraud & Security
    "scam": "fraud",
    "dhoka": "fraud",
    "dhokhadhadi": "fraud",
    "hack": "fraud",
    "cyber": "cyber_security",
    "धोखाधड़ी": "fraud",
    "शिकायत": "complaint",

    # Profile words
    "beti": "girl_child",
    "kanya": "girl_child",
    "ladki": "girl_child",
    "mahila": "woman",
    "बेटी": "girl_child",
    "कन्या": "girl_child",
    "लड़की": "girl_child",
    "महिला": "woman",
}


# ---------------------------------------------------------------------------
# Financial Numbers and Amount Patterns
# ---------------------------------------------------------------------------
FINANCIAL_PATTERNS = {
    # e.g., ₹5 lakh, 5 lakhs, 5 lac, 5 lacs
    "lakh": re.compile(r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:lakhs?|lacs?)\b", re.IGNORECASE),
    # e.g., 1 crore, 2 cr
    "crore": re.compile(r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:crores?|cr)\b", re.IGNORECASE),
    # e.g., 10k, 50k
    "thousand_k": re.compile(r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*k\b", re.IGNORECASE),
    # e.g., ₹ 50,000 or ₹500000
    "raw_rupees": re.compile(r"(?:₹|rs\.?|inr)\s*(\d[\d,]+(?:\.\d+)?)", re.IGNORECASE),
    # e.g., 9%, 9.5%, 9 percent
    "percentage": re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|percent(?:age)?)(?!\w)", re.IGNORECASE),
    # e.g., 28 years old, age 28, 28 saal
    "age": re.compile(r"\b(?:age\s*[:=]?\s*(\d{1,2})|(\d{1,2})\s*(?:years?\s+old|saal(?:\s+ka|\s+ki)?))\b", re.IGNORECASE),
    # e.g., 5 years, 60 months, 5 saal, 2 varsh (excluding 'old')
    "tenure_years": re.compile(r"\b(\d+)\s*(?:years?|yrs?|saal|varsh)\b(?!\s*old)", re.IGNORECASE),
    "tenure_months": re.compile(r"\b(\d+)\s*(?:months?|mahine)\b", re.IGNORECASE),
}


def extract_preserved_financials(text: str) -> Dict[str, Any]:
    """
    Extract structured financial amounts, percentages, tenures, and age
    before general text filtering removes numbers.
    """
    results: Dict[str, Any] = {}

    # 1. Age (extract first so it doesn't get confused with loan tenure)
    age_match = FINANCIAL_PATTERNS["age"].search(text)
    if age_match:
        val = age_match.group(1) or age_match.group(2)
        try:
            results["age"] = int(val)
        except (ValueError, TypeError):
            pass

    # 2. Lakhs -> Rupee numeric value
    lakh_match = FINANCIAL_PATTERNS["lakh"].search(text)
    if lakh_match:
        val = float(lakh_match.group(1))
        results["amount"] = int(val * 100000)
        results["amount_display"] = f"₹{val:g} Lakh"

    # 3. Crores -> Rupee numeric value
    crore_match = FINANCIAL_PATTERNS["crore"].search(text)
    if crore_match:
        val = float(crore_match.group(1))
        results["amount"] = int(val * 10000000)
        results["amount_display"] = f"₹{val:g} Crore"

    # 4. K notation
    k_match = FINANCIAL_PATTERNS["thousand_k"].search(text)
    if k_match and "amount" not in results:
        val = float(k_match.group(1))
        results["amount"] = int(val * 1000)
        results["amount_display"] = f"₹{int(val * 1000)}"

    # 5. Standard rupee amount
    if "amount" not in results:
        rupee_match = FINANCIAL_PATTERNS["raw_rupees"].search(text)
        if rupee_match:
            clean_num = rupee_match.group(1).replace(",", "")
            try:
                results["amount"] = int(float(clean_num))
                results["amount_display"] = f"₹{clean_num}"
            except ValueError:
                pass

    # 6. Interest rate / Percentage
    pct_match = FINANCIAL_PATTERNS["percentage"].search(text)
    if pct_match:
        try:
            results["interest_rate"] = float(pct_match.group(1))
        except ValueError:
            pass

    # 7. Tenure (years/months)
    # Search for all tenure matches in case age matched 'years'
    for yr_match in FINANCIAL_PATTERNS["tenure_years"].finditer(text):
        matched_val = int(yr_match.group(1))
        # If this number was matched as age, skip it unless it appears in another context
        if "age" in results and matched_val == results["age"]:
            # Check if text around match contains 'old'
            span = yr_match.span()
            following_text = text[span[1]:span[1]+10].lower()
            if "old" in following_text:
                continue
        results["tenure_years"] = matched_val
        break

    mo_match = FINANCIAL_PATTERNS["tenure_months"].search(text)
    if mo_match and "tenure_years" not in results:
        try:
            months = int(mo_match.group(1))
            results["tenure_months"] = months
            results["tenure_years"] = round(months / 12, 1)
        except ValueError:
            pass

    return results


def normalize_text(text: str) -> str:
    """
    Normalize raw user input string:
      1. Lowercase
      2. Currency symbols to canonical markers
      3. Multi-word banking phrase normalization
      4. Banking abbreviation expansion
      5. Single-word Hindi/Hinglish synonym mapping
      6. Clean extra punctuation while keeping canonical words
    """
    if not text:
        return ""

    # 1. Lowercase and standard whitespace
    normalized = text.lower().strip()

    # 2. Currency symbol handling
    normalized = re.sub(r"(?:₹|rs\.?|inr)\s*", "rs ", normalized)

    # 3. Apply Multi-Word Phrase Normalization FIRST (longest match first)
    for pattern, replacement in PHRASE_NORMALIZATION:
        normalized = pattern.sub(f" {replacement} ", normalized)

    # 4. Remove unwanted punctuation, preserving letters, digits, and underscores
    normalized = re.sub(r"[^\w\s%₹]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    # 5. Token-by-token abbreviation and single-word synonym normalization
    tokens = normalized.split()
    processed_tokens: List[str] = []

    for token in tokens:
        # Check abbreviations
        if token in BANKING_ABBREVIATIONS:
            processed_tokens.append(BANKING_ABBREVIATIONS[token])
        # Check single-word domain synonyms
        elif token in SINGLE_WORD_SYNONYMS:
            processed_tokens.append(SINGLE_WORD_SYNONYMS[token])
        else:
            processed_tokens.append(token)

    return " ".join(processed_tokens)


def tokenize(text: str) -> List[str]:
    """
    Tokenize preprocessed text into meaningful banking terms.
    Preserves compound tokens like 'small_business', 'zero_minimum_balance'.
    """
    norm = normalize_text(text)
    if not norm:
        return []
    return [t for t in norm.split() if len(t) > 0]


def preprocess_query(text: str) -> Dict[str, Any]:
    """
    Complete end-to-end preprocessing pipeline for a user query.

    Returns structured representation:
      - raw_query
      - language: detected language info (ENGLISH, HINDI, HINGLISH)
      - normalized_query: canonical text string
      - tokens: list of preprocessed tokens
      - preserved_financials: extracted amounts, rates, tenures, ages
    """
    lang_info = detect_language(text)
    financials = extract_preserved_financials(text)
    normalized = normalize_text(text)
    tokens = tokenize(text)

    return {
        "raw_query": text,
        "language": lang_info["language"],
        "language_confidence": lang_info["confidence"],
        "normalized_query": normalized,
        "tokens": tokens,
        "preserved_financials": financials,
    }

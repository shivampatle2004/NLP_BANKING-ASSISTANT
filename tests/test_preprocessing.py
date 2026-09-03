"""
Phase 3 — NLP Preprocessing Tests

Verifies:
  1. Language detection: English, Hindi (Devanagari), Hinglish
  2. Single-word Hindi/Hinglish banking synonym normalization
  3. Multi-word phrase canonicalization (loan chahiye, minimum balance nahi, etc.)
  4. Banking abbreviations handling (FD, RD, KCC, APY, PMJDY, EMI, etc.)
  5. Financial number, currency, percentage, and tenure preservation
  6. Tokenization structure and edge cases
"""

import pytest
from nlp.language import detect_language
from nlp.preprocessing import (
    normalize_text,
    tokenize,
    preprocess_query,
    extract_preserved_financials,
)


# ---------------------------------------------------------------------------
# 1. Language Detection Tests
# ---------------------------------------------------------------------------
class TestLanguageDetection:
    """Test language detection accuracy for English, Hindi, and Hinglish."""

    def test_english_query(self):
        query = "What is the interest rate for a home loan at SBI?"
        res = detect_language(query)
        assert res["language"] == "ENGLISH"
        assert res["confidence"] >= 0.85

    def test_hindi_devanagari_query(self):
        query = "मुझे अपनी दुकान के लिए मुद्रा लोन चाहिए"
        res = detect_language(query)
        assert res["language"] == "HINDI"
        assert res["devanagari_ratio"] > 0.5

    def test_hinglish_banking_query_1(self):
        query = "Mujhe dukaan ke liye loan chahiye"
        res = detect_language(query)
        assert res["language"] == "HINGLISH"
        assert "chahiye" in res["hinglish_markers_found"]

    def test_hinglish_banking_query_2(self):
        query = "ATM se cash nahi nikla but account se paisa kat gaya"
        res = detect_language(query)
        assert res["language"] == "HINGLISH"
        assert "nahi" in res["hinglish_markers_found"]

    def test_hinglish_banking_query_3(self):
        query = "kisan bhaiyon ke liye kcc kaise apply karein"
        res = detect_language(query)
        assert res["language"] == "HINGLISH"

    def test_empty_query_default(self):
        res = detect_language("")
        assert res["language"] == "ENGLISH"


# ---------------------------------------------------------------------------
# 2. Banking Synonym Normalization Tests
# ---------------------------------------------------------------------------
class TestBankingSynonymNormalization:
    """Test normalization of Hindi/Hinglish domain words into canonical tokens."""

    def test_dukaan_to_small_business(self):
        norm = normalize_text("I have a dukaan in the market")
        assert "small_business" in norm

    def test_shop_to_small_business(self):
        norm = normalize_text("Need funds for my new shop")
        assert "small_business" in norm

    def test_padhai_to_education(self):
        norm = normalize_text("padhai ke liye loan lena hai")
        assert "education" in norm

    def test_kheti_to_agriculture(self):
        norm = normalize_text("kheti ke kharche ke liye loan")
        assert "agriculture" in norm

    def test_kisan_to_farmer(self):
        norm = normalize_text("kisan credit card details")
        assert "farmer" in norm

    def test_khata_to_bank_account(self):
        norm = normalize_text("naya khata kholna hai")
        assert "bank_account" in norm

    def test_bima_to_insurance(self):
        norm = normalize_text("pradhan mantri suraksha bima")
        assert "insurance" in norm


# ---------------------------------------------------------------------------
# 3. Multi-word Phrase Canonicalization Tests
# ---------------------------------------------------------------------------
class TestMultiWordPhraseNormalization:
    """Test multi-word compound banking expressions."""

    def test_loan_chahiye_to_loan_required(self):
        norm = normalize_text("mujhe 5 lakh loan chahiye")
        assert "loan_required" in norm

    def test_minimum_balance_nahi_to_zero_minimum_balance(self):
        norm = normalize_text("aisa account jisme minimum balance nahi ho")
        assert "zero_minimum_balance" in norm

    def test_zero_balance_phrase(self):
        norm = normalize_text("need a zero balance account")
        assert "zero_minimum_balance" in norm

    def test_atm_failure_phrases(self):
        norm = normalize_text("atm se cash nahi nikla but paisa kat gaya")
        assert "cash_not_dispensed" in norm
        assert "amount_debited" in norm

    def test_fixed_deposit_phrase(self):
        norm = normalize_text("what is the rate on fixed deposit")
        assert "fixed_deposit" in norm


# ---------------------------------------------------------------------------
# 4. Banking Abbreviations Tests
# ---------------------------------------------------------------------------
class TestBankingAbbreviations:
    """Test expanding banking acronyms into standard representations."""

    def test_fd_and_rd(self):
        norm = normalize_text("compare fd and rd")
        assert "fixed_deposit" in norm
        assert "recurring_deposit" in norm

    def test_kcc(self):
        norm = normalize_text("eligibility criteria for kcc")
        assert "kisan_credit_card" in norm

    def test_apy(self):
        norm = normalize_text("who can join apy scheme")
        assert "atal_pension_yojana" in norm

    def test_pmjdy(self):
        norm = normalize_text("benefits of pmjdy account")
        assert "pmjdy" in norm

    def test_emi_preserved(self):
        norm = normalize_text("calculate monthly emi")
        assert "emi" in norm

    def test_safety_acronyms_preserved(self):
        norm = normalize_text("never share otp pin cvv")
        assert "otp" in norm
        assert "pin" in norm
        assert "cvv" in norm


# ---------------------------------------------------------------------------
# 5. Financial Number and Entity Preservation Tests
# ---------------------------------------------------------------------------
class TestFinancialPreservation:
    """Test extraction of amounts, interest rates, tenures, and age."""

    def test_lakh_amount(self):
        res = extract_preserved_financials("I need ₹5 lakh for my business")
        assert res.get("amount") == 500000
        assert res.get("amount_display") == "₹5 Lakh"

    def test_lakhs_decimal(self):
        res = extract_preserved_financials("Loan of 2.5 lakhs needed")
        assert res.get("amount") == 250000

    def test_crore_amount(self):
        res = extract_preserved_financials("Home loan of ₹1 crore")
        assert res.get("amount") == 10000000

    def test_k_amount(self):
        res = extract_preserved_financials("Need 50k emergency loan")
        assert res.get("amount") == 50000

    def test_interest_rate_percentage(self):
        res = extract_preserved_financials("Loan at 9.5% annual interest")
        assert res.get("interest_rate") == 9.5

    def test_tenure_years(self):
        res = extract_preserved_financials("Repayment over 5 years")
        assert res.get("tenure_years") == 5

    def test_tenure_months(self):
        res = extract_preserved_financials("Tenure is 60 months")
        assert res.get("tenure_years") == 5.0
        assert res.get("tenure_months") == 60

    def test_age_extraction(self):
        res = extract_preserved_financials("I am 28 years old and want a shop loan")
        assert res.get("age") == 28


# ---------------------------------------------------------------------------
# 6. End-to-End Query Preprocessing Tests
# ---------------------------------------------------------------------------
class TestPreprocessQuery:
    """Test the complete preprocessing pipeline output structure."""

    def test_complex_hinglish_query(self):
        raw = "I am 28 years old, mujhe dukaan ke liye ₹5 lakh ka loan chahiye at 9% for 5 years"
        res = preprocess_query(raw)

        assert res["language"] == "HINGLISH"
        assert "small_business" in res["tokens"]
        assert "loan_required" in res["tokens"]

        fin = res["preserved_financials"]
        assert fin.get("amount") == 500000
        assert fin.get("age") == 28
        assert fin.get("interest_rate") == 9.0
        assert fin.get("tenure_years") == 5

    def test_zero_balance_query(self):
        raw = "Mujhe aisa account chahiye jisme minimum balance nahi rakhna pade"
        res = preprocess_query(raw)
        assert res["language"] == "HINGLISH"
        assert "zero_minimum_balance" in res["tokens"]

    def test_empty_string_handling(self):
        res = preprocess_query("")
        assert res["raw_query"] == ""
        assert res["normalized_query"] == ""
        assert res["tokens"] == []

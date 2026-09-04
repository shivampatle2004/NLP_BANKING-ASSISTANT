"""
Bank Intelligence & Comparison Tests

Verifies:
  1. Banks database loads all 8 banks
  2. Individual bank lookup works
  3. Bank entity resolution from conversational text
  4. Multi-bank side-by-side comparison across products (savings, fd, loans, cards, support)
  5. Best rates ranking for FD (General and Senior Citizens), Home Loans, and Savings MAB
  6. Conversational bank answer synthesis
"""

import pytest
from backend.services.bank_service import (
    get_all_banks,
    get_bank_by_id,
    resolve_bank_ids_from_text,
    compare_banks,
    get_best_rates,
    generate_bank_conversational_response,
)


class TestBankIntelligenceService:
    """Unit tests for Bank Intelligence and Comparison."""

    def test_get_all_banks_count(self):
        banks = get_all_banks()
        assert len(banks) == 18
        ids = [b["id"] for b in banks]
        assert "sbi" in ids
        assert "hdfc" in ids
        assert "icici" in ids
        assert "kotak" in ids
        assert "pnb" in ids
        assert "bob" in ids
        assert "axis" in ids
        assert "canara" in ids
        assert "union" in ids
        assert "ausfb" in ids
        assert "scb" in ids
        assert "ippb" in ids

    def test_get_bank_by_id_success(self):
        sbi = get_bank_by_id("sbi")
        assert sbi is not None
        assert sbi["name"] == "State Bank of India"
        assert sbi["savings"]["minBalance"]["metro"] == 0

    def test_get_bank_by_id_not_found(self):
        unknown = get_bank_by_id("non_existent_bank")
        assert unknown is None

    def test_resolve_bank_ids_from_text(self):
        # Single bank
        assert resolve_bank_ids_from_text("What is SBI FD rate?") == ["sbi"]
        # Multi bank
        ids = resolve_bank_ids_from_text("Compare HDFC vs ICICI home loan interest")
        assert "hdfc" in ids
        assert "icici" in ids
        # Aliases
        assert "kotak" in resolve_bank_ids_from_text("I want a kotak 811 account")
        assert "bob" in resolve_bank_ids_from_text("Bank of Baroda personal loan")
        assert "pnb" in resolve_bank_ids_from_text("Punjab National Bank branch")

    def test_compare_banks_matrix(self):
        res = compare_banks(["sbi", "hdfc"], product_type="all")
        assert res["total_compared"] == 2
        b_sbi = res["banks"][0]
        assert "savings" in b_sbi
        assert "fixedDeposit" in b_sbi
        assert "loans" in b_sbi
        assert "cardsAndAtm" in b_sbi
        assert "customerSupport" in b_sbi

    def test_best_rates_fd_general_and_senior(self):
        general_res = get_best_rates("fd", senior_citizen=False)
        assert len(general_res["ranked_banks"]) == 18
        # Ensure rates are in descending order
        rates = [b["peak_rate"] for b in general_res["ranked_banks"]]
        assert rates == sorted(rates, reverse=True)

        senior_res = get_best_rates("fd", senior_citizen=True)
        assert senior_res["is_senior_citizen"] is True
        sen_rates = [b["peak_rate"] for b in senior_res["ranked_banks"]]
        assert sen_rates == sorted(sen_rates, reverse=True)
        # Senior rates should be >= general rates
        assert senior_res["ranked_banks"][0]["peak_rate"] >= general_res["ranked_banks"][0]["peak_rate"]

    def test_best_rates_home_loan(self):
        res = get_best_rates("home_loan")
        assert len(res["ranked_banks"]) == 18
        # Loans should be in ascending order (lowest starting rate first)
        rates = [b["starting_rate"] for b in res["ranked_banks"]]
        assert rates == sorted(rates)

    def test_best_rates_savings(self):
        res = get_best_rates("savings")
        assert len(res["ranked_banks"]) == 18
        # Lowest minimum balance first (SBI is 0)
        assert res["ranked_banks"][0]["metro_min_balance"] == 0

    def test_conversational_synthesis(self):
        resp = generate_bank_conversational_response("Compare SBI vs HDFC", "BANK_COMPARISON", ["sbi", "hdfc"])
        assert resp is not None
        assert resp["type"] == "bank_comparison"
        assert "SBI" in resp["title"]
        assert "HDFC" in resp["title"]

"""
BankSathi — Bank Intelligence Database Validator

Validates `data/banks-data.json` against structural rules, realistic numerical bounds,
telecom formats, and valid HTTP/HTTPS URLs.
"""

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BANKS_PATH = PROJECT_ROOT / "data" / "banks-data.json"

URL_REGEX = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)
PHONE_REGEX = re.compile(r"^[0-9\s\-+()]{6,20}$")
DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class BankValidationIssue:
    severity: str  # "ERROR" | "WARNING"
    bank_id: Optional[str]
    field_name: str
    message: str

    def __str__(self) -> str:
        prefix = f"[{self.severity}]"
        bank_tag = f" Bank '{self.bank_id}' ->" if self.bank_id else ""
        return f"{prefix}{bank_tag} {self.field_name}: {self.message}"


@dataclass
class BankValidationReport:
    passed: bool
    total_banks: int
    valid_banks: int
    errors: List[BankValidationIssue] = field(default_factory=list)
    warnings: List[BankValidationIssue] = field(default_factory=list)
    bank_ids: List[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"BankSathi Bank Database Validation Report",
            f"{'='*50}",
            f"Status:        {'PASSED' if self.passed else 'FAILED'}",
            f"Total Banks:   {self.total_banks}",
            f"Valid Banks:   {self.valid_banks}",
            f"Errors:        {len(self.errors)}",
            f"Warnings:      {len(self.warnings)}",
            f"Banks:         {', '.join(self.bank_ids)}",
        ]
        if self.errors:
            lines.append("\nErrors:")
            for err in self.errors:
                lines.append(f"  - {err}")
        if self.warnings:
            lines.append("\nWarnings:")
            for warn in self.warnings:
                lines.append(f"  - {warn}")
        return "\n".join(lines)


def validate_banks_data(
    path: Path = DEFAULT_BANKS_PATH,
    strict: bool = False,
) -> BankValidationReport:
    """Validate data/banks-data.json."""
    errors: List[BankValidationIssue] = []
    warnings: List[BankValidationIssue] = []

    if not path.exists():
        errors.append(BankValidationIssue("ERROR", None, "file", f"File not found at {path}"))
        return BankValidationReport(False, 0, 0, errors, warnings)

    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        errors.append(BankValidationIssue("ERROR", None, "json", f"JSON parsing error: {exc}"))
        return BankValidationReport(False, 0, 0, errors, warnings)

    # Validate metadata
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        errors.append(BankValidationIssue("ERROR", None, "metadata", "Missing 'metadata' object."))
    else:
        for req_meta in ["title", "version", "lastVerified", "disclaimer"]:
            if not metadata.get(req_meta):
                errors.append(BankValidationIssue("ERROR", None, f"metadata.{req_meta}", f"Field '{req_meta}' is required in metadata."))
        if "lastVerified" in metadata and not DATE_REGEX.match(metadata["lastVerified"]):
            errors.append(BankValidationIssue("ERROR", None, "metadata.lastVerified", "Format must be YYYY-MM-DD."))

    banks = data.get("banks")
    if not isinstance(banks, list):
        errors.append(BankValidationIssue("ERROR", None, "banks", "Missing 'banks' array."))
        return BankValidationReport(False, 0, 0, errors, warnings)

    seen_ids = set()
    valid_count = 0
    bank_ids = []

    for idx, bank in enumerate(banks):
        bank_has_error = False
        bank_id = bank.get("id")

        if not bank_id or not isinstance(bank_id, str) or not bank_id.strip():
            errors.append(BankValidationIssue("ERROR", f"index_{idx}", "id", "Missing or empty 'id'."))
            bank_has_error = True
        elif bank_id in seen_ids:
            errors.append(BankValidationIssue("ERROR", bank_id, "id", f"Duplicate bank id '{bank_id}'."))
            bank_has_error = True
        else:
            seen_ids.add(bank_id)
            bank_ids.append(bank_id)

        # Basic identity
        for req in ["name", "shortName", "type", "headquarters"]:
            if not bank.get(req) or not isinstance(bank[req], str):
                errors.append(BankValidationIssue("ERROR", bank_id, req, f"Missing required string field '{req}'."))
                bank_has_error = True

        # Savings section
        savings = bank.get("savings", {})
        if not isinstance(savings, dict):
            errors.append(BankValidationIssue("ERROR", bank_id, "savings", "Missing 'savings' object."))
            bank_has_error = True
        else:
            min_bal = savings.get("minBalance", {})
            for tier in ["metro", "urban", "semiUrban", "rural"]:
                val = min_bal.get(tier)
                if val is None or not isinstance(val, (int, float)) or val < 0:
                    errors.append(BankValidationIssue("ERROR", bank_id, f"savings.minBalance.{tier}", f"Invalid minBalance value '{val}'."))
                    bank_has_error = True

            int_rates = savings.get("interestRate", {})
            for slab in ["upTo10Lakh", "above10Lakh"]:
                val = int_rates.get(slab)
                if val is None or not (1.0 <= val <= 10.0):
                    errors.append(BankValidationIssue("ERROR", bank_id, f"savings.interestRate.{slab}", f"Savings rate '{val}' out of expected bounds (1.0-10.0%)."))
                    bank_has_error = True

        # Fixed Deposit section
        fd = bank.get("fixedDeposit", {})
        if not isinstance(fd, dict):
            errors.append(BankValidationIssue("ERROR", bank_id, "fixedDeposit", "Missing 'fixedDeposit' object."))
            bank_has_error = True
        else:
            for rate_key in ["rate1Year", "rate3Year", "rate5Year"]:
                r_obj = fd.get(rate_key, {})
                gen_r = r_obj.get("general")
                sen_r = r_obj.get("seniorCitizen")
                if gen_r is None or not (4.0 <= gen_r <= 12.0):
                    errors.append(BankValidationIssue("ERROR", bank_id, f"fixedDeposit.{rate_key}.general", f"General rate '{gen_r}' out of bounds (4.0-12.0%)."))
                    bank_has_error = True
                if sen_r is None or not (4.0 <= sen_r <= 13.0):
                    errors.append(BankValidationIssue("ERROR", bank_id, f"fixedDeposit.{rate_key}.seniorCitizen", f"Senior citizen rate '{sen_r}' out of bounds."))
                    bank_has_error = True
                if gen_r is not None and sen_r is not None and sen_r < gen_r:
                    errors.append(BankValidationIssue("ERROR", bank_id, f"fixedDeposit.{rate_key}", "Senior citizen rate cannot be lower than general rate."))
                    bank_has_error = True

        # Loans section
        loans = bank.get("loans", {})
        if not isinstance(loans, dict):
            errors.append(BankValidationIssue("ERROR", bank_id, "loans", "Missing 'loans' object."))
            bank_has_error = True
        else:
            home = loans.get("homeLoan", {})
            home_rate = home.get("startingRate")
            if home_rate is None or not (5.0 <= home_rate <= 15.0):
                errors.append(BankValidationIssue("ERROR", bank_id, "loans.homeLoan.startingRate", f"Home loan starting rate '{home_rate}' out of bounds (5.0-15.0%)."))
                bank_has_error = True

        # Customer support section
        support = bank.get("customerSupport", {})
        if not isinstance(support, dict):
            errors.append(BankValidationIssue("ERROR", bank_id, "customerSupport", "Missing 'customerSupport' object."))
            bank_has_error = True
        else:
            toll_free = support.get("tollFree", [])
            if not toll_free or not isinstance(toll_free, list):
                errors.append(BankValidationIssue("ERROR", bank_id, "customerSupport.tollFree", "Must be a non-empty list of toll-free numbers."))
                bank_has_error = True

            for url_field in ["netBankingUrl", "officialWebsite"]:
                url_val = support.get(url_field, "")
                if not URL_REGEX.match(url_val):
                    errors.append(BankValidationIssue("ERROR", bank_id, f"customerSupport.{url_field}", f"Invalid URL '{url_val}'."))
                    bank_has_error = True

        if not bank_has_error:
            valid_count += 1

    if strict and warnings:
        for w in warnings:
            errors.append(BankValidationIssue("ERROR", w.bank_id, w.field_name, f"[Promoted from Warning] {w.message}"))
        warnings.clear()

    passed = len(errors) == 0
    return BankValidationReport(
        passed=passed,
        total_banks=len(banks) if isinstance(banks, list) else 0,
        valid_banks=valid_count,
        errors=errors,
        warnings=warnings,
        bank_ids=bank_ids,
    )


if __name__ == "__main__":
    report = validate_banks_data()
    print(report.summary())
    if not report.passed:
        sys.exit(1)

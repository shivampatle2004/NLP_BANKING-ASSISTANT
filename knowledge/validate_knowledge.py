"""
BankSathi — Knowledge Base Validator

Validates the banking knowledge JSON for:
  - JSON parse integrity
  - Required metadata fields
  - Required fields on every entry
  - Duplicate entry IDs
  - Valid source URLs (format only, not reachability)
  - Authority field presence
  - lastVerified date format (YYYY-MM-DD)
  - Category field presence
  - Benefits array non-empty
  - Tags array non-empty
  - Staleness check (entries older than 180 days)

Usage:
    python -m knowledge.validate_knowledge
    python -m knowledge.validate_knowledge --path data/banking-knowledge.json
    python -m knowledge.validate_knowledge --strict
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Project root (knowledge/ is one level inside the project)
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KNOWLEDGE_PATH = PROJECT_ROOT / "data" / "banking-knowledge.json"

# ---------------------------------------------------------------------------
# Validation schema
# ---------------------------------------------------------------------------

# Fields every entry MUST have
REQUIRED_ENTRY_FIELDS = [
    "id",
    "name",
    "category",
    "tags",
    "summary",
    "eligibility",
    "benefits",
    "source",
    "authority",
    "lastVerified",
]

# Fields the top-level metadata MUST have
REQUIRED_METADATA_FIELDS = [
    "title",
    "lastVerified",
    "disclaimer",
]

# Regex for basic URL validation (http or https)
URL_PATTERN = re.compile(r"^https?://[^\s]+$")

# Date format expected: YYYY-MM-DD
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Max age before a staleness warning (days)
STALENESS_THRESHOLD_DAYS = 180


# ---------------------------------------------------------------------------
# Validation result classes
# ---------------------------------------------------------------------------

class ValidationIssue:
    """A single validation finding."""

    def __init__(self, level: str, entry_id: str, field: str, message: str):
        self.level = level      # ERROR or WARNING
        self.entry_id = entry_id
        self.field = field
        self.message = message

    def __str__(self):
        prefix = f"[{self.level}]"
        location = f" entry='{self.entry_id}'" if self.entry_id else ""
        field = f" field='{self.field}'" if self.field else ""
        return f"{prefix}{location}{field}: {self.message}"


class ValidationReport:
    """Aggregated validation results."""

    def __init__(self, knowledge_path: str):
        self.knowledge_path = knowledge_path
        self.issues: list[ValidationIssue] = []
        self.total_entries = 0
        self.valid_entries = 0
        self.categories: dict[str, int] = {}

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "ERROR"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "WARNING"]

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, entry_id: str, field: str, message: str):
        self.issues.append(ValidationIssue("ERROR", entry_id, field, message))

    def add_warning(self, entry_id: str, field: str, message: str):
        self.issues.append(ValidationIssue("WARNING", entry_id, field, message))

    def summary_text(self) -> str:
        """Generate a human-readable validation summary."""
        lines = [
            "=" * 60,
            "BANKSATHI KNOWLEDGE BASE VALIDATION REPORT",
            "=" * 60,
            f"File:            {self.knowledge_path}",
            f"Total entries:   {self.total_entries}",
            f"Valid entries:   {self.valid_entries}",
            f"Errors:          {len(self.errors)}",
            f"Warnings:        {len(self.warnings)}",
            f"Result:          {'PASS' if self.passed else 'FAIL'}",
            "-" * 60,
        ]

        if self.categories:
            lines.append("Categories:")
            for cat, count in sorted(self.categories.items()):
                lines.append(f"  {cat}: {count}")
            lines.append("-" * 60)

        if self.issues:
            lines.append("Issues:")
            for issue in self.issues:
                lines.append(f"  {issue}")
            lines.append("-" * 60)
        else:
            lines.append("No issues found.")
            lines.append("-" * 60)

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core validation logic
# ---------------------------------------------------------------------------

def validate_knowledge(
    path: Path | str | None = None,
    strict: bool = False,
) -> ValidationReport:
    """
    Validate the banking knowledge JSON file.

    Parameters
    ----------
    path : Path or str, optional
        Path to the knowledge JSON. Defaults to data/banking-knowledge.json.
    strict : bool
        If True, treat warnings as errors.

    Returns
    -------
    ValidationReport
        The complete validation report.
    """
    path = Path(path) if path else DEFAULT_KNOWLEDGE_PATH
    report = ValidationReport(str(path))

    # ------------------------------------------------------------------
    # Step 1: File existence and JSON parsing
    # ------------------------------------------------------------------
    if not path.exists():
        report.add_error("", "file", f"Knowledge file not found: {path}")
        return report

    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as e:
        report.add_error("", "json", f"JSON parse error: {e}")
        return report

    # ------------------------------------------------------------------
    # Step 2: Top-level structure
    # ------------------------------------------------------------------
    if not isinstance(data, dict):
        report.add_error("", "structure", "Root must be a JSON object")
        return report

    # Metadata validation
    metadata = data.get("metadata")
    if not metadata:
        report.add_error("", "metadata", "Missing 'metadata' object")
    else:
        for field in REQUIRED_METADATA_FIELDS:
            if field not in metadata or not metadata[field]:
                report.add_error("", f"metadata.{field}", f"Missing required metadata field: {field}")

    # Entries array
    entries = data.get("entries")
    if entries is None:
        report.add_error("", "entries", "Missing 'entries' array")
        return report

    if not isinstance(entries, list):
        report.add_error("", "entries", "'entries' must be an array")
        return report

    report.total_entries = len(entries)

    if report.total_entries == 0:
        report.add_warning("", "entries", "Knowledge base is empty (0 entries)")
        return report

    # ------------------------------------------------------------------
    # Step 3: Per-entry validation
    # ------------------------------------------------------------------
    seen_ids: set[str] = set()
    today = datetime.now().date()

    for idx, entry in enumerate(entries):
        entry_id = entry.get("id", f"<index_{idx}>")
        entry_valid = True

        # --- Required fields ---
        for field in REQUIRED_ENTRY_FIELDS:
            if field not in entry:
                report.add_error(entry_id, field, f"Missing required field: {field}")
                entry_valid = False
            elif entry[field] is None or (isinstance(entry[field], str) and not entry[field].strip()):
                report.add_error(entry_id, field, f"Field is empty: {field}")
                entry_valid = False

        # --- Duplicate ID check ---
        if entry_id in seen_ids:
            report.add_error(entry_id, "id", f"Duplicate entry ID: '{entry_id}'")
            entry_valid = False
        seen_ids.add(entry_id)

        # --- Source URL format ---
        source = entry.get("source", "")
        if source and not URL_PATTERN.match(source):
            report.add_error(entry_id, "source", f"Invalid URL format: '{source}'")
            entry_valid = False

        # --- lastVerified date format ---
        last_verified = entry.get("lastVerified", "")
        if last_verified:
            if not DATE_PATTERN.match(last_verified):
                report.add_error(entry_id, "lastVerified", f"Invalid date format: '{last_verified}' (expected YYYY-MM-DD)")
                entry_valid = False
            else:
                # Check staleness
                try:
                    verified_date = datetime.strptime(last_verified, "%Y-%m-%d").date()
                    age_days = (today - verified_date).days
                    if age_days > STALENESS_THRESHOLD_DAYS:
                        report.add_warning(
                            entry_id, "lastVerified",
                            f"Entry is {age_days} days old (threshold: {STALENESS_THRESHOLD_DAYS} days)"
                        )
                except ValueError:
                    report.add_error(entry_id, "lastVerified", f"Cannot parse date: '{last_verified}'")
                    entry_valid = False

        # --- Tags array ---
        tags = entry.get("tags")
        if tags is not None:
            if not isinstance(tags, list):
                report.add_error(entry_id, "tags", "Tags must be an array")
                entry_valid = False
            elif len(tags) == 0:
                report.add_warning(entry_id, "tags", "Tags array is empty")

        # --- Benefits array ---
        benefits = entry.get("benefits")
        if benefits is not None:
            if not isinstance(benefits, list):
                report.add_error(entry_id, "benefits", "Benefits must be an array")
                entry_valid = False
            elif len(benefits) == 0:
                report.add_warning(entry_id, "benefits", "Benefits array is empty")

        # --- Category tracking ---
        category = entry.get("category", "Uncategorized")
        report.categories[category] = report.categories.get(category, 0) + 1

        # --- Summary length check ---
        summary = entry.get("summary", "")
        if summary and len(summary) < 20:
            report.add_warning(entry_id, "summary", f"Summary seems too short ({len(summary)} chars)")
        if summary and len(summary) > 500:
            report.add_warning(entry_id, "summary", f"Summary seems too long ({len(summary)} chars)")

        # --- Authority check ---
        authority = entry.get("authority", "")
        if authority and len(authority) < 3:
            report.add_warning(entry_id, "authority", f"Authority seems too short: '{authority}'")

        if entry_valid:
            report.valid_entries += 1

    # ------------------------------------------------------------------
    # Step 4: Strict mode — promote warnings to errors
    # ------------------------------------------------------------------
    if strict:
        for issue in report.issues:
            if issue.level == "WARNING":
                issue.level = "ERROR"

    return report


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="BankSathi Knowledge Base Validator"
    )
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help=f"Path to knowledge JSON (default: {DEFAULT_KNOWLEDGE_PATH})",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    report = validate_knowledge(path=args.path, strict=args.strict)

    if args.json_output:
        output = {
            "file": report.knowledge_path,
            "total_entries": report.total_entries,
            "valid_entries": report.valid_entries,
            "errors": len(report.errors),
            "warnings": len(report.warnings),
            "passed": report.passed,
            "categories": report.categories,
            "issues": [
                {
                    "level": i.level,
                    "entry_id": i.entry_id,
                    "field": i.field,
                    "message": i.message,
                }
                for i in report.issues
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        print(report.summary_text())

    sys.exit(0 if report.passed else 1)


if __name__ == "__main__":
    main()

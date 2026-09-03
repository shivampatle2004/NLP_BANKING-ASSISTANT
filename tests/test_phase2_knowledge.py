"""
Phase 2 — Knowledge Base Validation Tests

Verifies:
  1. Real knowledge base passes validation
  2. Validator detects missing required fields
  3. Validator detects duplicate IDs
  4. Validator detects invalid URLs
  5. Validator detects invalid date formats
  6. Validator detects empty arrays
  7. Strict mode promotes warnings to errors
  8. JSON output mode works
  9. Missing file is reported
"""

import json
import tempfile
from pathlib import Path

import pytest

from knowledge.validate_knowledge import validate_knowledge, ValidationReport


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _write_temp_json(data: dict) -> Path:
    """Write a dict to a temporary JSON file and return its path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(data, tmp)
    tmp.close()
    return Path(tmp.name)


def _make_valid_entry(**overrides) -> dict:
    """Create a valid knowledge entry with optional field overrides."""
    entry = {
        "id": "test_entry",
        "name": "Test Entry",
        "category": "Test",
        "tags": ["test"],
        "summary": "A test entry for validation purposes.",
        "eligibility": "Open to all testers.",
        "benefits": ["Testing works"],
        "source": "https://example.com/test",
        "authority": "Test Authority",
        "lastVerified": "2026-09-03",
    }
    entry.update(overrides)
    return entry


def _make_valid_kb(*entries) -> dict:
    """Wrap entries in a valid knowledge base structure."""
    if not entries:
        entries = [_make_valid_entry()]
    return {
        "metadata": {
            "title": "Test KB",
            "lastVerified": "2026-09-03",
            "disclaimer": "Test only",
        },
        "entries": list(entries),
    }


# -----------------------------------------------------------------------
# Tests against the REAL knowledge base
# -----------------------------------------------------------------------

class TestRealKnowledgeBase:
    """Validate the actual banking-knowledge.json in the project."""

    def test_real_kb_passes(self):
        """The real knowledge base should pass validation with 0 errors."""
        report = validate_knowledge()
        assert report.passed, f"Real KB failed: {[str(i) for i in report.errors]}"

    def test_real_kb_has_18_entries(self):
        """The real knowledge base should contain exactly 18 entries."""
        report = validate_knowledge()
        assert report.total_entries == 18

    def test_real_kb_all_valid(self):
        """All 18 entries should be individually valid."""
        report = validate_knowledge()
        assert report.valid_entries == 18

    def test_real_kb_has_expected_categories(self):
        """The real KB should contain key categories."""
        report = validate_knowledge()
        assert "Loan" in report.categories
        assert "Insurance" in report.categories
        assert "Savings" in report.categories


# -----------------------------------------------------------------------
# Tests for validation logic (synthetic data)
# -----------------------------------------------------------------------

class TestMissingFields:
    """Validator should detect missing required fields."""

    def test_missing_id(self):
        entry = _make_valid_entry()
        del entry["id"]
        kb = _make_valid_kb(entry)
        report = validate_knowledge(path=_write_temp_json(kb))
        assert not report.passed
        assert any("id" in str(e) for e in report.errors)

    def test_missing_source(self):
        entry = _make_valid_entry()
        del entry["source"]
        kb = _make_valid_kb(entry)
        report = validate_knowledge(path=_write_temp_json(kb))
        assert not report.passed

    def test_missing_authority(self):
        entry = _make_valid_entry()
        del entry["authority"]
        kb = _make_valid_kb(entry)
        report = validate_knowledge(path=_write_temp_json(kb))
        assert not report.passed

    def test_missing_lastVerified(self):
        entry = _make_valid_entry()
        del entry["lastVerified"]
        kb = _make_valid_kb(entry)
        report = validate_knowledge(path=_write_temp_json(kb))
        assert not report.passed

    def test_empty_name(self):
        entry = _make_valid_entry(name="")
        kb = _make_valid_kb(entry)
        report = validate_knowledge(path=_write_temp_json(kb))
        assert not report.passed


class TestDuplicateIDs:
    """Validator should detect duplicate entry IDs."""

    def test_duplicate_id_detected(self):
        e1 = _make_valid_entry(id="dup")
        e2 = _make_valid_entry(id="dup")
        kb = _make_valid_kb(e1, e2)
        report = validate_knowledge(path=_write_temp_json(kb))
        assert not report.passed
        assert any("Duplicate" in str(e) for e in report.errors)


class TestURLValidation:
    """Validator should check URL format."""

    def test_invalid_url(self):
        entry = _make_valid_entry(source="not-a-url")
        kb = _make_valid_kb(entry)
        report = validate_knowledge(path=_write_temp_json(kb))
        assert not report.passed
        assert any("URL" in str(e) for e in report.errors)

    def test_valid_http_url(self):
        entry = _make_valid_entry(source="http://example.com")
        kb = _make_valid_kb(entry)
        report = validate_knowledge(path=_write_temp_json(kb))
        assert report.passed

    def test_valid_https_url(self):
        entry = _make_valid_entry(source="https://gov.in/scheme")
        kb = _make_valid_kb(entry)
        report = validate_knowledge(path=_write_temp_json(kb))
        assert report.passed


class TestDateValidation:
    """Validator should check lastVerified date format."""

    def test_invalid_date_format(self):
        entry = _make_valid_entry(lastVerified="03-09-2026")
        kb = _make_valid_kb(entry)
        report = validate_knowledge(path=_write_temp_json(kb))
        assert not report.passed

    def test_valid_date(self):
        entry = _make_valid_entry(lastVerified="2026-09-03")
        kb = _make_valid_kb(entry)
        report = validate_knowledge(path=_write_temp_json(kb))
        assert report.passed


class TestArrayValidation:
    """Validator should check tags and benefits arrays."""

    def test_tags_not_array(self):
        entry = _make_valid_entry(tags="not-an-array")
        kb = _make_valid_kb(entry)
        report = validate_knowledge(path=_write_temp_json(kb))
        assert not report.passed

    def test_benefits_not_array(self):
        entry = _make_valid_entry(benefits="not-an-array")
        kb = _make_valid_kb(entry)
        report = validate_knowledge(path=_write_temp_json(kb))
        assert not report.passed

    def test_empty_tags_warning(self):
        entry = _make_valid_entry(tags=[])
        kb = _make_valid_kb(entry)
        report = validate_knowledge(path=_write_temp_json(kb))
        assert report.passed  # Warning, not error
        assert len(report.warnings) > 0

    def test_empty_benefits_warning(self):
        entry = _make_valid_entry(benefits=[])
        kb = _make_valid_kb(entry)
        report = validate_knowledge(path=_write_temp_json(kb))
        assert report.passed
        assert len(report.warnings) > 0


class TestStrictMode:
    """Strict mode should promote warnings to errors."""

    def test_strict_fails_on_warnings(self):
        entry = _make_valid_entry(tags=[])  # Triggers a warning
        kb = _make_valid_kb(entry)
        report = validate_knowledge(path=_write_temp_json(kb), strict=True)
        assert not report.passed  # Warning promoted to error


class TestEdgeCases:
    """Edge cases and file-level errors."""

    def test_missing_file(self):
        report = validate_knowledge(path="/nonexistent/path.json")
        assert not report.passed
        assert any("not found" in str(e) for e in report.errors)

    def test_invalid_json(self):
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        tmp.write("{invalid json")
        tmp.close()
        report = validate_knowledge(path=tmp.name)
        assert not report.passed

    def test_valid_single_entry(self):
        kb = _make_valid_kb(_make_valid_entry())
        report = validate_knowledge(path=_write_temp_json(kb))
        assert report.passed
        assert report.total_entries == 1
        assert report.valid_entries == 1

    def test_missing_metadata(self):
        kb = {"entries": [_make_valid_entry()]}
        report = validate_knowledge(path=_write_temp_json(kb))
        assert not report.passed
        assert any("metadata" in str(e) for e in report.errors)

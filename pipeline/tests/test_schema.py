"""
test_schema.py

1. schema.json loads without error and is valid JSON Schema Draft 2020-12
2. A handcrafted valid row produces zero errors
3. A handcrafted invalid row produces at least one error
"""

import json
from pathlib import Path

import jsonschema
import pytest

from catalog.schema import validate, _SCHEMA, _SCHEMA_PATH


def test_schema_file_exists():
    assert _SCHEMA_PATH.exists(), f"schema.json missing at {_SCHEMA_PATH}"


def test_schema_is_valid_json():
    with _SCHEMA_PATH.open(encoding="utf-8") as f:
        loaded = json.load(f)
    assert isinstance(loaded, dict)
    assert loaded.get("$schema") == "https://json-schema.org/draft/2020-12/schema"


def test_schema_passes_meta_validation():
    """The schema itself is valid according to Draft 2020-12 meta-schema."""
    meta_validator = jsonschema.Draft202012Validator
    meta_validator.check_schema(_SCHEMA)


def test_valid_row_passes(valid_row):
    errors = validate(valid_row)
    assert errors == [], f"Expected no errors, got: {errors}"


def test_valid_row_with_optional_fields():
    row = {
        "vendor": "test-vendor",
        "vendor_display_name": "Test Vendor",
        "category": "payments",
        "event_name": "invoice.payment_succeeded",
        "trigger_description": "Fires when an invoice payment is successfully processed.",
        "payload_schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "invoice_id": {"type": "string"},
                "amount": {"type": "integer"},
            },
        },
        "auth_method": "hmac-sha256",
        "signature_header": "Stripe-Signature",
        "docs_url": "https://docs.stripe.com/api/events/types",
        "last_introspected_at": "2026-05-13T12:00:00Z",
        "source_extractor_version": "v0.1",
        "extraction_method": "manual-html",
        "delivery_guarantees": "at-least-once",
        "retry_policy": {
            "max_attempts": 3,
            "backoff": "exponential",
            "total_retry_window": "PT24H",
        },
        "required_oauth_scopes": None,
        "extraction_confidence": None,
        "notes": "Test row.",
    }
    errors = validate(row)
    assert errors == [], f"Expected no errors, got: {errors}"


def test_invalid_row_missing_required_fields():
    row = {"vendor": "test-vendor"}
    errors = validate(row)
    required_fields = {
        "vendor_display_name", "category", "event_name",
        "trigger_description", "payload_schema", "auth_method",
        "docs_url", "last_introspected_at", "source_extractor_version",
        "extraction_method",
    }
    error_messages = " ".join(str(e) for e in errors)
    # There should be errors for each missing required field
    assert len(errors) > 0


def test_invalid_row_wrong_category(valid_row):
    valid_row["category"] = "not-a-real-category"
    errors = validate(valid_row)
    assert any("category" in str(e.json_path) or "not-a-real-category" in str(e) for e in errors)


def test_invalid_row_bad_vendor_slug(valid_row):
    valid_row["vendor"] = "Invalid Slug With Spaces"
    errors = validate(valid_row)
    assert len(errors) > 0


def test_invalid_row_bad_extractor_version(valid_row):
    valid_row["source_extractor_version"] = "not-a-version"
    errors = validate(valid_row)
    assert len(errors) > 0


def test_invalid_row_trigger_description_too_long(valid_row):
    valid_row["trigger_description"] = "x" * 501
    errors = validate(valid_row)
    assert len(errors) > 0


def test_invalid_row_payload_schema_missing_dollar_schema(valid_row):
    # payload_schema is required to have $schema field
    valid_row["payload_schema"] = {"type": "object"}
    errors = validate(valid_row)
    assert len(errors) > 0


def test_invalid_row_extra_property(valid_row):
    valid_row["unknown_field_xyz"] = "should fail"
    errors = validate(valid_row)
    assert len(errors) > 0

"""
Shared pytest fixtures.
"""

import pytest


# A minimal valid row that satisfies all required fields in schema.json
VALID_ROW = {
    "vendor": "test-vendor",
    "vendor_display_name": "Test Vendor",
    "category": "dev-tools",
    "event_name": "resource.created",
    "trigger_description": "Fired when a resource is created.",
    "payload_schema": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
    },
    "auth_method": "hmac-sha256",
    "docs_url": "https://example.com/docs/webhooks",
    "last_introspected_at": "2026-05-13T00:00:00Z",
    "source_extractor_version": "v0.1",
    "extraction_method": "manual-html",
}


@pytest.fixture
def valid_row() -> dict:
    return dict(VALID_ROW)

"""
example_stub.py — stub extractor showing the pattern for real extractors.

This is NOT a real vendor. It yields two hardcoded rows so the CLI
end-to-end (run --vendor example) works without hitting the network.

Sub 1.5 will add real tier-1 extractors following this same pattern:
  1. Subclass ExtractorBase
  2. Set slug (matches vendors.yaml) and docs_urls
  3. Implement extract() as an async generator
  4. Call register(MyExtractor) at module level
"""

from __future__ import annotations

from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher


class ExampleExtractor(ExtractorBase):
    slug = "example"
    docs_urls = ["https://example.com/docs/webhooks"]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        # A real extractor would call fetcher.get(url) and parse the response.
        # This stub yields two hardcoded rows matching schema.json.
        yield {
            "vendor": "example",
            "vendor_display_name": "Example Corp",
            "category": "dev-tools",
            "event_name": "object.created",
            "trigger_description": "Fired when a new object is created in the system.",
            "payload_schema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Unique identifier of the created object."},
                    "created_at": {"type": "string", "format": "date-time"},
                },
                "required": ["id", "created_at"],
            },
            "auth_method": "hmac-sha256",
            "signature_header": "X-Example-Signature",
            "docs_url": "https://example.com/docs/webhooks#object-created",
            "last_introspected_at": "2026-05-13T00:00:00Z",
            "source_extractor_version": "v0.1",
            "extraction_method": "manual-html",
            "delivery_guarantees": "at-least-once",
            "retry_policy": {
                "max_attempts": 5,
                "backoff": "exponential, capped at 24h",
                "total_retry_window": "PT72H",
            },
            "notes": "Stub row — not a real vendor.",
        }
        yield {
            "vendor": "example",
            "vendor_display_name": "Example Corp",
            "category": "dev-tools",
            "event_name": "object.deleted",
            "trigger_description": "Fired when an object is permanently deleted.",
            "payload_schema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Unique identifier of the deleted object."},
                    "deleted_at": {"type": "string", "format": "date-time"},
                },
                "required": ["id", "deleted_at"],
            },
            "auth_method": "hmac-sha256",
            "signature_header": "X-Example-Signature",
            "docs_url": "https://example.com/docs/webhooks#object-deleted",
            "last_introspected_at": "2026-05-13T00:00:00Z",
            "source_extractor_version": "v0.1",
            "extraction_method": "manual-html",
            "delivery_guarantees": "at-least-once",
            "notes": None,
        }


register(ExampleExtractor)

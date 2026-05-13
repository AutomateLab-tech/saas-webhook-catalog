"""
notion.py — Notion webhooks extractor.

Source: https://developers.notion.com/reference/webhooks
Small surface (~5 events confirmed from live docs).

Authentication: HMAC-SHA256, header X-Notion-Signature.
Signature is HMAC-SHA256 of the request body using the verification_token.

extraction_method: manual-html
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
_DOCS_URL = "https://developers.notion.com/reference/webhooks"

_EVENTS = [
    (
        "page.content_updated",
        "collaboration",
        "Fires when the content of a Notion page changes; deliveries may be aggregated (batched) when multiple edits happen in quick succession.",
        None,
    ),
    (
        "comment.created",
        "collaboration",
        "Fires when a new comment is added to a Notion page or database record; requires 'comment read' capability on the integration.",
        None,
    ),
    (
        "page.locked",
        "collaboration",
        "Fires when a Notion page is locked by a user, preventing further edits without unlocking.",
        None,
    ),
    (
        "data_source.schema_updated",
        "collaboration",
        "Fires when the schema of a linked Notion database is modified (added or removed properties); available from API version 2025-09-03.",
        None,
    ),
    (
        "database.schema_updated",
        "collaboration",
        "Fires when a Notion database schema changes. Deprecated after API version 2022-06-28; replaced by data_source.schema_updated for newer API versions.",
        "DEPRECATED: replaced by data_source.schema_updated for API versions after 2022-06-28. Retained for backward compatibility.",
    ),
]


def _payload_schema(event_name: str) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "description": "Event type identifier matching this row's event_name.",
            },
            "entity": {
                "type": "object",
                "description": "The Notion entity that triggered the event.",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "ID of the object (page, database, comment) that changed.",
                    },
                    "type": {
                        "type": "string",
                        "description": "Object type (e.g. 'page', 'database', 'comment').",
                    },
                },
                "required": ["id", "type"],
            },
            "workspace_id": {
                "type": "string",
                "description": "ID of the Notion workspace where the event occurred.",
            },
            "workspace_name": {
                "type": ["string", "null"],
                "description": "Display name of the Notion workspace.",
            },
            "subscription_id": {
                "type": "string",
                "description": "ID of the webhook subscription that received this event.",
            },
            "integration_id": {
                "type": "string",
                "description": "ID of the Notion integration (internal or public) that owns the subscription.",
            },
            "authors": {
                "type": "array",
                "description": "List of users or bots that authored the triggering change.",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "type": {"type": "string"},
                    },
                },
            },
            "timestamp": {
                "type": "string",
                "format": "date-time",
                "description": "ISO 8601 timestamp when the event was dispatched.",
            },
        },
        "required": ["type", "entity", "workspace_id", "subscription_id"],
    }


class NotionExtractor(ExtractorBase):
    slug = "notion"
    docs_urls = [_DOCS_URL]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, category, trigger_description, event_notes in _EVENTS:
            base_note = "Notion webhooks are currently in limited availability. The page.content_updated event uses aggregated delivery, meaning multiple rapid edits may be batched into a single event dispatch."
            notes = f"{event_notes} {base_note}" if event_notes else base_note
            yield {
                "vendor": "notion",
                "vendor_display_name": "Notion",
                "category": category,
                "event_name": event_name,
                "event_namespace": None,
                "trigger_description": trigger_description,
                "payload_schema": _payload_schema(event_name),
                "auth_method": "hmac-sha256",
                "signature_header": "X-Notion-Signature",
                "signature_algorithm_detail": "HMAC-SHA256 of the raw request body using the integration's verification_token as the signing key.",
                "docs_url": _DOCS_URL,
                "last_introspected_at": _TIMESTAMP,
                "source_extractor_version": "v1.0",
                "extraction_method": "manual-html",
                "delivery_guarantees": None,
                "retry_policy": None,
                "required_oauth_scopes": None,
                "notes": notes,
            }


register(NotionExtractor)

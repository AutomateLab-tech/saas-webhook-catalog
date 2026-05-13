"""
calendly.py — Calendly webhooks extractor.

Source: https://developer.calendly.com/api-docs/d7755e2f9e5fe-webhook-subscriptions
Small surface. Events confirmed from Calendly API reference and developer portal.

Calendly supports webhook subscriptions for scheduling events.
Auth: OAuth bearer token or personal access token; payload signing via X-Calendly-Webhook-Signature (HMAC-SHA256).

extraction_method: manual-html
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
_DOCS_URL = "https://developer.calendly.com/api-docs/d7755e2f9e5fe-webhook-subscriptions"

_EVENTS = [
    (
        "invitee.created",
        "Fires when someone books an appointment and becomes a Calendly invitee on a scheduled event.",
    ),
    (
        "invitee.canceled",
        "Fires when an invitee cancels an existing Calendly appointment.",
    ),
    (
        "invitee_no_show.created",
        "Fires when an invitee is marked as a no-show on a past event.",
    ),
    (
        "routing_form_submission.created",
        "Fires when a visitor submits a Calendly routing form response.",
    ),
]


def _payload_schema(event_name: str) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "event": {
                "type": "string",
                "description": "Event type identifier (e.g. 'invitee.created').",
            },
            "created_at": {
                "type": "string",
                "format": "date-time",
                "description": "ISO 8601 timestamp when this webhook was dispatched.",
            },
            "created_by": {
                "type": "string",
                "format": "uri",
                "description": "URI of the Calendly user or organization that owns the webhook subscription.",
            },
            "payload": {
                "type": "object",
                "description": "Event-specific data. Shape varies by event type.",
                "properties": {
                    "cancel_url": {
                        "type": ["string", "null"],
                        "format": "uri",
                        "description": "URL the invitee can use to cancel the appointment.",
                    },
                    "reschedule_url": {
                        "type": ["string", "null"],
                        "format": "uri",
                        "description": "URL the invitee can use to reschedule the appointment.",
                    },
                    "invitee": {
                        "type": "object",
                        "description": "Data about the invitee who booked or canceled.",
                        "properties": {
                            "uri": {"type": "string", "format": "uri"},
                            "email": {"type": "string", "format": "email"},
                            "name": {"type": "string"},
                            "first_name": {"type": ["string", "null"]},
                            "last_name": {"type": ["string", "null"]},
                            "status": {"type": "string", "enum": ["active", "canceled"]},
                        },
                    },
                    "event": {
                        "type": "object",
                        "description": "The scheduled Calendly event that the invitee relates to.",
                        "properties": {
                            "uri": {"type": "string", "format": "uri"},
                            "name": {"type": "string"},
                            "start_time": {"type": "string", "format": "date-time"},
                            "end_time": {"type": "string", "format": "date-time"},
                            "status": {"type": "string"},
                            "location": {"type": "object"},
                        },
                    },
                },
            },
        },
        "required": ["event", "created_at", "payload"],
    }


class CalendlyExtractor(ExtractorBase):
    slug = "calendly"
    docs_urls = [_DOCS_URL]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, trigger_description in _EVENTS:
            yield {
                "vendor": "calendly",
                "vendor_display_name": "Calendly",
                "category": "scheduling",
                "event_name": event_name,
                "event_namespace": None,
                "trigger_description": trigger_description,
                "payload_schema": _payload_schema(event_name),
                "auth_method": "hmac-sha256",
                "signature_header": "Calendly-Webhook-Signature",
                "signature_algorithm_detail": "HMAC-SHA256 of the raw request body; timestamp included in the signature header to prevent replay attacks.",
                "docs_url": _DOCS_URL,
                "last_introspected_at": _TIMESTAMP,
                "source_extractor_version": "v1.0",
                "extraction_method": "manual-html",
                "delivery_guarantees": None,
                "retry_policy": None,
                "required_oauth_scopes": ["default"],
                "notes": "Webhook subscriptions require OAuth or personal access token. Scope is limited to the user or organization that owns the subscription.",
            }


register(CalendlyExtractor)

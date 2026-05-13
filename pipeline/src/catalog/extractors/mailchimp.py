"""
mailchimp.py — Mailchimp webhook extractor (tier-2, llm-assisted).

Scope: Mailchimp Marketing API webhooks covering audience/list subscriber events.

Source: https://mailchimp.com/developer/marketing/guides/sync-audience-data-webhooks/

extraction_method: llm-assisted
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_DOCS_URL = "https://mailchimp.com/developer/marketing/guides/sync-audience-data-webhooks/"

def _mc_schema(event_type: str, data_props: dict, required_data_fields: list[str] | None = None) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "description": f"Event type identifier, e.g. '{event_type}'.",
            },
            "fired_at": {
                "type": "string",
                "description": "Datetime string (Y-m-d H:i:s) when the event was fired.",
            },
            "data": {
                "type": "object",
                "description": "Event-specific data payload.",
                "properties": data_props,
                "required": required_data_fields or [],
            },
        },
        "required": ["type", "fired_at", "data"],
    }

_SUBSCRIBER_DATA = {
    "id": {"type": "string", "description": "Mailchimp unique member ID (hashed email)."},
    "list_id": {"type": "string", "description": "Audience/list ID."},
    "email": {"type": "string", "description": "Subscriber's email address."},
    "email_type": {"type": "string", "description": "Email format preference (html or text)."},
    "ip_opt": {"type": ["string", "null"], "description": "IP address recorded at opt-in/out."},
    "ip_signup": {"type": ["string", "null"], "description": "IP address recorded at signup."},
    "web_id": {"type": "integer", "description": "Numeric web ID for this subscriber."},
    "merges": {
        "type": "object",
        "description": "Merge field values for the subscriber (e.g. FNAME, LNAME, plus custom fields).",
    },
}

_UNSUBSCRIBE_DATA = {
    **_SUBSCRIBER_DATA,
    "action": {"type": "string", "enum": ["unsub", "delete"], "description": "Whether the user unsubscribed or was deleted."},
    "reason": {"type": "string", "description": "Reason for the unsubscribe action."},
    "campaign_id": {"type": ["string", "null"], "description": "Campaign ID that prompted the unsubscribe, if applicable."},
}

_PROFILE_DATA = {
    **_SUBSCRIBER_DATA,
}

_CLEANED_DATA = {
    "list_id": {"type": "string", "description": "Audience/list ID."},
    "campaign_id": {"type": "string", "description": "Campaign that generated the bounce."},
    "reason": {"type": "string", "enum": ["hard", "abuse"], "description": "Reason for cleaning (hard bounce or abuse report)."},
    "email": {"type": "string", "description": "Cleaned email address."},
}

_CAMPAIGN_DATA = {
    "id": {"type": "string", "description": "Campaign ID."},
    "subject": {"type": "string", "description": "Campaign subject line."},
    "status": {"type": "string", "description": "Campaign status."},
    "reason": {"type": ["string", "null"], "description": "Reason for status change."},
    "list_id": {"type": "string", "description": "Audience/list ID the campaign was sent to."},
}

# (event_name, schema, trigger_description, confidence)
_EVENTS = [
    (
        "subscribe",
        _mc_schema("subscribe", _SUBSCRIBER_DATA, ["list_id", "email"]),
        "A contact subscribes to a Mailchimp audience, either via a signup form or API.",
        0.95,
    ),
    (
        "unsubscribe",
        _mc_schema("unsubscribe", _UNSUBSCRIBE_DATA, ["list_id", "email", "action"]),
        "A contact unsubscribes from an audience or is deleted from it.",
        0.95,
    ),
    (
        "profile",
        _mc_schema("profile", _PROFILE_DATA, ["list_id", "email"]),
        "A subscriber's profile data (merge fields, email preferences) is updated.",
        0.90,
    ),
    (
        "cleaned",
        _mc_schema("cleaned", _CLEANED_DATA, ["list_id", "email", "reason"]),
        "An email address is removed from an audience due to a hard bounce or abuse report.",
        0.90,
    ),
    (
        "upemail",
        _mc_schema("upemail", {
            "list_id": {"type": "string", "description": "Audience/list ID."},
            "new_id": {"type": "string", "description": "New subscriber ID after email change."},
            "new_email": {"type": "string", "description": "New email address."},
            "old_email": {"type": "string", "description": "Previous email address."},
        }, ["list_id", "new_email", "old_email"]),
        "A subscriber changes their email address on the audience.",
        0.90,
    ),
    (
        "campaign",
        _mc_schema("campaign", _CAMPAIGN_DATA, ["id", "status"]),
        "A campaign status changes (sent, canceled, paused, etc.).",
        0.85,
    ),
]


class MailchimpExtractor(ExtractorBase):
    slug = "mailchimp"
    docs_urls = [
        "https://mailchimp.com/developer/marketing/guides/sync-audience-data-webhooks/",
    ]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, payload_schema, trigger_description, confidence in _EVENTS:
            yield {
                "vendor": "mailchimp",
                "vendor_display_name": "Mailchimp",
                "category": "marketing",
                "event_name": event_name,
                "event_namespace": None,
                "trigger_description": trigger_description,
                "payload_schema": payload_schema,
                "required_oauth_scopes": None,
                "required_subscription_event": None,
                "auth_method": "none",
                "signature_header": None,
                "signature_algorithm_detail": (
                    "Mailchimp webhooks do not include a built-in signature header. "
                    "Authentication relies on a secret token embedded in the webhook callback URL."
                ),
                "retry_policy": {
                    "max_attempts": None,
                    "backoff": "Mailchimp retries failed webhook deliveries a limited number of times.",
                    "total_retry_window": None,
                },
                "max_payload_size_bytes": None,
                "idempotency_key_header": None,
                "event_id_header": None,
                "delivery_guarantees": "at-least-once",
                "delivery": None,
                "docs_url": _DOCS_URL,
                "last_introspected_at": _TIMESTAMP,
                "source_extractor_version": "v0.1.0",
                "extraction_method": "llm-assisted",
                "extraction_confidence": confidence,
                "notes": (
                    "Mailchimp webhooks deliver data as application/x-www-form-urlencoded POST "
                    "or JSON depending on configuration. fired_at uses 'Y-m-d H:i:s' format, not ISO 8601."
                ),
            }


register(MailchimpExtractor)

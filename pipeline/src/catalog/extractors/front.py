"""
front.py — Front webhook extractor (tier-2, llm-assisted).

Scope: Front platform webhook events for conversations, messages, contacts, and teammates.

Source: https://dev.frontapp.com/docs/webhooks-1

extraction_method: llm-assisted
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_DOCS_URL = "https://dev.frontapp.com/docs/webhooks-1"

def _front_schema(event_type: str, target_type: str, target_props: dict) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "_links": {
                "type": "object",
                "description": "HAL-style links for this event.",
                "properties": {
                    "self": {"type": "string", "description": "URL to this event resource."},
                },
            },
            "id": {"type": "string", "description": "Event ID."},
            "type": {"type": "string", "description": f"Event type: {event_type}."},
            "emitted_at": {"type": "number", "description": "Unix timestamp (seconds) when the event occurred."},
            "source": {
                "type": "object",
                "description": "The actor who triggered the event.",
                "properties": {
                    "_meta": {"type": "object", "description": "Metadata about the source."},
                    "data": {"type": "object", "description": "Source data (teammate or rule)."},
                },
            },
            "target": {
                "type": "object",
                "description": f"The {target_type} resource that was affected.",
                "properties": {
                    "_meta": {"type": "object", "properties": {"type": {"type": "string"}}},
                    "data": {
                        "type": "object",
                        "description": f"{target_type} data.",
                        "properties": target_props,
                    },
                },
            },
            "conversation": {
                "type": ["object", "null"],
                "description": "The conversation associated with this event, if applicable.",
                "properties": {
                    "id": {"type": "string", "description": "Conversation ID."},
                    "subject": {"type": "string", "description": "Conversation subject."},
                    "status": {"type": "string", "enum": ["assigned", "unassigned", "archived", "deleted"]},
                },
            },
        },
        "required": ["id", "type", "emitted_at"],
    }

_CONVERSATION_PROPS = {
    "id": {"type": "string", "description": "Conversation ID."},
    "subject": {"type": "string"},
    "status": {"type": "string", "enum": ["assigned", "unassigned", "archived", "deleted"]},
    "assignee": {"type": ["object", "null"], "description": "Assigned teammate."},
    "recipient": {"type": "object", "description": "Primary recipient of the conversation."},
    "tags": {"type": "array", "description": "Tags applied to the conversation."},
    "links": {"type": "array", "description": "External links attached."},
    "created_at": {"type": "number", "description": "Unix timestamp."},
    "is_private": {"type": "boolean"},
    "is_locked": {"type": "boolean"},
    "waiting_since": {"type": ["number", "null"]},
    "inbox": {"type": ["object", "null"], "description": "Inbox object."},
}

_MESSAGE_PROPS = {
    "id": {"type": "string", "description": "Message ID."},
    "type": {"type": "string", "description": "Message type (email, sms, tweet, etc.)."},
    "body": {"type": "string", "description": "Message body text (may be HTML)."},
    "subject": {"type": ["string", "null"]},
    "is_inbound": {"type": "boolean", "description": "True if the message was received (not sent by team)."},
    "created_at": {"type": "number"},
    "author": {"type": ["object", "null"], "description": "Message author (teammate or contact)."},
    "recipients": {"type": "array", "description": "Array of recipient objects."},
    "attachments": {"type": "array", "description": "Array of file attachments."},
}

_CONTACT_PROPS = {
    "id": {"type": "string", "description": "Contact ID."},
    "name": {"type": "string", "description": "Contact display name."},
    "description": {"type": ["string", "null"]},
    "avatar_url": {"type": ["string", "null"]},
    "is_spammer": {"type": "boolean"},
    "handles": {"type": "array", "description": "Contact handles (email, phone, etc.)."},
    "groups": {"type": "array", "description": "Contact groups."},
    "links": {"type": "array"},
    "custom_fields": {"type": "object", "description": "Custom field values."},
}

_TEAMMATE_PROPS = {
    "id": {"type": "string"},
    "email": {"type": "string"},
    "username": {"type": "string"},
    "first_name": {"type": ["string", "null"]},
    "last_name": {"type": ["string", "null"]},
    "is_available": {"type": "boolean"},
}

# (event_name, target_type, target_props, trigger_description, confidence)
_EVENTS = [
    ("conversation_created", "conversation", _CONVERSATION_PROPS,
     "A new conversation is created in a Front inbox.", 0.90),
    ("conversation_assigned", "conversation", _CONVERSATION_PROPS,
     "A conversation is assigned to a teammate.", 0.90),
    ("conversation_unassigned", "conversation", _CONVERSATION_PROPS,
     "A conversation's assignee is removed.", 0.85),
    ("conversation_tagged", "conversation", _CONVERSATION_PROPS,
     "A tag is added to a conversation.", 0.85),
    ("conversation_untagged", "conversation", _CONVERSATION_PROPS,
     "A tag is removed from a conversation.", 0.85),
    ("conversation_archived", "conversation", _CONVERSATION_PROPS,
     "A conversation is archived.", 0.90),
    ("conversation_unarchived", "conversation", _CONVERSATION_PROPS,
     "An archived conversation is reopened.", 0.85),
    ("conversation_deleted", "conversation", _CONVERSATION_PROPS,
     "A conversation is moved to trash.", 0.85),
    ("conversation_restored", "conversation", _CONVERSATION_PROPS,
     "A deleted conversation is restored.", 0.80),
    ("conversation_inbox_moved", "conversation", _CONVERSATION_PROPS,
     "A conversation is moved from one inbox to another.", 0.85),
    ("message_received", "message", _MESSAGE_PROPS,
     "A new inbound message is received in a conversation.", 0.90),
    ("message_sent", "message", _MESSAGE_PROPS,
     "An outbound message is sent from Front.", 0.90),
    ("message_imported", "message", _MESSAGE_PROPS,
     "A message is imported into Front via the API.", 0.80),
    ("message_autoreply_sent", "message", _MESSAGE_PROPS,
     "An automated reply is sent by a Front rule or auto-responder.", 0.80),
    ("contact_created", "contact", _CONTACT_PROPS,
     "A new contact record is created in Front.", 0.85),
    ("contact_updated", "contact", _CONTACT_PROPS,
     "A contact's information is updated.", 0.85),
    ("contact_deleted", "contact", _CONTACT_PROPS,
     "A contact is deleted.", 0.80),
    ("teammate_created", "teammate", _TEAMMATE_PROPS,
     "A new teammate is added to the Front workspace.", 0.80),
    ("teammate_updated", "teammate", _TEAMMATE_PROPS,
     "A teammate's profile or availability changes.", 0.80),
    ("tag_created", "tag", {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "highlight": {"type": ["string", "null"]},
        "is_private": {"type": "boolean"},
    }, "A new tag is created in the workspace.", 0.80),
]


class FrontExtractor(ExtractorBase):
    slug = "front"
    docs_urls = [
        "https://dev.frontapp.com/docs/webhooks-1",
    ]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, target_type, target_props, trigger_description, confidence in _EVENTS:
            yield {
                "vendor": "front",
                "vendor_display_name": "Front",
                "category": "support",
                "event_name": event_name,
                "event_namespace": None,
                "trigger_description": trigger_description,
                "payload_schema": _front_schema(event_name, target_type, target_props),
                "required_oauth_scopes": None,
                "required_subscription_event": None,
                "auth_method": "hmac-sha256",
                "signature_header": "X-Front-Signature",
                "signature_algorithm_detail": (
                    "Base64-encoded HMAC-SHA256 of the raw request body using the webhook's secret."
                ),
                "retry_policy": {
                    "max_attempts": None,
                    "backoff": "Front retries failed webhook deliveries.",
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
                "notes": None,
            }


register(FrontExtractor)

"""
help_scout.py — Help Scout webhook extractor (tier-2, llm-assisted).

Scope: Help Scout webhook events for conversations, emails, customers, and mailboxes.

Source: https://developer.helpscout.com/webhooks/

extraction_method: llm-assisted
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_DOCS_URL = "https://developer.helpscout.com/webhooks/"

def _hs_schema(event_type: str, object_props: dict, required_fields: list[str] | None = None) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "eventType": {"type": "string", "description": f"Event type identifier: {event_type}."},
            "createdAt": {"type": "string", "format": "date-time", "description": "ISO 8601 timestamp when the event was created."},
            "primaryKey": {"type": "integer", "description": "Primary key (ID) of the affected resource."},
            "object": {
                "type": "object",
                "description": "The affected resource object.",
                "properties": object_props,
                "required": required_fields or [],
            },
        },
        "required": ["eventType", "createdAt", "primaryKey"],
    }

_CONVERSATION_PROPS = {
    "id": {"type": "integer", "description": "Conversation ID."},
    "number": {"type": "integer", "description": "Conversation number (human-readable)."},
    "subject": {"type": "string"},
    "status": {"type": "string", "enum": ["active", "pending", "closed", "spam"]},
    "type": {"type": "string", "enum": ["email", "chat", "phone"]},
    "createdAt": {"type": "string", "format": "date-time"},
    "closedAt": {"type": ["string", "null"], "format": "date-time"},
    "userUpdatedAt": {"type": ["string", "null"], "format": "date-time"},
    "customer": {"type": "object", "description": "The primary customer in this conversation."},
    "assignee": {"type": ["object", "null"], "description": "The assigned Help Scout user."},
    "mailbox": {"type": "object", "description": "The mailbox this conversation belongs to."},
    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags applied to the conversation."},
    "threads": {"type": "array", "description": "Thread objects in this conversation."},
}

_THREAD_PROPS = {
    "id": {"type": "integer", "description": "Thread ID."},
    "type": {"type": "string", "enum": ["customer", "message", "lineitem", "note", "forwardparent", "forwardchild", "chat", "phone"]},
    "body": {"type": ["string", "null"], "description": "Thread body text (HTML)."},
    "status": {"type": "string"},
    "createdAt": {"type": "string", "format": "date-time"},
    "openedAt": {"type": ["string", "null"], "format": "date-time"},
    "createdBy": {"type": "object", "description": "User or customer who created this thread."},
    "assignedTo": {"type": ["object", "null"]},
    "conversationId": {"type": "integer"},
}

_CUSTOMER_PROPS = {
    "id": {"type": "integer", "description": "Customer ID."},
    "firstName": {"type": ["string", "null"]},
    "lastName": {"type": ["string", "null"]},
    "emails": {"type": "array", "description": "Array of email address objects."},
    "phones": {"type": "array", "description": "Array of phone number objects."},
    "websites": {"type": "array"},
    "createdAt": {"type": "string", "format": "date-time"},
    "updatedAt": {"type": "string", "format": "date-time"},
    "organization": {"type": ["string", "null"]},
    "jobTitle": {"type": ["string", "null"]},
    "background": {"type": ["string", "null"]},
}

_MAILBOX_PROPS = {
    "id": {"type": "integer"},
    "name": {"type": "string"},
    "slug": {"type": "string"},
    "email": {"type": "string"},
    "createdAt": {"type": "string", "format": "date-time"},
}

# (event_name, schema, trigger_description, confidence)
_EVENTS = [
    ("convo.created", _hs_schema("convo.created", _CONVERSATION_PROPS, ["id", "status"]),
     "A new conversation is created in a Help Scout mailbox.", 0.90),
    ("convo.deleted", _hs_schema("convo.deleted", {"id": {"type": "integer"}}, ["id"]),
     "A conversation is deleted.", 0.85),
    ("convo.assigned", _hs_schema("convo.assigned", _CONVERSATION_PROPS, ["id"]),
     "A conversation is assigned to a specific Help Scout user.", 0.90),
    ("convo.moved", _hs_schema("convo.moved", _CONVERSATION_PROPS, ["id"]),
     "A conversation is moved to a different mailbox.", 0.85),
    ("convo.merged", _hs_schema("convo.merged", {
        "id": {"type": "integer"},
        "mergedConversationId": {"type": "integer", "description": "ID of the conversation that was merged away."},
    }, ["id"]), "Two conversations are merged into one.", 0.85),
    ("convo.status", _hs_schema("convo.status", _CONVERSATION_PROPS, ["id", "status"]),
     "A conversation's status changes (e.g. from active to closed).", 0.90),
    ("convo.tags", _hs_schema("convo.tags", _CONVERSATION_PROPS, ["id"]),
     "Tags are added to or removed from a conversation.", 0.85),
    ("convo.agent.reply.created", _hs_schema("convo.agent.reply.created", _THREAD_PROPS, ["id", "conversationId"]),
     "An agent sends a reply from a Help Scout mailbox to a customer.", 0.90),
    ("convo.customer.reply.created", _hs_schema("convo.customer.reply.created", _THREAD_PROPS, ["id", "conversationId"]),
     "A customer sends a reply to an existing conversation.", 0.90),
    ("convo.note.created", _hs_schema("convo.note.created", _THREAD_PROPS, ["id", "conversationId"]),
     "An internal note is added to a conversation.", 0.90),
    ("customer.created", _hs_schema("customer.created", _CUSTOMER_PROPS, ["id"]),
     "A new customer record is created.", 0.85),
    ("customer.updated", _hs_schema("customer.updated", _CUSTOMER_PROPS, ["id"]),
     "A customer's profile data is updated.", 0.85),
    ("satisfaction.ratings", _hs_schema("satisfaction.ratings", {
        "conversationId": {"type": "integer"},
        "customer": {"type": "object"},
        "rating": {"type": "string", "enum": ["Great", "Okay", "Not Good"], "description": "Satisfaction rating submitted."},
        "comments": {"type": ["string", "null"]},
        "ratedAt": {"type": "string", "format": "date-time"},
    }, ["conversationId", "rating"]), "A customer submits a satisfaction rating for a conversation.", 0.85),
]


class HelpScoutExtractor(ExtractorBase):
    slug = "help-scout"
    docs_urls = [
        "https://developer.helpscout.com/webhooks/",
    ]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, payload_schema, trigger_description, confidence in _EVENTS:
            yield {
                "vendor": "help-scout",
                "vendor_display_name": "Help Scout",
                "category": "support",
                "event_name": event_name,
                "event_namespace": None,
                "trigger_description": trigger_description,
                "payload_schema": payload_schema,
                "required_oauth_scopes": None,
                "required_subscription_event": None,
                "auth_method": "hmac-sha1",
                "signature_header": "X-HelpScout-Signature",
                "signature_algorithm_detail": (
                    "HMAC-SHA1 of the raw request body using the webhook's secret key. "
                    "The header value is base64-encoded."
                ),
                "retry_policy": {
                    "max_attempts": 5,
                    "backoff": "Help Scout retries failed deliveries up to 5 times with increasing delays.",
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


register(HelpScoutExtractor)

"""
freshdesk.py — Freshdesk webhook extractor (tier-2, llm-assisted).

Scope: Freshdesk webhook events representing ticket lifecycle triggers.
Freshdesk uses automation rules; the catalog covers the supported trigger events.

Source: https://developers.freshdesk.com/api/#webhooks

extraction_method: llm-assisted
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_DOCS_URL = "https://developers.freshdesk.com/api/#webhooks"

# Freshdesk webhook payloads are JSON with a ticket object and action info.
def _fd_schema(event: str, context_props: dict | None = None) -> dict:
    ticket_props = {
        "id": {"type": "integer", "description": "Ticket ID."},
        "subject": {"type": "string", "description": "Ticket subject."},
        "description": {"type": ["string", "null"], "description": "HTML description of the ticket."},
        "status": {"type": "integer", "description": "Status code (2=open, 3=pending, 4=resolved, 5=closed)."},
        "priority": {"type": "integer", "description": "Priority code (1=low, 2=medium, 3=high, 4=urgent)."},
        "type": {"type": ["string", "null"], "description": "Ticket type (Question, Incident, Problem, Feature Request, etc.)."},
        "source": {"type": "integer", "description": "Source channel (1=email, 2=portal, 3=phone, etc.)."},
        "requester_id": {"type": "integer", "description": "ID of the contact who submitted the ticket."},
        "responder_id": {"type": ["integer", "null"], "description": "ID of the assigned agent."},
        "group_id": {"type": ["integer", "null"], "description": "ID of the assigned group."},
        "due_by": {"type": ["string", "null"], "format": "date-time", "description": "Resolution due date."},
        "fr_due_by": {"type": ["string", "null"], "format": "date-time", "description": "First response due date."},
        "created_at": {"type": "string", "format": "date-time"},
        "updated_at": {"type": "string", "format": "date-time"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "custom_fields": {"type": "object", "description": "Custom field values for this ticket."},
    }
    schema: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "description": f"Freshdesk webhook payload for {event}.",
        "properties": {
            "ticket": {
                "type": "object",
                "description": "The ticket that triggered the event.",
                "properties": ticket_props,
                "required": ["id", "subject", "status"],
            },
        },
        "required": ["ticket"],
    }
    if context_props:
        schema["properties"].update(context_props)
    return schema


_REPLY_PROPS = {
    "reply": {
        "type": "object",
        "description": "The reply or note that was added.",
        "properties": {
            "id": {"type": "integer"},
            "body": {"type": "string", "description": "HTML body of the reply."},
            "body_text": {"type": "string", "description": "Plain text version of the body."},
            "created_at": {"type": "string", "format": "date-time"},
            "from_email": {"type": ["string", "null"]},
            "user_id": {"type": ["integer", "null"]},
        },
    },
}

# (event_name, schema, trigger_description, confidence)
_EVENTS = [
    ("ticket.created", _fd_schema("ticket.created"),
     "A new support ticket is created via email, web portal, phone, or API.", 0.90),
    ("ticket.status_updated", _fd_schema("ticket.status_updated"),
     "A ticket's status changes (e.g. from open to pending, resolved, or closed).", 0.90),
    ("ticket.priority_updated", _fd_schema("ticket.priority_updated"),
     "A ticket's priority level is changed.", 0.90),
    ("ticket.assigned", _fd_schema("ticket.assigned"),
     "A ticket is assigned to an agent or reassigned from one agent to another.", 0.90),
    ("ticket.group_assigned", _fd_schema("ticket.group_assigned"),
     "A ticket is assigned to or moved between support groups.", 0.85),
    ("ticket.type_updated", _fd_schema("ticket.type_updated"),
     "A ticket's type classification is changed.", 0.85),
    ("ticket.due_date_updated", _fd_schema("ticket.due_date_updated"),
     "The resolution due date on a ticket is changed.", 0.85),
    ("ticket.tag_added", _fd_schema("ticket.tag_added"),
     "A tag is added to a ticket.", 0.85),
    ("ticket.tag_removed", _fd_schema("ticket.tag_removed"),
     "A tag is removed from a ticket.", 0.85),
    ("ticket.note_added", _fd_schema("ticket.note_added", _REPLY_PROPS),
     "An internal note is added to a ticket by an agent.", 0.85),
    ("ticket.reply_sent", _fd_schema("ticket.reply_sent", _REPLY_PROPS),
     "An agent sends a reply to the ticket requester.", 0.85),
    ("ticket.requester_replied", _fd_schema("ticket.requester_replied", _REPLY_PROPS),
     "The ticket requester (customer) sends a reply.", 0.85),
    ("ticket.resolved", _fd_schema("ticket.resolved"),
     "A ticket is marked as resolved.", 0.90),
    ("ticket.closed", _fd_schema("ticket.closed"),
     "A ticket is moved to closed state.", 0.90),
    ("ticket.reopened", _fd_schema("ticket.reopened"),
     "A previously resolved or closed ticket is reopened.", 0.85),
    ("ticket.deleted", _fd_schema("ticket.deleted"),
     "A ticket is deleted (moved to trash).", 0.80),
    ("contact.created", {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "contact": {
                "type": "object",
                "description": "The created contact.",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "email": {"type": ["string", "null"]},
                    "phone": {"type": ["string", "null"]},
                    "company_id": {"type": ["integer", "null"]},
                    "created_at": {"type": "string", "format": "date-time"},
                },
                "required": ["id"],
            },
        },
        "required": ["contact"],
    }, "A new contact record is created in Freshdesk.", 0.80),
    ("contact.updated", {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "contact": {
                "type": "object",
                "description": "The updated contact.",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "email": {"type": ["string", "null"]},
                    "updated_at": {"type": "string", "format": "date-time"},
                },
                "required": ["id"],
            },
        },
        "required": ["contact"],
    }, "A contact's information is updated.", 0.75),
]


class FreshdeskExtractor(ExtractorBase):
    slug = "freshdesk"
    docs_urls = [
        "https://developers.freshdesk.com/api/#webhooks",
    ]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, payload_schema, trigger_description, confidence in _EVENTS:
            yield {
                "vendor": "freshdesk",
                "vendor_display_name": "Freshdesk",
                "category": "support",
                "event_name": event_name,
                "event_namespace": None,
                "trigger_description": trigger_description,
                "payload_schema": payload_schema,
                "required_oauth_scopes": None,
                "required_subscription_event": None,
                "auth_method": "none",
                "signature_header": None,
                "signature_algorithm_detail": (
                    "Freshdesk webhooks do not include a request signature by default. "
                    "Authentication relies on IP allowlisting or a custom token in the URL."
                ),
                "retry_policy": {
                    "max_attempts": None,
                    "backoff": "Freshdesk retries failed webhook deliveries.",
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
                    "Freshdesk webhooks are configured via automation rules rather than a webhook subscription API. "
                    "Events are trigger conditions; payload shape depends on which rule fires."
                ),
            }


register(FreshdeskExtractor)

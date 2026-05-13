"""
close.py — Close CRM webhook extractor (tier-2, llm-assisted).

Scope: Close.com webhook events for leads, contacts, activities, opportunities, and tasks.

Source: https://developer.close.com/resources/webhooks

extraction_method: llm-assisted
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_DOCS_URL = "https://developer.close.com/resources/webhooks"

def _close_schema(event: str, model_type: str, data_props: dict, required: list[str] | None = None) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "event": {"type": "string", "description": f"Event type identifier: {event}."},
            "subscription_id": {"type": "string", "description": "Webhook subscription ID."},
            "data": {
                "type": "object",
                "description": f"The {model_type} object that was affected.",
                "properties": data_props,
                "required": required or [],
            },
        },
        "required": ["event", "subscription_id", "data"],
    }

_LEAD_PROPS = {
    "id": {"type": "string", "description": "Lead ID (prefixed 'lead_')."},
    "name": {"type": "string"},
    "description": {"type": ["string", "null"]},
    "status_id": {"type": ["string", "null"], "description": "Lead status ID."},
    "status_label": {"type": ["string", "null"], "description": "Human-readable status label."},
    "created_by": {"type": ["string", "null"]},
    "updated_by": {"type": ["string", "null"]},
    "date_created": {"type": "string", "format": "date-time"},
    "date_updated": {"type": "string", "format": "date-time"},
    "organization_id": {"type": "string"},
    "contacts": {"type": "array", "description": "Array of contact objects on this lead."},
    "opportunities": {"type": "array", "description": "Array of opportunity objects."},
    "tasks": {"type": "array", "description": "Array of task objects."},
    "custom": {"type": "object", "description": "Custom field values."},
}

_CONTACT_PROPS = {
    "id": {"type": "string", "description": "Contact ID (prefixed 'cont_')."},
    "name": {"type": "string"},
    "title": {"type": ["string", "null"]},
    "lead_id": {"type": "string"},
    "phones": {"type": "array", "description": "Array of phone objects."},
    "emails": {"type": "array", "description": "Array of email objects."},
    "urls": {"type": "array"},
    "date_created": {"type": "string", "format": "date-time"},
    "date_updated": {"type": "string", "format": "date-time"},
}

_OPPORTUNITY_PROPS = {
    "id": {"type": "string", "description": "Opportunity ID (prefixed 'oppo_')."},
    "lead_id": {"type": "string"},
    "lead_name": {"type": "string"},
    "status_id": {"type": "string"},
    "status_label": {"type": "string"},
    "status_type": {"type": "string", "enum": ["active", "won", "lost"]},
    "value": {"type": ["integer", "null"], "description": "Value in cents."},
    "value_currency": {"type": ["string", "null"]},
    "confidence": {"type": ["integer", "null"], "description": "Win probability percentage."},
    "note": {"type": ["string", "null"]},
    "date_created": {"type": "string", "format": "date-time"},
    "date_updated": {"type": "string", "format": "date-time"},
    "date_won": {"type": ["string", "null"], "format": "date-time"},
    "date_lost": {"type": ["string", "null"], "format": "date-time"},
    "close_date": {"type": ["string", "null"]},
}

_TASK_PROPS = {
    "id": {"type": "string", "description": "Task ID (prefixed 'task_')."},
    "lead_id": {"type": ["string", "null"]},
    "assigned_to": {"type": ["string", "null"], "description": "User ID the task is assigned to."},
    "text": {"type": "string", "description": "Task description."},
    "is_complete": {"type": "boolean"},
    "date": {"type": ["string", "null"]},
    "date_created": {"type": "string", "format": "date-time"},
    "date_updated": {"type": "string", "format": "date-time"},
}

_ACTIVITY_CALL_PROPS = {
    "id": {"type": "string", "description": "Call activity ID (prefixed 'acti_')."},
    "lead_id": {"type": "string"},
    "direction": {"type": "string", "enum": ["inbound", "outbound"]},
    "status": {"type": "string", "enum": ["completed", "missed", "voicemail"]},
    "duration": {"type": ["integer", "null"], "description": "Call duration in seconds."},
    "created_by": {"type": ["string", "null"]},
    "date_created": {"type": "string", "format": "date-time"},
    "note": {"type": ["string", "null"]},
}

_ACTIVITY_EMAIL_PROPS = {
    "id": {"type": "string"},
    "lead_id": {"type": "string"},
    "direction": {"type": "string", "enum": ["inbound", "outbound"]},
    "subject": {"type": ["string", "null"]},
    "body_text": {"type": ["string", "null"]},
    "created_by": {"type": ["string", "null"]},
    "date_created": {"type": "string", "format": "date-time"},
    "status": {"type": "string", "description": "Email delivery status."},
}

# (event_name, model_type, data_props, trigger_description, confidence)
_EVENTS = [
    ("lead.created", "lead", _LEAD_PROPS, "A new lead is created in Close.", 0.95),
    ("lead.updated", "lead", _LEAD_PROPS, "A lead's properties are modified.", 0.90),
    ("lead.deleted", "lead", _LEAD_PROPS, "A lead is permanently deleted.", 0.90),
    ("lead.merged", "lead", {**_LEAD_PROPS, "source_id": {"type": "string", "description": "ID of the lead that was merged in."}},
     "Two leads are merged; source_id indicates the removed lead.", 0.80),
    ("contact.created", "contact", _CONTACT_PROPS, "A new contact is added to a lead.", 0.90),
    ("contact.updated", "contact", _CONTACT_PROPS, "A contact's details are changed.", 0.85),
    ("contact.deleted", "contact", _CONTACT_PROPS, "A contact is deleted.", 0.85),
    ("opportunity.created", "opportunity", _OPPORTUNITY_PROPS, "A new opportunity is created on a lead.", 0.90),
    ("opportunity.updated", "opportunity", _OPPORTUNITY_PROPS, "An opportunity's status, value, or properties are changed.", 0.90),
    ("opportunity.deleted", "opportunity", _OPPORTUNITY_PROPS, "An opportunity is deleted.", 0.85),
    ("task.created", "task", _TASK_PROPS, "A new task is created.", 0.85),
    ("task.updated", "task", _TASK_PROPS, "A task's details or completion status changes.", 0.85),
    ("task.completed", "task", _TASK_PROPS, "A task is marked as complete.", 0.85),
    ("task.deleted", "task", _TASK_PROPS, "A task is deleted.", 0.80),
    ("activity.call.created", "activity.call", _ACTIVITY_CALL_PROPS, "A call activity is logged on a lead.", 0.85),
    ("activity.call.updated", "activity.call", _ACTIVITY_CALL_PROPS, "A logged call activity is updated.", 0.80),
    ("activity.call.deleted", "activity.call", _ACTIVITY_CALL_PROPS, "A call activity is deleted.", 0.80),
    ("activity.email.created", "activity.email", _ACTIVITY_EMAIL_PROPS, "An email activity is logged (inbound or outbound).", 0.85),
    ("activity.email.updated", "activity.email", _ACTIVITY_EMAIL_PROPS, "An email activity is updated.", 0.75),
    ("activity.note.created", "activity.note", {
        "id": {"type": "string"},
        "lead_id": {"type": "string"},
        "note": {"type": "string"},
        "created_by": {"type": ["string", "null"]},
        "date_created": {"type": "string", "format": "date-time"},
    }, "A note activity is added to a lead.", 0.85),
]


class CloseExtractor(ExtractorBase):
    slug = "close"
    docs_urls = [
        "https://developer.close.com/resources/webhooks",
    ]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, model_type, data_props, trigger_description, confidence in _EVENTS:
            yield {
                "vendor": "close",
                "vendor_display_name": "Close",
                "category": "crm",
                "event_name": event_name,
                "event_namespace": model_type.split(".")[0] if "." in model_type else model_type,
                "trigger_description": trigger_description,
                "payload_schema": _close_schema(event_name, model_type, data_props, ["id"]),
                "required_oauth_scopes": None,
                "required_subscription_event": None,
                "auth_method": "hmac-sha256",
                "signature_header": "close-sig-hash",
                "signature_algorithm_detail": (
                    "HMAC-SHA256 of the concatenation of close-sig-timestamp and the raw request body. "
                    "The timestamp is included in the close-sig-timestamp header."
                ),
                "retry_policy": {
                    "max_attempts": None,
                    "backoff": "Close retries failed webhook deliveries.",
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


register(CloseExtractor)

"""
attio.py — Attio CRM webhook extractor (tier-2, llm-assisted).

Scope: Attio webhook events for records, lists, notes, tasks, and attribute changes.

Source: https://developers.attio.com/docs/webhooks

extraction_method: llm-assisted
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_DOCS_URL = "https://developers.attio.com/docs/webhooks"

def _attio_schema(event_type: str, data_props: dict, required: list[str] | None = None) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "event_type": {"type": "string", "description": f"Event type: {event_type}."},
            "id": {
                "type": "object",
                "description": "Unique event identifier.",
                "properties": {
                    "workspace_id": {"type": "string", "description": "Attio workspace ID."},
                    "event_id": {"type": "string", "description": "Unique event ID."},
                },
                "required": ["workspace_id", "event_id"],
            },
            "created_at": {"type": "string", "format": "date-time", "description": "ISO 8601 timestamp when the event occurred."},
            "data": {
                "type": "object",
                "description": "Event-specific data.",
                "properties": data_props,
                "required": required or [],
            },
        },
        "required": ["event_type", "id", "created_at", "data"],
    }

_RECORD_PROPS = {
    "record": {
        "type": "object",
        "description": "The record that was created, updated, or deleted.",
        "properties": {
            "object": {
                "type": "object",
                "description": "The object (collection) this record belongs to.",
                "properties": {
                    "workspace_id": {"type": "string"},
                    "object_id": {"type": "string", "description": "Object ID."},
                    "api_slug": {"type": "string", "description": "API slug for the object (e.g. 'people', 'companies')."},
                },
            },
            "id": {
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string"},
                    "object_id": {"type": "string"},
                    "record_id": {"type": "string"},
                },
            },
            "values": {
                "type": "object",
                "description": "Map of attribute API slugs to their values.",
            },
        },
    },
}

_LIST_ENTRY_PROPS = {
    "entry": {
        "type": "object",
        "description": "The list entry that was created or deleted.",
        "properties": {
            "list": {
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string"},
                    "list_id": {"type": "string"},
                    "api_slug": {"type": "string"},
                },
            },
            "id": {
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string"},
                    "list_id": {"type": "string"},
                    "entry_id": {"type": "string"},
                },
            },
            "parent_record_id": {"type": ["object", "null"]},
            "values": {"type": "object", "description": "Attribute values for this list entry."},
        },
    },
}

_NOTE_PROPS = {
    "note": {
        "type": "object",
        "description": "The note that was created or deleted.",
        "properties": {
            "id": {
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string"},
                    "note_id": {"type": "string"},
                },
            },
            "parent_object": {"type": ["string", "null"]},
            "parent_record_id": {"type": ["string", "null"]},
            "title": {"type": "string"},
            "content": {"type": ["string", "null"]},
            "created_by_actor": {"type": "object", "description": "Actor who created the note."},
            "created_at": {"type": "string", "format": "date-time"},
        },
    },
}

_TASK_PROPS = {
    "task": {
        "type": "object",
        "description": "The task that was created or updated.",
        "properties": {
            "id": {
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string"},
                    "task_id": {"type": "string"},
                },
            },
            "content": {"type": "string", "description": "Task description."},
            "is_completed": {"type": "boolean"},
            "deadline_at": {"type": ["string", "null"], "format": "date-time"},
            "created_by_actor": {"type": "object"},
            "created_at": {"type": "string", "format": "date-time"},
            "completed_at": {"type": ["string", "null"], "format": "date-time"},
            "linked_records": {"type": "array", "description": "Records linked to this task."},
            "assignees": {"type": "array", "description": "Workspace members assigned to this task."},
        },
    },
}

_ATTR_CHANGE_PROPS = {
    **_RECORD_PROPS,
    "changed_attribute": {
        "type": "string",
        "description": "API slug of the attribute that changed.",
    },
}

# (event_name, data_props, required_data_fields, trigger_description, confidence)
_EVENTS = [
    ("record.created", _RECORD_PROPS, ["record"],
     "A new record is created in any object (people, companies, deals, or custom objects).", 0.90),
    ("record.updated", {**_RECORD_PROPS}, ["record"],
     "A record's attribute values are updated.", 0.85),
    ("record.deleted", {**_RECORD_PROPS}, ["record"],
     "A record is deleted.", 0.85),
    ("record.attribute.created", _ATTR_CHANGE_PROPS, ["record", "changed_attribute"],
     "A new value is set on a multi-value attribute of a record (e.g. a new email added).", 0.80),
    ("record.attribute.updated", _ATTR_CHANGE_PROPS, ["record", "changed_attribute"],
     "An existing attribute value on a record is modified.", 0.80),
    ("record.attribute.deleted", _ATTR_CHANGE_PROPS, ["record", "changed_attribute"],
     "An attribute value is removed from a record.", 0.80),
    ("list-entry.created", _LIST_ENTRY_PROPS, ["entry"],
     "A record is added to a list (e.g. a deal pipeline).", 0.85),
    ("list-entry.deleted", _LIST_ENTRY_PROPS, ["entry"],
     "A record is removed from a list.", 0.85),
    ("list-entry.attribute.created", {
        **_LIST_ENTRY_PROPS,
        "changed_attribute": {"type": "string"},
    }, ["entry", "changed_attribute"],
     "A new value is set on a list entry attribute.", 0.75),
    ("list-entry.attribute.updated", {
        **_LIST_ENTRY_PROPS,
        "changed_attribute": {"type": "string"},
    }, ["entry", "changed_attribute"],
     "An existing list entry attribute is modified.", 0.75),
    ("note.created", _NOTE_PROPS, ["note"],
     "A note is added to a record or list entry.", 0.85),
    ("note.deleted", _NOTE_PROPS, ["note"],
     "A note is deleted.", 0.80),
    ("task.created", _TASK_PROPS, ["task"],
     "A new task is created and linked to records.", 0.85),
    ("task.updated", _TASK_PROPS, ["task"],
     "A task's properties or completion status are updated.", 0.80),
    ("task.deleted", _TASK_PROPS, ["task"],
     "A task is deleted.", 0.75),
]


class AttioExtractor(ExtractorBase):
    slug = "attio"
    docs_urls = [
        "https://developers.attio.com/docs/webhooks",
    ]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, data_props, required_data_fields, trigger_description, confidence in _EVENTS:
            yield {
                "vendor": "attio",
                "vendor_display_name": "Attio",
                "category": "crm",
                "event_name": event_name,
                "event_namespace": event_name.split(".")[0],
                "trigger_description": trigger_description,
                "payload_schema": _attio_schema(event_name, data_props, required_data_fields),
                "required_oauth_scopes": None,
                "required_subscription_event": None,
                "auth_method": "hmac-sha256",
                "signature_header": "X-Attio-Signature",
                "signature_algorithm_detail": (
                    "HMAC-SHA256 of the raw request body using the webhook's signing secret."
                ),
                "retry_policy": {
                    "max_attempts": None,
                    "backoff": "Attio retries failed webhook deliveries with exponential backoff.",
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
                    "Attio uses a structured ID object pattern throughout (workspace_id + resource_id). "
                    "Custom objects and lists are supported; event types are generic across all object slugs."
                ),
            }


register(AttioExtractor)

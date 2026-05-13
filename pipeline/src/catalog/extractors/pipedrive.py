"""
pipedrive.py — Pipedrive webhook extractor (tier-2, llm-assisted).

Scope: Pipedrive webhook events for all core CRM objects (deals, persons,
       organizations, activities, leads, notes, pipelines, stages, products).

Source: https://pipedrive.readme.io/docs/guide-for-webhooks

extraction_method: llm-assisted
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_DOCS_URL = "https://pipedrive.readme.io/docs/guide-for-webhooks"

# Pipedrive webhooks use action × object pairs.
# Common envelope schema.
def _pd_schema(action: str, object_type: str, current_props: dict, previous_desc: str = "Previous state of the object before the change.") -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "v": {"type": "integer", "description": "Webhook version."},
            "matches_filters": {
                "type": "object",
                "description": "Filter conditions matched by this event.",
                "properties": {
                    "current": {"type": "array"},
                    "previous": {"type": "array"},
                },
            },
            "meta": {
                "type": "object",
                "description": "Metadata about the webhook event.",
                "properties": {
                    "v": {"type": "integer"},
                    "action": {"type": "string", "description": f"Action: {action}."},
                    "object": {"type": "string", "description": f"Object type: {object_type}."},
                    "id": {"type": "integer", "description": "ID of the affected object."},
                    "company_id": {"type": "integer", "description": "Pipedrive company (account) ID."},
                    "user_id": {"type": ["integer", "null"], "description": "User who triggered the event."},
                    "host": {"type": "string"},
                    "timestamp": {"type": "integer", "description": "Unix timestamp."},
                    "timestamp_micro": {"type": "integer"},
                    "permitted_user_ids": {"type": "array", "items": {"type": "integer"}},
                    "is_bulk_update": {"type": "boolean"},
                    "webhook_id": {"type": "string"},
                    "attempt_no": {"type": "integer"},
                    "change_source": {"type": "string"},
                    "next_attempt_ts": {"type": ["integer", "null"]},
                },
                "required": ["action", "object", "id"],
            },
            "current": {
                "type": ["object", "null"],
                "description": f"Current (post-change) state of the {object_type}.",
                "properties": current_props,
            },
            "previous": {
                "type": ["object", "null"],
                "description": previous_desc,
            },
            "event": {"type": "string", "description": f"Combined event string, e.g. {action}.{object_type}."},
        },
        "required": ["meta", "event"],
    }

_DEAL_PROPS = {
    "id": {"type": "integer"},
    "title": {"type": "string"},
    "value": {"type": ["number", "null"], "description": "Deal value amount."},
    "currency": {"type": ["string", "null"]},
    "status": {"type": "string", "enum": ["open", "won", "lost", "deleted"]},
    "person_id": {"type": ["object", "null"], "description": "Associated person."},
    "org_id": {"type": ["object", "null"], "description": "Associated organization."},
    "owner_id": {"type": "object", "description": "Deal owner user object."},
    "pipeline_id": {"type": "integer", "description": "Pipeline this deal is in."},
    "stage_id": {"type": "integer", "description": "Current stage ID."},
    "add_time": {"type": "string"},
    "update_time": {"type": "string"},
    "close_time": {"type": ["string", "null"]},
    "expected_close_date": {"type": ["string", "null"]},
    "probability": {"type": ["number", "null"]},
    "lost_reason": {"type": ["string", "null"]},
}

_PERSON_PROPS = {
    "id": {"type": "integer"},
    "name": {"type": "string"},
    "email": {"type": "array", "description": "Array of email objects."},
    "phone": {"type": "array", "description": "Array of phone objects."},
    "org_id": {"type": ["object", "null"]},
    "owner_id": {"type": "object"},
    "add_time": {"type": "string"},
    "update_time": {"type": "string"},
}

_ORG_PROPS = {
    "id": {"type": "integer"},
    "name": {"type": "string"},
    "owner_id": {"type": "object"},
    "address": {"type": ["string", "null"]},
    "people_count": {"type": ["integer", "null"]},
    "open_deals_count": {"type": ["integer", "null"]},
    "add_time": {"type": "string"},
    "update_time": {"type": "string"},
}

_ACTIVITY_PROPS = {
    "id": {"type": "integer"},
    "subject": {"type": ["string", "null"]},
    "type": {"type": "string", "description": "Activity type (call, meeting, task, email, etc.)."},
    "done": {"type": "boolean"},
    "due_date": {"type": ["string", "null"]},
    "due_time": {"type": ["string", "null"]},
    "deal_id": {"type": ["integer", "null"]},
    "person_id": {"type": ["integer", "null"]},
    "org_id": {"type": ["integer", "null"]},
    "user_id": {"type": "integer"},
    "add_time": {"type": "string"},
    "update_time": {"type": "string"},
}

# (event_name, action, object_type, schema, trigger_description, confidence)
_EVENTS = [
    ("added.deal", "added", "deal", _pd_schema("added", "deal", _DEAL_PROPS), "A new deal is added to the pipeline.", 0.95),
    ("updated.deal", "updated", "deal", _pd_schema("updated", "deal", _DEAL_PROPS), "A deal's properties are modified.", 0.90),
    ("deleted.deal", "deleted", "deal", _pd_schema("deleted", "deal", _DEAL_PROPS), "A deal is deleted.", 0.90),
    ("added.person", "added", "person", _pd_schema("added", "person", _PERSON_PROPS), "A new contact person is added to Pipedrive.", 0.95),
    ("updated.person", "updated", "person", _pd_schema("updated", "person", _PERSON_PROPS), "A person's profile details are changed.", 0.90),
    ("deleted.person", "deleted", "person", _pd_schema("deleted", "person", _PERSON_PROPS), "A person is deleted.", 0.85),
    ("added.organization", "added", "organization", _pd_schema("added", "organization", _ORG_PROPS), "A new organization is added.", 0.90),
    ("updated.organization", "updated", "organization", _pd_schema("updated", "organization", _ORG_PROPS), "An organization's details are changed.", 0.85),
    ("deleted.organization", "deleted", "organization", _pd_schema("deleted", "organization", _ORG_PROPS), "An organization is deleted.", 0.85),
    ("added.activity", "added", "activity", _pd_schema("added", "activity", _ACTIVITY_PROPS), "A new activity is scheduled.", 0.90),
    ("updated.activity", "updated", "activity", _pd_schema("updated", "activity", _ACTIVITY_PROPS), "An activity's details are changed or it is marked done.", 0.85),
    ("deleted.activity", "deleted", "activity", _pd_schema("deleted", "activity", _ACTIVITY_PROPS), "An activity is deleted.", 0.85),
    ("added.note", "added", "note", _pd_schema("added", "note", {
        "id": {"type": "integer"},
        "content": {"type": "string"},
        "deal_id": {"type": ["integer", "null"]},
        "person_id": {"type": ["integer", "null"]},
        "org_id": {"type": ["integer", "null"]},
        "user_id": {"type": "integer"},
        "add_time": {"type": "string"},
        "update_time": {"type": "string"},
    }), "A new note is added to a deal, person, or organization.", 0.85),
    ("updated.note", "updated", "note", _pd_schema("updated", "note", {
        "id": {"type": "integer"},
        "content": {"type": "string"},
    }), "An existing note's content is edited.", 0.80),
    ("deleted.note", "deleted", "note", _pd_schema("deleted", "note", {"id": {"type": "integer"}}), "A note is deleted.", 0.80),
    ("added.pipeline", "added", "pipeline", _pd_schema("added", "pipeline", {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "order_nr": {"type": "integer"},
    }), "A new pipeline is created.", 0.85),
    ("updated.pipeline", "updated", "pipeline", _pd_schema("updated", "pipeline", {
        "id": {"type": "integer"},
        "name": {"type": "string"},
    }), "A pipeline's properties are updated.", 0.80),
    ("deleted.pipeline", "deleted", "pipeline", _pd_schema("deleted", "pipeline", {"id": {"type": "integer"}}), "A pipeline is deleted.", 0.80),
    ("added.stage", "added", "stage", _pd_schema("added", "stage", {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "pipeline_id": {"type": "integer"},
        "order_nr": {"type": "integer"},
    }), "A new stage is added to a pipeline.", 0.85),
    ("updated.stage", "updated", "stage", _pd_schema("updated", "stage", {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "pipeline_id": {"type": "integer"},
    }), "A stage's properties are updated.", 0.80),
]


class PipedriveExtractor(ExtractorBase):
    slug = "pipedrive"
    docs_urls = [
        "https://pipedrive.readme.io/docs/guide-for-webhooks",
    ]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, action, object_type, payload_schema, trigger_description, confidence in _EVENTS:
            yield {
                "vendor": "pipedrive",
                "vendor_display_name": "Pipedrive",
                "category": "crm",
                "event_name": event_name,
                "event_namespace": object_type,
                "trigger_description": trigger_description,
                "payload_schema": payload_schema,
                "required_oauth_scopes": None,
                "required_subscription_event": None,
                "auth_method": "none",
                "signature_header": None,
                "signature_algorithm_detail": (
                    "Pipedrive classic webhooks do not include a request signature. "
                    "Basic authentication can be set on the receiving endpoint."
                ),
                "retry_policy": {
                    "max_attempts": None,
                    "backoff": "Pipedrive retries failed webhook deliveries with exponential backoff.",
                    "total_retry_window": "P3D",
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
                    "Pipedrive event_name format is '{action}.{object}'. "
                    "Payload shape is uniform; 'current' is null on deleted events."
                ),
            }


register(PipedriveExtractor)

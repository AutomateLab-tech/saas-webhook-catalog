"""
clickup.py — ClickUp webhook extractor (tier-2, llm-assisted).

Scope: ClickUp Webhooks API events across tasks, lists, folders, spaces, goals, and members.

Source: https://clickup.com/api/developer-portal/webhooks/

extraction_method: llm-assisted
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_DOCS_URL = "https://clickup.com/api/developer-portal/webhooks/"

def _cu_schema(event_name: str, history_items_description: str) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "webhook_id": {"type": "string", "description": "ID of the webhook that delivered this event."},
            "event": {"type": "string", "description": f"Event type identifier: {event_name}."},
            "task_id": {"type": ["string", "null"], "description": "Task ID if the event is task-scoped."},
            "history_items": {
                "type": "array",
                "description": history_items_description,
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "History item ID."},
                        "type": {"type": "integer", "description": "History item type integer."},
                        "date": {"type": "string", "description": "Epoch milliseconds string when the change occurred."},
                        "field": {"type": ["string", "null"], "description": "Field name that changed, if applicable."},
                        "parent_id": {"type": ["string", "null"], "description": "Parent resource ID."},
                        "data": {"type": ["object", "null"], "description": "Additional data about the change."},
                        "source": {"type": ["string", "null"], "description": "Change source (app, api, etc.)."},
                        "user": {
                            "type": "object",
                            "description": "User who triggered the event.",
                            "properties": {
                                "id": {"type": "integer", "description": "User ID."},
                                "username": {"type": "string"},
                                "email": {"type": "string"},
                                "color": {"type": "string"},
                                "profilePicture": {"type": ["string", "null"]},
                                "initials": {"type": "string"},
                            },
                        },
                        "before": {"type": ["object", "string", "null"], "description": "Previous value before the change."},
                        "after": {"type": ["object", "string", "null"], "description": "New value after the change."},
                    },
                    "required": ["id", "type", "date"],
                },
            },
        },
        "required": ["webhook_id", "event"],
    }


# (event_name, trigger_description, confidence)
_EVENTS = [
    ("taskCreated", "A new task is created in a subscribed workspace, space, folder, or list.", 0.95),
    ("taskUpdated", "A task's properties are modified; history_items lists each changed field.", 0.90),
    ("taskDeleted", "A task is deleted or moved to trash.", 0.90),
    ("taskPriorityUpdated", "A task's priority level is changed.", 0.90),
    ("taskStatusUpdated", "A task's status transitions to a new status value.", 0.95),
    ("taskAssigneeUpdated", "An assignee is added to or removed from a task.", 0.90),
    ("taskDueDateUpdated", "A task's due date is set, changed, or cleared.", 0.90),
    ("taskTagUpdated", "A tag is added to or removed from a task.", 0.85),
    ("taskMoved", "A task is moved to a different list, folder, or space.", 0.85),
    ("taskCommentPosted", "A new comment is posted on a task.", 0.90),
    ("taskCommentUpdated", "An existing comment on a task is edited.", 0.85),
    ("taskTimeEstimateUpdated", "A task's time estimate is set or modified.", 0.85),
    ("taskTimeTrackedUpdated", "Time tracked against a task is added or edited.", 0.85),
    ("listCreated", "A new list is created within a subscribed space or folder.", 0.90),
    ("listUpdated", "A list's properties are modified.", 0.85),
    ("listDeleted", "A list is deleted.", 0.85),
    ("folderCreated", "A new folder is created in a subscribed space.", 0.90),
    ("folderUpdated", "A folder's properties are modified.", 0.85),
    ("folderDeleted", "A folder is deleted.", 0.85),
    ("spaceCreated", "A new space is created in the workspace.", 0.85),
    ("spaceUpdated", "A space's properties are modified.", 0.80),
    ("spaceDeleted", "A space is deleted.", 0.80),
    ("goalCreated", "A new goal is created in the workspace.", 0.80),
    ("goalUpdated", "A goal's properties or targets are updated.", 0.75),
    ("goalDeleted", "A goal is deleted.", 0.75),
    ("keyResultCreated", "A new key result target is added to a goal.", 0.75),
    ("keyResultUpdated", "A key result is updated.", 0.75),
    ("keyResultDeleted", "A key result is removed from a goal.", 0.75),
]


class ClickUpExtractor(ExtractorBase):
    slug = "clickup"
    docs_urls = [
        "https://clickup.com/api/developer-portal/webhooks/",
    ]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, trigger_description, confidence in _EVENTS:
            yield {
                "vendor": "clickup",
                "vendor_display_name": "ClickUp",
                "category": "collaboration",
                "event_name": event_name,
                "event_namespace": None,
                "trigger_description": trigger_description,
                "payload_schema": _cu_schema(event_name, f"Array of change history items for event {event_name}."),
                "required_oauth_scopes": None,
                "required_subscription_event": None,
                "auth_method": "hmac-sha256",
                "signature_header": None,
                "signature_algorithm_detail": (
                    "ClickUp signs webhook payloads with HMAC-SHA256 using the webhook secret. "
                    "The signature is included in the 'signature' field inside the JSON body, "
                    "not as a header."
                ),
                "retry_policy": {
                    "max_attempts": None,
                    "backoff": "ClickUp retries failed deliveries; exact policy not documented publicly.",
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
                    "ClickUp payload schemas are sparse in public docs; "
                    "field shapes inferred from API reference and community samples."
                ),
            }


register(ClickUpExtractor)

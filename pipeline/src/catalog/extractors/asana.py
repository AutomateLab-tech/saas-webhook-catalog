"""
asana.py — Asana webhook extractor (tier-2, llm-assisted).

Scope: Asana webhook events delivered via HTTP POST to a registered target URL.
Events cover tasks, projects, teams, workspaces, stories, and attachments.

Source: https://developers.asana.com/docs/webhooks
        https://developers.asana.com/docs/webhooks-guide

extraction_method: llm-assisted
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_PAYLOAD_SCHEMA_BASE = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "description": "Array of event objects in this delivery batch.",
            "items": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The action that occurred: added, changed, deleted, removed, undeleted.",
                    },
                    "created_at": {
                        "type": "string",
                        "format": "date-time",
                        "description": "ISO 8601 timestamp when the event was created.",
                    },
                    "parent": {
                        "type": ["object", "null"],
                        "description": "The parent resource if the changed resource is a sub-resource.",
                        "properties": {
                            "gid": {"type": "string", "description": "Global ID of the parent resource."},
                            "resource_type": {"type": "string", "description": "Resource type of the parent."},
                        },
                    },
                    "resource": {
                        "type": "object",
                        "description": "The resource that was changed.",
                        "properties": {
                            "gid": {"type": "string", "description": "Global ID of the changed resource."},
                            "resource_type": {"type": "string", "description": "Type of the changed resource."},
                            "resource_subtype": {
                                "type": ["string", "null"],
                                "description": "Subtype of the changed resource, if applicable.",
                            },
                        },
                        "required": ["gid", "resource_type"],
                    },
                    "user": {
                        "type": ["object", "null"],
                        "description": "The user who triggered the event.",
                        "properties": {
                            "gid": {"type": "string", "description": "Global ID of the user."},
                            "resource_type": {"type": "string", "description": "Always 'user'."},
                        },
                    },
                    "change": {
                        "type": ["object", "null"],
                        "description": "Details of what changed (for 'changed' actions).",
                        "properties": {
                            "field": {"type": "string", "description": "The field that changed."},
                            "action": {"type": "string", "description": "The change action (added/changed/removed)."},
                            "added_value": {"type": ["object", "null"], "description": "Value added to the field."},
                            "removed_value": {"type": ["object", "null"], "description": "Value removed from the field."},
                        },
                    },
                },
                "required": ["action", "created_at", "resource"],
            },
        },
    },
    "required": ["events"],
}

# (event_name, resource_type, action, trigger_description, confidence)
_EVENTS = [
    ("task.added", "task", "added", "task", "A new task is created in a subscribed project or workspace.", 0.95),
    ("task.changed", "task", "changed", "task", "A task's properties are modified, such as name, description, due date, assignee, or status.", 0.95),
    ("task.deleted", "task", "deleted", "task", "A task is moved to the trash (soft delete).", 0.95),
    ("task.undeleted", "task", "undeleted", "task", "A previously deleted task is restored from the trash.", 0.90),
    ("task.removed", "task", "removed", "task", "A task is removed from a project or section (not deleted).", 0.90),
    ("story.added", "story", "added", "story", "A new story (comment or system event) is added to a task.", 0.90),
    ("story.changed", "story", "changed", "story", "An existing story or comment is edited.", 0.85),
    ("story.deleted", "story", "deleted", "story", "A story or comment is deleted from a task.", 0.85),
    ("story.undeleted", "story", "undeleted", "story", "A deleted story is restored.", 0.80),
    ("project.added", "project", "added", "project", "A new project is created in the subscribed workspace or team.", 0.95),
    ("project.changed", "project", "changed", "project", "A project's properties are updated, such as name, color, owner, or status.", 0.90),
    ("project.deleted", "project", "deleted", "project", "A project is moved to the trash.", 0.90),
    ("project.undeleted", "project", "undeleted", "project", "A deleted project is restored from the trash.", 0.80),
    ("project_membership.added", "project_membership", "added", "project_membership", "A user or team is added as a member to a project.", 0.85),
    ("project_membership.removed", "project_membership", "removed", "project_membership", "A user or team is removed from a project's membership.", 0.85),
    ("section.added", "section", "added", "section", "A new section is created within a subscribed project.", 0.90),
    ("section.changed", "section", "changed", "section", "A section's properties (name, position) are modified.", 0.85),
    ("section.deleted", "section", "deleted", "section", "A section is removed from a project.", 0.85),
    ("attachment.added", "attachment", "added", "attachment", "A file or URL is attached to a task.", 0.85),
    ("attachment.deleted", "attachment", "deleted", "attachment", "An attachment is removed from a task.", 0.80),
    ("tag.added", "tag", "added", "tag", "A new tag is created in the workspace.", 0.85),
    ("tag.changed", "tag", "changed", "tag", "A tag's properties are updated.", 0.80),
    ("tag.deleted", "tag", "deleted", "tag", "A tag is deleted from the workspace.", 0.80),
    ("workspace.changed", "workspace", "changed", "workspace", "Workspace-level properties such as name or email domains are updated.", 0.80),
    ("team.added", "team", "added", "team", "A new team is created within the subscribed workspace.", 0.85),
    ("team.changed", "team", "changed", "team", "A team's properties are updated.", 0.80),
    ("team.deleted", "team", "deleted", "team", "A team is deleted from the workspace.", 0.80),
    ("team_membership.added", "team_membership", "added", "team_membership", "A user joins or is added to a team.", 0.85),
    ("team_membership.removed", "team_membership", "removed", "team_membership", "A user leaves or is removed from a team.", 0.85),
]


class AsanaExtractor(ExtractorBase):
    slug = "asana"
    docs_urls = [
        "https://developers.asana.com/docs/webhooks",
        "https://developers.asana.com/docs/webhooks-guide",
    ]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, resource_type, action, namespace, trigger_description, confidence in _EVENTS:
            yield {
                "vendor": "asana",
                "vendor_display_name": "Asana",
                "category": "collaboration",
                "event_name": event_name,
                "event_namespace": resource_type,
                "trigger_description": trigger_description,
                "payload_schema": _PAYLOAD_SCHEMA_BASE,
                "required_oauth_scopes": None,
                "required_subscription_event": None,
                "auth_method": "hmac-sha256",
                "signature_header": "X-Hook-Secret",
                "signature_algorithm_detail": (
                    "HMAC-SHA256 computed over the raw request body. "
                    "The secret is established during webhook handshake via X-Hook-Secret header."
                ),
                "retry_policy": {
                    "max_attempts": 3,
                    "backoff": "Asana retries with brief delays on non-2xx responses.",
                    "total_retry_window": None,
                },
                "max_payload_size_bytes": None,
                "idempotency_key_header": None,
                "event_id_header": None,
                "delivery_guarantees": "at-least-once",
                "delivery": None,
                "docs_url": "https://developers.asana.com/docs/webhooks-guide",
                "last_introspected_at": _TIMESTAMP,
                "source_extractor_version": "v0.1.0",
                "extraction_method": "llm-assisted",
                "extraction_confidence": confidence,
                "notes": (
                    "Asana webhooks batch multiple events per delivery. "
                    "The X-Hook-Secret handshake occurs on registration; subsequent deliveries use HMAC-SHA256."
                ),
            }


register(AsanaExtractor)

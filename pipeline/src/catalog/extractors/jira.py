"""
jira.py — Jira Cloud webhook extractor (tier-2, llm-assisted).

Scope: Jira Cloud webhooks only (excludes Server/Data Center per scope decision).
Events cover issues, projects, sprints, boards, versions, and user actions.

Source: https://developer.atlassian.com/cloud/jira/platform/webhooks/

compliance: Throttle <=1 req/sec on developer.atlassian.com (throttle.yaml).
docs_url must link to https://developer.atlassian.com/cloud/jira/platform/webhooks/

extraction_method: llm-assisted
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_BASE_DOCS_URL = "https://developer.atlassian.com/cloud/jira/platform/webhooks/"

_ISSUE_PAYLOAD_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "timestamp": {
            "type": "integer",
            "description": "Unix epoch milliseconds when the event occurred.",
        },
        "webhookEvent": {
            "type": "string",
            "description": "The event type identifier (e.g. jira:issue_created).",
        },
        "issue_event_type_name": {
            "type": ["string", "null"],
            "description": "Name of the issue-level event (e.g. issue_assigned, issue_updated).",
        },
        "user": {
            "type": "object",
            "description": "The user who performed the action.",
            "properties": {
                "accountId": {"type": "string", "description": "Atlassian account ID of the user."},
                "displayName": {"type": "string", "description": "Display name of the user."},
                "emailAddress": {"type": ["string", "null"], "description": "Email address if visible."},
            },
        },
        "issue": {
            "type": "object",
            "description": "The issue object that was created or modified.",
            "properties": {
                "id": {"type": "string", "description": "Issue ID."},
                "key": {"type": "string", "description": "Issue key (e.g. PROJ-123)."},
                "fields": {
                    "type": "object",
                    "description": "Issue fields including summary, status, assignee, priority, etc.",
                },
            },
            "required": ["id", "key"],
        },
        "changelog": {
            "type": ["object", "null"],
            "description": "Field changes included when an issue is updated.",
            "properties": {
                "id": {"type": "string", "description": "Changelog entry ID."},
                "items": {
                    "type": "array",
                    "description": "List of field changes.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "field": {"type": "string", "description": "Name of the changed field."},
                            "fieldtype": {"type": "string", "description": "Type of the field (jira, custom)."},
                            "from": {"type": ["string", "null"], "description": "Previous field value ID."},
                            "fromString": {"type": ["string", "null"], "description": "Previous field value string."},
                            "to": {"type": ["string", "null"], "description": "New field value ID."},
                            "toString": {"type": ["string", "null"], "description": "New field value string."},
                        },
                    },
                },
            },
        },
        "comment": {
            "type": ["object", "null"],
            "description": "Comment object included when a comment event occurs.",
            "properties": {
                "id": {"type": "string", "description": "Comment ID."},
                "body": {"type": "string", "description": "Comment body text (may be ADF format)."},
                "author": {"type": "object", "description": "Author of the comment."},
                "created": {"type": "string", "format": "date-time"},
                "updated": {"type": "string", "format": "date-time"},
            },
        },
    },
    "required": ["timestamp", "webhookEvent"],
}

_PROJECT_PAYLOAD_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "timestamp": {"type": "integer", "description": "Unix epoch milliseconds when the event occurred."},
        "webhookEvent": {"type": "string", "description": "The event type identifier."},
        "project": {
            "type": "object",
            "description": "The project object that was created, updated, or deleted.",
            "properties": {
                "id": {"type": "integer", "description": "Project ID."},
                "key": {"type": "string", "description": "Project key."},
                "name": {"type": "string", "description": "Project name."},
                "projectTypeKey": {"type": "string", "description": "Project type (software, business, service_desk)."},
                "lead": {"type": "object", "description": "Project lead user object."},
            },
            "required": ["id", "key"],
        },
    },
    "required": ["timestamp", "webhookEvent"],
}

_SPRINT_PAYLOAD_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "timestamp": {"type": "integer", "description": "Unix epoch milliseconds when the event occurred."},
        "webhookEvent": {"type": "string", "description": "The event type identifier."},
        "sprint": {
            "type": "object",
            "description": "The sprint object.",
            "properties": {
                "id": {"type": "integer", "description": "Sprint ID."},
                "name": {"type": "string", "description": "Sprint name."},
                "state": {"type": "string", "description": "Sprint state: future, active, or closed."},
                "startDate": {"type": ["string", "null"], "format": "date-time"},
                "endDate": {"type": ["string", "null"], "format": "date-time"},
                "originBoardId": {"type": "integer", "description": "ID of the board this sprint belongs to."},
            },
            "required": ["id", "name", "state"],
        },
    },
    "required": ["timestamp", "webhookEvent"],
}

_VERSION_PAYLOAD_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "timestamp": {"type": "integer", "description": "Unix epoch milliseconds when the event occurred."},
        "webhookEvent": {"type": "string", "description": "The event type identifier."},
        "version": {
            "type": "object",
            "description": "The version (release) object.",
            "properties": {
                "id": {"type": "integer", "description": "Version ID."},
                "name": {"type": "string", "description": "Version name."},
                "description": {"type": ["string", "null"], "description": "Version description."},
                "released": {"type": "boolean", "description": "Whether the version has been released."},
                "releaseDate": {"type": ["string", "null"], "description": "Planned or actual release date."},
                "projectId": {"type": "integer", "description": "ID of the project this version belongs to."},
            },
            "required": ["id", "name", "projectId"],
        },
    },
    "required": ["timestamp", "webhookEvent"],
}

# (event_name, payload_schema, trigger_description, confidence)
_EVENTS = [
    (
        "jira:issue_created",
        _ISSUE_PAYLOAD_SCHEMA,
        "A new issue is created in a subscribed Jira Cloud project.",
        0.95,
    ),
    (
        "jira:issue_updated",
        _ISSUE_PAYLOAD_SCHEMA,
        "An existing issue is modified; the changelog lists changed fields.",
        0.95,
    ),
    (
        "jira:issue_deleted",
        _ISSUE_PAYLOAD_SCHEMA,
        "An issue is permanently deleted from a Jira Cloud project.",
        0.90,
    ),
    (
        "worklog_updated",
        _ISSUE_PAYLOAD_SCHEMA,
        "A worklog entry on an issue is added, updated, or deleted.",
        0.85,
    ),
    (
        "comment_created",
        _ISSUE_PAYLOAD_SCHEMA,
        "A new comment is added to an issue.",
        0.90,
    ),
    (
        "comment_updated",
        _ISSUE_PAYLOAD_SCHEMA,
        "An existing comment on an issue is edited.",
        0.90,
    ),
    (
        "comment_deleted",
        _ISSUE_PAYLOAD_SCHEMA,
        "A comment is deleted from an issue.",
        0.85,
    ),
    (
        "project_created",
        _PROJECT_PAYLOAD_SCHEMA,
        "A new project is created in the Jira Cloud instance.",
        0.90,
    ),
    (
        "project_updated",
        _PROJECT_PAYLOAD_SCHEMA,
        "A project's configuration or properties are changed.",
        0.90,
    ),
    (
        "project_deleted",
        _PROJECT_PAYLOAD_SCHEMA,
        "A project is deleted from the Jira Cloud instance.",
        0.85,
    ),
    (
        "project_soft_deleted",
        _PROJECT_PAYLOAD_SCHEMA,
        "A project is moved to the trash (soft delete, restorable).",
        0.80,
    ),
    (
        "project_restored_deleted",
        _PROJECT_PAYLOAD_SCHEMA,
        "A soft-deleted project is restored from the trash.",
        0.80,
    ),
    (
        "sprint_created",
        _SPRINT_PAYLOAD_SCHEMA,
        "A new sprint is created on a board.",
        0.90,
    ),
    (
        "sprint_updated",
        _SPRINT_PAYLOAD_SCHEMA,
        "A sprint's properties (name, dates, goal) are modified.",
        0.85,
    ),
    (
        "sprint_deleted",
        _SPRINT_PAYLOAD_SCHEMA,
        "A sprint is deleted from a board.",
        0.85,
    ),
    (
        "sprint_started",
        _SPRINT_PAYLOAD_SCHEMA,
        "A sprint transitions from future to active state.",
        0.90,
    ),
    (
        "sprint_closed",
        _SPRINT_PAYLOAD_SCHEMA,
        "A sprint is closed and any incomplete issues are moved.",
        0.90,
    ),
    (
        "jira:version_created",
        _VERSION_PAYLOAD_SCHEMA,
        "A new version (release) is created in a project.",
        0.90,
    ),
    (
        "jira:version_updated",
        _VERSION_PAYLOAD_SCHEMA,
        "A version's properties are modified.",
        0.85,
    ),
    (
        "jira:version_deleted",
        _VERSION_PAYLOAD_SCHEMA,
        "A version is deleted from a project.",
        0.85,
    ),
    (
        "jira:version_released",
        _VERSION_PAYLOAD_SCHEMA,
        "A version is marked as released.",
        0.90,
    ),
    (
        "jira:version_unreleased",
        _VERSION_PAYLOAD_SCHEMA,
        "A version is rolled back from released to unreleased state.",
        0.85,
    ),
    (
        "jira:version_moved",
        _VERSION_PAYLOAD_SCHEMA,
        "A version's position in the release sequence is changed.",
        0.75,
    ),
    (
        "user_created",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "timestamp": {"type": "integer", "description": "Unix epoch milliseconds."},
                "webhookEvent": {"type": "string", "description": "Event type identifier."},
                "user": {
                    "type": "object",
                    "description": "The newly created user.",
                    "properties": {
                        "accountId": {"type": "string", "description": "Atlassian account ID."},
                        "displayName": {"type": "string"},
                        "emailAddress": {"type": ["string", "null"]},
                    },
                },
            },
            "required": ["timestamp", "webhookEvent"],
        },
        "A new user account is created or added to the Jira Cloud site.",
        0.85,
    ),
    (
        "user_updated",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "timestamp": {"type": "integer", "description": "Unix epoch milliseconds."},
                "webhookEvent": {"type": "string", "description": "Event type identifier."},
                "user": {
                    "type": "object",
                    "description": "The updated user object.",
                    "properties": {
                        "accountId": {"type": "string"},
                        "displayName": {"type": "string"},
                        "emailAddress": {"type": ["string", "null"]},
                    },
                },
            },
            "required": ["timestamp", "webhookEvent"],
        },
        "A user's profile information is changed on the Jira Cloud site.",
        0.80,
    ),
]


class JiraExtractor(ExtractorBase):
    slug = "jira"
    docs_urls = [
        "https://developer.atlassian.com/cloud/jira/platform/webhooks/",
    ]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, payload_schema, trigger_description, confidence in _EVENTS:
            yield {
                "vendor": "jira",
                "vendor_display_name": "Jira (Cloud)",
                "category": "dev-tools",
                "event_name": event_name,
                "event_namespace": None,
                "trigger_description": trigger_description,
                "payload_schema": payload_schema,
                "required_oauth_scopes": None,
                "required_subscription_event": None,
                "auth_method": "shared-secret-header",
                "signature_header": None,
                "signature_algorithm_detail": (
                    "Jira Cloud webhooks do not include a request signature by default. "
                    "Webhook consumers should use a secret token embedded in the URL "
                    "or restrict inbound IPs to Atlassian ranges."
                ),
                "retry_policy": {
                    "max_attempts": 3,
                    "backoff": "Jira retries failed webhook deliveries up to 3 times.",
                    "total_retry_window": None,
                },
                "max_payload_size_bytes": None,
                "idempotency_key_header": None,
                "event_id_header": None,
                "delivery_guarantees": "at-least-once",
                "delivery": None,
                "docs_url": _BASE_DOCS_URL,
                "last_introspected_at": _TIMESTAMP,
                "source_extractor_version": "v0.1.0",
                "extraction_method": "llm-assisted",
                "extraction_confidence": confidence,
                "notes": "Jira Cloud only; Server/Data Center excluded per scope decision.",
            }


register(JiraExtractor)

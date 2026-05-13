"""
loom.py — Loom webhook extractor (tier-2, llm-assisted).

Scope: Loom webhook events for video lifecycle events (created, updated, deleted, viewed, etc.)

Source: https://dev.loom.com/docs/embed-sdk-docs/reference/webhook-events

extraction_method: llm-assisted
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_DOCS_URL = "https://dev.loom.com/docs/embed-sdk-docs/reference/webhook-events"

def _loom_schema(event_type: str, data_props: dict, required: list[str] | None = None) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "type": {"type": "string", "description": f"Event type: {event_type}."},
            "created_at": {"type": "string", "format": "date-time", "description": "ISO 8601 timestamp when the event was created."},
            "workspace_id": {"type": "string", "description": "Loom workspace ID."},
            "data": {
                "type": "object",
                "description": "Event-specific data payload.",
                "properties": data_props,
                "required": required or [],
            },
        },
        "required": ["type", "created_at", "workspace_id", "data"],
    }

_VIDEO_PROPS = {
    "id": {"type": "string", "description": "Video ID."},
    "title": {"type": ["string", "null"], "description": "Video title."},
    "url": {"type": "string", "description": "Public URL of the video."},
    "owner_id": {"type": "string", "description": "User ID of the video owner."},
    "created_at": {"type": "string", "format": "date-time"},
    "updated_at": {"type": "string", "format": "date-time"},
    "duration": {"type": ["number", "null"], "description": "Video duration in seconds."},
    "visibility": {"type": "string", "enum": ["workspace", "anyone", "private"], "description": "Video visibility setting."},
    "folder_id": {"type": ["string", "null"], "description": "Folder ID if the video is in a folder."},
    "transcription_status": {"type": ["string", "null"], "description": "Status of the video transcription."},
}

# (event_name, schema, trigger_description, confidence)
_EVENTS = [
    (
        "video.created",
        _loom_schema("video.created", _VIDEO_PROPS, ["id", "url", "owner_id"]),
        "A new video is created and uploaded to the Loom workspace.",
        0.90,
    ),
    (
        "video.updated",
        _loom_schema("video.updated", _VIDEO_PROPS, ["id"]),
        "A video's title, description, or settings are changed.",
        0.85,
    ),
    (
        "video.deleted",
        _loom_schema("video.deleted", {"id": {"type": "string", "description": "ID of the deleted video."}, "owner_id": {"type": "string"}}, ["id"]),
        "A video is deleted from the workspace.",
        0.85,
    ),
    (
        "video.viewed",
        _loom_schema("video.viewed", {
            **_VIDEO_PROPS,
            "viewer_id": {"type": ["string", "null"], "description": "User ID of the viewer (null for anonymous)."},
        }, ["id"]),
        "A video is viewed by a user (or an anonymous visitor for public videos).",
        0.80,
    ),
    (
        "video.transcription.completed",
        _loom_schema("video.transcription.completed", {
            **_VIDEO_PROPS,
            "transcription": {"type": "object", "description": "Transcription metadata.", "properties": {
                "status": {"type": "string", "description": "Transcription status (completed)."},
                "language": {"type": ["string", "null"], "description": "Detected language code."},
            }},
        }, ["id"]),
        "Automatic transcription of a video finishes processing.",
        0.85,
    ),
    (
        "video.comment.created",
        _loom_schema("video.comment.created", {
            "video_id": {"type": "string", "description": "ID of the video the comment was posted on."},
            "comment": {
                "type": "object",
                "description": "The comment object.",
                "properties": {
                    "id": {"type": "string", "description": "Comment ID."},
                    "body": {"type": "string", "description": "Comment text."},
                    "author_id": {"type": "string", "description": "User ID of the commenter."},
                    "timestamp": {"type": ["number", "null"], "description": "Video timestamp (seconds) where the comment is placed."},
                    "created_at": {"type": "string", "format": "date-time"},
                },
            },
        }, ["video_id", "comment"]),
        "A comment is posted on a video.",
        0.85,
    ),
    (
        "video.comment.deleted",
        _loom_schema("video.comment.deleted", {
            "video_id": {"type": "string"},
            "comment_id": {"type": "string", "description": "ID of the deleted comment."},
        }, ["video_id", "comment_id"]),
        "A comment is removed from a video.",
        0.80,
    ),
    (
        "folder.created",
        _loom_schema("folder.created", {
            "id": {"type": "string", "description": "Folder ID."},
            "name": {"type": "string", "description": "Folder name."},
            "owner_id": {"type": "string"},
            "parent_folder_id": {"type": ["string", "null"]},
        }, ["id", "name"]),
        "A new folder is created in the workspace.",
        0.80,
    ),
    (
        "folder.updated",
        _loom_schema("folder.updated", {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "owner_id": {"type": "string"},
        }, ["id"]),
        "A folder's name or settings are updated.",
        0.75,
    ),
    (
        "folder.deleted",
        _loom_schema("folder.deleted", {
            "id": {"type": "string", "description": "ID of the deleted folder."},
        }, ["id"]),
        "A folder is deleted from the workspace.",
        0.75,
    ),
]


class LoomExtractor(ExtractorBase):
    slug = "loom"
    docs_urls = [
        "https://dev.loom.com/docs/embed-sdk-docs/reference/webhook-events",
    ]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, payload_schema, trigger_description, confidence in _EVENTS:
            yield {
                "vendor": "loom",
                "vendor_display_name": "Loom",
                "category": "collaboration",
                "event_name": event_name,
                "event_namespace": None,
                "trigger_description": trigger_description,
                "payload_schema": payload_schema,
                "required_oauth_scopes": None,
                "required_subscription_event": None,
                "auth_method": "hmac-sha256",
                "signature_header": "X-Loom-Signature",
                "signature_algorithm_detail": (
                    "HMAC-SHA256 of the raw request body using the webhook signing secret."
                ),
                "retry_policy": {
                    "max_attempts": None,
                    "backoff": "Loom retries failed webhook deliveries.",
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
                    "Loom is now part of Atlassian. Webhook API is available via the Loom Embed SDK. "
                    "Some event details (e.g. viewer_id on video.viewed) may be null for anonymous viewers."
                ),
            }


register(LoomExtractor)

"""
zoom.py — Zoom webhook extractor (tier-2, llm-assisted).

Scope: Zoom event notification webhooks for meetings, webinars, recordings, users, and chat.

Source: https://developers.zoom.us/docs/api/webhooks/

extraction_method: llm-assisted
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_DOCS_URL = "https://developers.zoom.us/docs/api/webhooks/"

def _zoom_schema(event: str, payload_object_desc: str, payload_object_props: dict) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "event": {"type": "string", "description": f"Event type identifier, e.g. '{event}'."},
            "event_ts": {"type": "integer", "description": "Unix timestamp in milliseconds when the event occurred."},
            "payload": {
                "type": "object",
                "description": "Event payload envelope.",
                "properties": {
                    "account_id": {"type": "string", "description": "Zoom account ID."},
                    "operator": {"type": ["string", "null"], "description": "User who triggered the event."},
                    "operator_id": {"type": ["string", "null"], "description": "User ID who triggered the event."},
                    "object": {
                        "type": "object",
                        "description": payload_object_desc,
                        "properties": payload_object_props,
                    },
                },
                "required": ["account_id", "object"],
            },
        },
        "required": ["event", "event_ts", "payload"],
    }

_MEETING_PROPS = {
    "id": {"type": "integer", "description": "Meeting ID."},
    "uuid": {"type": "string", "description": "Unique meeting UUID (changes each occurrence)."},
    "host_id": {"type": "string", "description": "Zoom user ID of the host."},
    "host_email": {"type": ["string", "null"], "description": "Host email address."},
    "topic": {"type": "string", "description": "Meeting topic."},
    "type": {"type": "integer", "description": "Meeting type (1=instant, 2=scheduled, 3=recurring no fixed time, 8=recurring fixed time)."},
    "start_time": {"type": ["string", "null"], "format": "date-time"},
    "duration": {"type": ["integer", "null"], "description": "Meeting duration in minutes."},
    "timezone": {"type": ["string", "null"]},
}

_PARTICIPANT_PROPS = {
    "user_id": {"type": "string", "description": "Participant user ID."},
    "user_name": {"type": "string", "description": "Participant display name."},
    "email": {"type": ["string", "null"]},
    "participant_uuid": {"type": "string", "description": "Unique ID for this participant session."},
    "join_time": {"type": ["string", "null"], "format": "date-time"},
    "leave_time": {"type": ["string", "null"], "format": "date-time"},
    "leave_reason": {"type": ["string", "null"]},
}

_RECORDING_PROPS = {
    "id": {"type": "string", "description": "Recording object ID."},
    "uuid": {"type": "string", "description": "Meeting UUID for this recording."},
    "host_id": {"type": "string", "description": "Host user ID."},
    "host_email": {"type": ["string", "null"]},
    "topic": {"type": "string"},
    "start_time": {"type": "string", "format": "date-time"},
    "duration": {"type": "integer", "description": "Meeting duration in minutes."},
    "recording_count": {"type": "integer"},
    "recording_files": {"type": "array", "description": "Array of recording file objects."},
    "share_url": {"type": ["string", "null"]},
    "total_size": {"type": "integer", "description": "Total recording size in bytes."},
}

_WEBINAR_PROPS = {
    "id": {"type": "integer", "description": "Webinar ID."},
    "uuid": {"type": "string"},
    "host_id": {"type": "string"},
    "topic": {"type": "string"},
    "type": {"type": "integer", "description": "Webinar type (5=webinar, 6=recurring no fixed time, 9=recurring fixed time)."},
    "start_time": {"type": ["string", "null"], "format": "date-time"},
    "duration": {"type": ["integer", "null"]},
    "timezone": {"type": ["string", "null"]},
}

_USER_PROPS = {
    "id": {"type": "string", "description": "Zoom user ID."},
    "email": {"type": "string"},
    "first_name": {"type": ["string", "null"]},
    "last_name": {"type": ["string", "null"]},
    "type": {"type": "integer", "description": "User type (1=Basic, 2=Licensed, 3=On-prem)."},
}

# (event_name, namespace, object_desc, object_props, trigger_description, confidence)
_EVENTS = [
    ("meeting.created", "meeting", "Meeting object created.", _MEETING_PROPS, "A new meeting is scheduled.", 0.90),
    ("meeting.updated", "meeting", "Updated meeting object.", _MEETING_PROPS, "A scheduled meeting's settings are modified.", 0.85),
    ("meeting.deleted", "meeting", "Deleted meeting object.", _MEETING_PROPS, "A scheduled meeting is deleted.", 0.85),
    ("meeting.started", "meeting", "Meeting that has started.", _MEETING_PROPS, "A meeting transitions to started state when the host or a participant joins.", 0.90),
    ("meeting.ended", "meeting", "Meeting that ended.", _MEETING_PROPS, "A meeting session ends.", 0.90),
    ("meeting.participant_joined", "meeting", "Participant who joined.", {**_MEETING_PROPS, "participant": {"type": "object", "description": "Joining participant.", "properties": _PARTICIPANT_PROPS}},
     "A participant joins a running meeting.", 0.90),
    ("meeting.participant_left", "meeting", "Participant who left.", {**_MEETING_PROPS, "participant": {"type": "object", "description": "Leaving participant.", "properties": _PARTICIPANT_PROPS}},
     "A participant leaves a meeting.", 0.90),
    ("meeting.registration_created", "meeting", "Meeting with new registrant.", _MEETING_PROPS,
     "A user registers for a meeting that requires registration.", 0.85),
    ("meeting.registration_approved", "meeting", "Meeting with approved registrant.", _MEETING_PROPS,
     "A meeting registration is approved.", 0.85),
    ("recording.completed", "recording", "Completed cloud recording object.", _RECORDING_PROPS,
     "A cloud recording finishes processing and is available.", 0.90),
    ("recording.started", "recording", "Recording object when started.", {**_MEETING_PROPS},
     "Cloud recording starts for a meeting.", 0.85),
    ("recording.stopped", "recording", "Recording object when stopped.", {**_MEETING_PROPS},
     "Cloud recording is stopped for a meeting.", 0.85),
    ("recording.deleted", "recording", "Deleted recording object.", _RECORDING_PROPS,
     "A cloud recording is moved to trash.", 0.85),
    ("recording.registration_completed", "recording", "Recording with new registrant.", _RECORDING_PROPS,
     "A user registers to view an on-demand recording.", 0.80),
    ("webinar.created", "webinar", "Created webinar object.", _WEBINAR_PROPS, "A new webinar is scheduled.", 0.90),
    ("webinar.updated", "webinar", "Updated webinar object.", _WEBINAR_PROPS, "A webinar's settings are modified.", 0.85),
    ("webinar.deleted", "webinar", "Deleted webinar object.", _WEBINAR_PROPS, "A webinar is deleted.", 0.85),
    ("webinar.started", "webinar", "Webinar that started.", _WEBINAR_PROPS, "A webinar session begins.", 0.90),
    ("webinar.ended", "webinar", "Webinar that ended.", _WEBINAR_PROPS, "A webinar session ends.", 0.90),
    ("user.created", "user", "Created user object.", _USER_PROPS, "A new user is added to the Zoom account.", 0.90),
    ("user.updated", "user", "Updated user object.", _USER_PROPS, "A user's profile details are changed.", 0.85),
    ("user.deleted", "user", "Deleted user object.", _USER_PROPS, "A user is removed from the Zoom account.", 0.85),
    ("user.deactivated", "user", "Deactivated user.", _USER_PROPS, "A user's account is deactivated.", 0.85),
    ("user.activated", "user", "Activated user.", _USER_PROPS, "A previously deactivated user account is reactivated.", 0.85),
]


class ZoomExtractor(ExtractorBase):
    slug = "zoom"
    docs_urls = [
        "https://developers.zoom.us/docs/api/webhooks/",
    ]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, namespace, obj_desc, obj_props, trigger_description, confidence in _EVENTS:
            yield {
                "vendor": "zoom",
                "vendor_display_name": "Zoom",
                "category": "collaboration",
                "event_name": event_name,
                "event_namespace": namespace,
                "trigger_description": trigger_description,
                "payload_schema": _zoom_schema(event_name, obj_desc, obj_props),
                "required_oauth_scopes": None,
                "required_subscription_event": None,
                "auth_method": "hmac-sha256",
                "signature_header": "x-zm-signature",
                "signature_algorithm_detail": (
                    "HMAC-SHA256 computed over 'v0:' + timestamp + ':' + raw body. "
                    "Timestamp is in the x-zm-request-timestamp header."
                ),
                "retry_policy": {
                    "max_attempts": None,
                    "backoff": "Zoom retries failed webhook deliveries.",
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


register(ZoomExtractor)

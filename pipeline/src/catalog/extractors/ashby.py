"""
ashby.py — Ashby ATS webhook extractor (tier-2, llm-assisted).

Scope: Ashby webhook events covering applications, candidates, interviews, offers, jobs, and job postings.

Source: https://developers.ashbyhq.com/docs/webhooks

extraction_method: llm-assisted
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_DOCS_URL = "https://developers.ashbyhq.com/docs/webhooks"

def _ashby_schema(event_type: str, data_props: dict, required: list[str] | None = None) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "eventType": {"type": "string", "description": f"Webhook event type: {event_type}."},
            "createdAt": {"type": "string", "format": "date-time", "description": "ISO 8601 timestamp when the event was created."},
            "data": {
                "type": "object",
                "description": "Event-specific payload.",
                "properties": data_props,
                "required": required or [],
            },
        },
        "required": ["eventType", "createdAt", "data"],
    }

_APPLICATION_PROPS = {
    "id": {"type": "string", "description": "Application ID."},
    "candidateId": {"type": "string", "description": "Candidate ID."},
    "jobId": {"type": "string", "description": "Job ID."},
    "jobPostingId": {"type": ["string", "null"]},
    "status": {"type": "string", "enum": ["active", "archived", "hired", "converted_to_lead"]},
    "createdAt": {"type": "string", "format": "date-time"},
    "updatedAt": {"type": "string", "format": "date-time"},
    "currentInterviewStage": {
        "type": ["object", "null"],
        "description": "Current stage in the interview pipeline.",
        "properties": {
            "id": {"type": "string"},
            "title": {"type": "string"},
            "type": {"type": "string"},
        },
    },
    "archiveReason": {"type": ["object", "null"]},
    "hiringTeam": {"type": ["object", "null"]},
    "source": {"type": ["object", "null"]},
}

_CANDIDATE_PROPS = {
    "id": {"type": "string", "description": "Candidate ID."},
    "name": {"type": "string"},
    "primaryEmailAddress": {
        "type": ["object", "null"],
        "description": "Primary email address object.",
        "properties": {
            "value": {"type": "string"},
            "type": {"type": "string"},
        },
    },
    "phoneNumbers": {"type": "array", "description": "Candidate phone numbers."},
    "socialLinks": {"type": "array"},
    "tags": {"type": "array"},
    "createdAt": {"type": "string", "format": "date-time"},
    "updatedAt": {"type": "string", "format": "date-time"},
    "isDoNotContact": {"type": "boolean"},
}

_INTERVIEW_PROPS = {
    "id": {"type": "string", "description": "Interview event ID."},
    "applicationId": {"type": "string"},
    "candidateId": {"type": "string"},
    "interviewType": {"type": "object", "description": "Interview type details."},
    "status": {"type": "string", "enum": ["scheduled", "complete", "cancelled", "no_show", "needs_scheduling"]},
    "startTime": {"type": ["string", "null"], "format": "date-time"},
    "endTime": {"type": ["string", "null"], "format": "date-time"},
    "interviewers": {"type": "array", "description": "Array of interviewer objects."},
    "location": {"type": ["string", "null"]},
    "videoConferencingUrl": {"type": ["string", "null"]},
    "createdAt": {"type": "string", "format": "date-time"},
    "updatedAt": {"type": "string", "format": "date-time"},
}

_OFFER_PROPS = {
    "id": {"type": "string"},
    "applicationId": {"type": "string"},
    "version": {"type": "integer", "description": "Offer version number."},
    "status": {"type": "string", "enum": ["draft", "extended", "signed", "rescinded", "declined"]},
    "createdAt": {"type": "string", "format": "date-time"},
    "updatedAt": {"type": "string", "format": "date-time"},
    "offerLetterUrl": {"type": ["string", "null"]},
    "offerFields": {"type": "array", "description": "Array of offer field values."},
}

_JOB_PROPS = {
    "id": {"type": "string"},
    "title": {"type": "string"},
    "status": {"type": "string", "enum": ["draft", "open", "paused", "closed", "archived"]},
    "department": {"type": ["object", "null"]},
    "location": {"type": ["object", "null"]},
    "hiringTeam": {"type": "object"},
    "openings": {"type": "array", "description": "Array of job opening objects."},
    "customFields": {"type": "array"},
    "createdAt": {"type": "string", "format": "date-time"},
    "updatedAt": {"type": "string", "format": "date-time"},
}

_JOB_POSTING_PROPS = {
    "id": {"type": "string"},
    "jobId": {"type": "string"},
    "title": {"type": "string"},
    "status": {"type": "string", "enum": ["draft", "published", "unpublished", "archived"]},
    "locationIds": {"type": "array"},
    "applyUrl": {"type": ["string", "null"]},
    "publishedDate": {"type": ["string", "null"], "format": "date-time"},
    "createdAt": {"type": "string", "format": "date-time"},
    "updatedAt": {"type": "string", "format": "date-time"},
}

_SURVEY_PROPS = {
    "id": {"type": "string"},
    "applicationId": {"type": "string"},
    "candidateId": {"type": "string"},
    "surveyType": {"type": "string", "description": "Type of survey (e.g. candidate experience, offer, exit)."},
    "submittedAt": {"type": "string", "format": "date-time"},
    "responses": {"type": "array", "description": "Array of survey response objects."},
}

# (event_name, data_props, required, trigger_description, confidence)
_EVENTS = [
    ("application.created", _APPLICATION_PROPS, ["id", "candidateId", "jobId"],
     "A new application is submitted or created for a job.", 0.90),
    ("application.updated", _APPLICATION_PROPS, ["id"],
     "An application's properties are modified.", 0.85),
    ("application.stage_changed", {**_APPLICATION_PROPS, "previousInterviewStage": {"type": ["object", "null"]}},
     ["id", "currentInterviewStage"],
     "An application moves to a different interview stage.", 0.90),
    ("application.hired", _APPLICATION_PROPS, ["id", "status"],
     "An application's status transitions to hired.", 0.90),
    ("application.archived", {**_APPLICATION_PROPS, "archiveReason": {"type": ["object", "null"]}},
     ["id", "status"],
     "An application is archived (typically when a candidate is rejected or withdrawn).", 0.90),
    ("candidate.created", _CANDIDATE_PROPS, ["id", "name"],
     "A new candidate record is created.", 0.90),
    ("candidate.updated", _CANDIDATE_PROPS, ["id"],
     "A candidate's profile information is updated.", 0.85),
    ("candidate.deleted", {"id": {"type": "string"}}, ["id"],
     "A candidate record is deleted.", 0.80),
    ("candidate.merged", {
        "winnerId": {"type": "string", "description": "ID of the remaining candidate after merge."},
        "loserId": {"type": "string", "description": "ID of the merged-away candidate."},
    }, ["winnerId", "loserId"],
     "Two candidate records are merged.", 0.80),
    ("interview.created", _INTERVIEW_PROPS, ["id", "applicationId"],
     "An interview event is scheduled for an application.", 0.90),
    ("interview.updated", _INTERVIEW_PROPS, ["id"],
     "An interview's details are changed.", 0.85),
    ("interview.deleted", {"id": {"type": "string"}, "applicationId": {"type": "string"}}, ["id"],
     "A scheduled interview is cancelled and deleted.", 0.85),
    ("offer.created", _OFFER_PROPS, ["id", "applicationId"],
     "A new offer is created for an application.", 0.90),
    ("offer.updated", _OFFER_PROPS, ["id"],
     "An offer's details or status are changed.", 0.85),
    ("job.created", _JOB_PROPS, ["id", "title"],
     "A new job requisition is created.", 0.90),
    ("job.updated", _JOB_PROPS, ["id"],
     "A job's details or status are changed.", 0.85),
    ("job.deleted", {"id": {"type": "string"}}, ["id"],
     "A job is deleted.", 0.80),
    ("jobPosting.created", _JOB_POSTING_PROPS, ["id", "jobId"],
     "A new job posting is created (may be in draft or published).", 0.85),
    ("jobPosting.updated", _JOB_POSTING_PROPS, ["id"],
     "A job posting's content or status is updated.", 0.80),
    ("jobPosting.deleted", {"id": {"type": "string"}, "jobId": {"type": "string"}}, ["id"],
     "A job posting is deleted.", 0.80),
    ("survey.submitted", _SURVEY_PROPS, ["id", "applicationId"],
     "A candidate survey is submitted.", 0.80),
]


class AshbyExtractor(ExtractorBase):
    slug = "ashby"
    docs_urls = [
        "https://developers.ashbyhq.com/docs/webhooks",
    ]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, data_props, required, trigger_description, confidence in _EVENTS:
            yield {
                "vendor": "ashby",
                "vendor_display_name": "Ashby",
                "category": "ats",
                "event_name": event_name,
                "event_namespace": event_name.split(".")[0],
                "trigger_description": trigger_description,
                "payload_schema": _ashby_schema(event_name, data_props, required),
                "required_oauth_scopes": None,
                "required_subscription_event": None,
                "auth_method": "hmac-sha256",
                "signature_header": "X-Ashby-Signature",
                "signature_algorithm_detail": (
                    "HMAC-SHA256 of the raw request body using the webhook's secret key."
                ),
                "retry_policy": {
                    "max_attempts": None,
                    "backoff": "Ashby retries failed webhook deliveries.",
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


register(AshbyExtractor)

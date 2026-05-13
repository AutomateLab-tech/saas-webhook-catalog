"""
greenhouse.py — Greenhouse webhook extractor (tier-2, llm-assisted).

Scope: Greenhouse Harvest API webhook events covering candidate, application,
       interview, offer, and job management workflows.

Source: https://developers.greenhouse.io/webhooks.html

extraction_method: llm-assisted
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_DOCS_URL = "https://developers.greenhouse.io/webhooks.html"

def _gh_schema(action: str, object_type: str, object_props: dict) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": f"The webhook action, e.g. '{action}'.",
            },
            "payload": {
                "type": "object",
                "description": f"The {object_type} object that was affected.",
                "properties": object_props,
            },
        },
        "required": ["action", "payload"],
    }

_CANDIDATE_PROPS = {
    "id": {"type": "integer", "description": "Candidate ID."},
    "first_name": {"type": "string"},
    "last_name": {"type": "string"},
    "company": {"type": ["string", "null"]},
    "title": {"type": ["string", "null"]},
    "created_at": {"type": "string", "format": "date-time"},
    "updated_at": {"type": "string", "format": "date-time"},
    "last_activity": {"type": ["string", "null"], "format": "date-time"},
    "is_private": {"type": "boolean"},
    "photo_url": {"type": ["string", "null"]},
    "can_email": {"type": "boolean"},
    "tags": {"type": "array", "items": {"type": "string"}},
    "recruiter": {"type": ["object", "null"], "description": "Assigned recruiter."},
    "coordinator": {"type": ["object", "null"], "description": "Assigned coordinator."},
    "applications": {"type": "array", "description": "List of application objects."},
    "educations": {"type": "array", "description": "Education history entries."},
    "employments": {"type": "array", "description": "Employment history entries."},
    "phone_numbers": {"type": "array", "description": "Candidate phone numbers."},
    "email_addresses": {"type": "array", "description": "Candidate email addresses."},
    "website_addresses": {"type": "array", "description": "Candidate website/portfolio links."},
    "social_media_addresses": {"type": "array", "description": "Social media profile links."},
}

_APPLICATION_PROPS = {
    "id": {"type": "integer", "description": "Application ID."},
    "candidate_id": {"type": "integer", "description": "ID of the candidate."},
    "job_id": {"type": "integer", "description": "ID of the job."},
    "status": {"type": "string", "description": "Application status (active, rejected, hired)."},
    "stage": {"type": ["object", "null"], "description": "Current pipeline stage."},
    "current_stage": {"type": ["object", "null"], "description": "Current stage object."},
    "applied_at": {"type": ["string", "null"], "format": "date-time"},
    "rejected_at": {"type": ["string", "null"], "format": "date-time"},
    "last_activity_at": {"type": ["string", "null"], "format": "date-time"},
    "source": {"type": ["object", "null"], "description": "Application source (referral, job board, etc.)."},
    "credited_to": {"type": ["object", "null"], "description": "Person credited for the hire."},
    "rejection_reason": {"type": ["object", "null"]},
    "prospect": {"type": "boolean", "description": "Whether this is a prospect (not yet applied)."},
}

_OFFER_PROPS = {
    "id": {"type": "integer", "description": "Offer ID."},
    "application_id": {"type": "integer"},
    "created_at": {"type": "string", "format": "date-time"},
    "updated_at": {"type": "string", "format": "date-time"},
    "sent_at": {"type": ["string", "null"], "format": "date-time"},
    "resolved_at": {"type": ["string", "null"], "format": "date-time"},
    "starts_at": {"type": ["string", "null"], "description": "Proposed start date."},
    "status": {"type": "string", "description": "Offer status (unresolved, accepted, rejected, deprecated)."},
    "candidate": {"type": "object", "description": "Candidate object."},
    "opening": {"type": ["object", "null"], "description": "Job opening this offer belongs to."},
}

_INTERVIEW_PROPS = {
    "id": {"type": "integer", "description": "Scheduled interview ID."},
    "application_id": {"type": "integer"},
    "start": {"type": "object", "description": "Start time object with date_time field."},
    "end": {"type": "object", "description": "End time object with date_time field."},
    "location": {"type": ["string", "null"]},
    "video_conferencing_url": {"type": ["string", "null"]},
    "status": {"type": "string", "description": "Interview status (awaiting_feedback, complete, scheduled, to_be_scheduled)."},
    "interviewers": {"type": "array", "description": "Array of interviewer objects."},
    "interview": {"type": "object", "description": "The interview stage definition."},
}

_JOB_PROPS = {
    "id": {"type": "integer", "description": "Job ID."},
    "name": {"type": "string", "description": "Job title."},
    "status": {"type": "string", "description": "Job status (open, closed, draft)."},
    "created_at": {"type": "string", "format": "date-time"},
    "updated_at": {"type": "string", "format": "date-time"},
    "opened_at": {"type": ["string", "null"], "format": "date-time"},
    "closed_at": {"type": ["string", "null"], "format": "date-time"},
    "departments": {"type": "array", "description": "Departments for this job."},
    "offices": {"type": "array", "description": "Offices for this job."},
    "hiring_team": {"type": "object", "description": "Hiring team members."},
    "openings": {"type": "array", "description": "Individual job openings (headcount)."},
}

_DELETION_PROPS = {
    "id": {"type": "integer", "description": "ID of the deleted resource."},
}

# (event_name, action, object_type, schema, trigger_description, confidence)
_EVENTS = [
    # Application events
    ("new_candidate_application", "new_candidate_application", "application", _gh_schema("new_candidate_application", "application", _APPLICATION_PROPS),
     "A new application is added to a job (may be by recruiter or submitted by the candidate).", 0.90),
    ("delete_application", "delete_application", "application", _gh_schema("delete_application", "application", _DELETION_PROPS),
     "An application is deleted.", 0.90),
    ("application_updated", "application_updated", "application", _gh_schema("application_updated", "application", _APPLICATION_PROPS),
     "An application's details or status are updated.", 0.90),
    ("offer_created", "offer_created", "offer", _gh_schema("offer_created", "offer", _OFFER_PROPS),
     "A new offer is created for an application.", 0.90),
    ("offer_approved", "offer_approved", "offer", _gh_schema("offer_approved", "offer", _OFFER_PROPS),
     "An offer is approved; also fires when a candidate accepts an offer (marking it accepted).", 0.90),
    ("offer_updated", "offer_updated", "offer", _gh_schema("offer_updated", "offer", _OFFER_PROPS),
     "An offer's details are modified.", 0.85),
    ("offer_deleted", "offer_deleted", "offer", _gh_schema("offer_deleted", "offer", _DELETION_PROPS),
     "An offer is deleted.", 0.80),
    ("new_prospect_application", "new_prospect_application", "application", _gh_schema("new_prospect_application", "application", _APPLICATION_PROPS),
     "A new prospect record is created (candidate not yet applied to a specific job).", 0.90),
    # Candidate events
    ("delete_candidate", "delete_candidate", "candidate", _gh_schema("delete_candidate", "candidate", _DELETION_PROPS),
     "A candidate record is permanently deleted.", 0.90),
    ("hire_candidate", "hire_candidate", "candidate", _gh_schema("hire_candidate", "candidate", _APPLICATION_PROPS),
     "A candidate is moved to the Hired stage.", 0.90),
    ("merge_candidate", "merge_candidate", "candidate", _gh_schema("merge_candidate", "candidate", {
        "winner": {"type": "object", "description": "The candidate record that was kept."},
        "loser": {"type": "object", "description": "The candidate record that was merged away."},
    }), "Two duplicate candidate records are merged into one.", 0.85),
    ("candidate_stage_change", "candidate_stage_change", "application", _gh_schema("candidate_stage_change", "application", _APPLICATION_PROPS),
     "An application moves to a different pipeline stage.", 0.90),
    ("unhire_candidate", "unhire_candidate", "candidate", _gh_schema("unhire_candidate", "candidate", _APPLICATION_PROPS),
     "A previously hired candidate is marked as not hired.", 0.85),
    ("reject_candidate", "reject_candidate", "application", _gh_schema("reject_candidate", "application", _APPLICATION_PROPS),
     "A candidate's application is rejected.", 0.90),
    ("unreject_candidate", "unreject_candidate", "application", _gh_schema("unreject_candidate", "application", _APPLICATION_PROPS),
     "A previously rejected application is reopened.", 0.85),
    ("update_candidate", "update_candidate", "candidate", _gh_schema("update_candidate", "candidate", _CANDIDATE_PROPS),
     "A candidate's profile information is updated.", 0.85),
    ("candidate_anonymized", "candidate_anonymized", "candidate", _gh_schema("candidate_anonymized", "candidate", _DELETION_PROPS),
     "A candidate's personal information is anonymized.", 0.85),
    # Interview events
    ("interview_deleted", "interview_deleted", "interview", _gh_schema("interview_deleted", "interview", _DELETION_PROPS),
     "A scheduled interview is deleted.", 0.90),
    ("scorecard_deleted", "scorecard_deleted", "scorecard", _gh_schema("scorecard_deleted", "scorecard", _DELETION_PROPS),
     "An individual interviewer scorecard is deleted.", 0.90),
    # Job events
    ("job_created", "job_created", "job", _gh_schema("job_created", "job", _JOB_PROPS),
     "A new job requisition is created.", 0.90),
    ("job_deleted", "job_deleted", "job", _gh_schema("job_deleted", "job", _DELETION_PROPS),
     "A job is deleted.", 0.85),
    ("job_updated", "job_updated", "job", _gh_schema("job_updated", "job", _JOB_PROPS),
     "A job's details (title, department, status, etc.) are changed.", 0.85),
    ("job_approved", "job_approved", "job", _gh_schema("job_approved", "job", _JOB_PROPS),
     "A job requisition is approved.", 0.85),
    ("job_post_created", "job_post_created", "job", _gh_schema("job_post_created", "job", _JOB_PROPS),
     "A new job posting is created.", 0.85),
    ("job_post_updated", "job_post_updated", "job", _gh_schema("job_post_updated", "job", _JOB_PROPS),
     "A job posting's content or settings are updated.", 0.85),
    ("job_post_deleted", "job_post_deleted", "job", _gh_schema("job_post_deleted", "job", _DELETION_PROPS),
     "A job posting is deleted.", 0.85),
    ("job_interview_stage_deleted", "job_interview_stage_deleted", "job", _gh_schema("job_interview_stage_deleted", "job", _DELETION_PROPS),
     "An interview stage is removed from a job's pipeline.", 0.85),
    # Organization events
    ("department_deleted", "department_deleted", "department", _gh_schema("department_deleted", "department", _DELETION_PROPS),
     "A department is deleted.", 0.85),
    ("office_deleted", "office_deleted", "office", _gh_schema("office_deleted", "office", _DELETION_PROPS),
     "An office is deleted.", 0.85),
]


class GreenhouseExtractor(ExtractorBase):
    slug = "greenhouse"
    docs_urls = [
        "https://developers.greenhouse.io/webhooks.html",
    ]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, action, obj_type, payload_schema, trigger_description, confidence in _EVENTS:
            yield {
                "vendor": "greenhouse",
                "vendor_display_name": "Greenhouse",
                "category": "ats",
                "event_name": event_name,
                "event_namespace": obj_type,
                "trigger_description": trigger_description,
                "payload_schema": payload_schema,
                "required_oauth_scopes": None,
                "required_subscription_event": None,
                "auth_method": "hmac-sha256",
                "signature_header": "Signature",
                "signature_algorithm_detail": (
                    "HMAC-SHA256 digest of the request body signed with the webhook secret key. "
                    "Header format: 'sha256 <hexdigest>'."
                ),
                "retry_policy": {
                    "max_attempts": None,
                    "backoff": "Greenhouse retries webhook deliveries. Exact backoff not documented.",
                    "total_retry_window": None,
                },
                "max_payload_size_bytes": None,
                "idempotency_key_header": None,
                "event_id_header": "Greenhouse-Event-ID",
                "delivery_guarantees": "at-least-once",
                "delivery": None,
                "docs_url": _DOCS_URL,
                "last_introspected_at": _TIMESTAMP,
                "source_extractor_version": "v0.1.0",
                "extraction_method": "llm-assisted",
                "extraction_confidence": confidence,
                "notes": None,
            }


register(GreenhouseExtractor)

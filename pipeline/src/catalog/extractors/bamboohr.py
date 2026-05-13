"""
bamboohr.py — BambooHR webhook extractor (tier-2, llm-assisted).

Scope: BambooHR employee data change webhooks for HR lifecycle events.

Source: https://documentation.bamboohr.com/docs/getting-started-with-webhooks

extraction_method: llm-assisted
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_DOCS_URL = "https://documentation.bamboohr.com/docs/getting-started-with-webhooks"

def _bhr_schema(event_type: str, field_changes_desc: str) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "webhookId": {"type": "integer", "description": "ID of the webhook configuration."},
            "eventType": {"type": "string", "description": f"Event type: {event_type}."},
            "companyDomain": {"type": "string", "description": "The BambooHR company subdomain."},
            "employees": {
                "type": "array",
                "description": "Array of employee change objects.",
                "items": {
                    "type": "object",
                    "properties": {
                        "employeeId": {"type": "integer", "description": "BambooHR employee ID."},
                        "fields": {
                            "type": "object",
                            "description": field_changes_desc,
                            "additionalProperties": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string", "description": "BambooHR field ID."},
                                    "name": {"type": "string", "description": "Field name."},
                                    "value": {"type": ["string", "null"], "description": "New field value."},
                                    "valueOld": {"type": ["string", "null"], "description": "Previous value (included on change events)."},
                                },
                            },
                        },
                    },
                    "required": ["employeeId"],
                },
            },
        },
        "required": ["webhookId", "eventType", "companyDomain", "employees"],
    }

# (event_name, trigger_description, confidence)
_EVENTS = [
    (
        "changed",
        _bhr_schema("changed", "Fields that changed on this employee, keyed by field ID."),
        "One or more monitored fields on an employee record are changed.",
        0.90,
    ),
    (
        "hired",
        _bhr_schema("hired", "Fields for the newly hired employee."),
        "A new employee is added to BambooHR (hire event).",
        0.90,
    ),
    (
        "terminated",
        _bhr_schema("terminated", "Fields for the terminated employee including termination details."),
        "An employee's status is changed to terminated.",
        0.85,
    ),
    (
        "department_changed",
        _bhr_schema("department_changed", "Fields showing the new and previous department values."),
        "An employee is moved to a different department.",
        0.85,
    ),
    (
        "job_title_changed",
        _bhr_schema("job_title_changed", "Fields showing the new and previous job title values."),
        "An employee's job title is changed.",
        0.85,
    ),
    (
        "compensation_changed",
        _bhr_schema("compensation_changed", "Fields showing the updated compensation details."),
        "An employee's compensation (salary or hourly rate) is updated.",
        0.80,
    ),
    (
        "manager_changed",
        _bhr_schema("manager_changed", "Fields showing the new and previous manager."),
        "An employee's reporting manager is changed.",
        0.85,
    ),
    (
        "location_changed",
        _bhr_schema("location_changed", "Fields showing the new and previous location."),
        "An employee's work location is changed.",
        0.80,
    ),
    (
        "employment_status_changed",
        _bhr_schema("employment_status_changed", "Fields showing the employment status change (e.g. full-time to part-time)."),
        "An employee's employment status type is changed.",
        0.80,
    ),
    (
        "time_off.approved",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "webhookId": {"type": "integer"},
                "eventType": {"type": "string"},
                "companyDomain": {"type": "string"},
                "employees": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "employeeId": {"type": "integer"},
                            "timeOff": {
                                "type": "object",
                                "description": "Time off request that was approved.",
                                "properties": {
                                    "id": {"type": "integer"},
                                    "type": {"type": "string"},
                                    "startDate": {"type": "string"},
                                    "endDate": {"type": "string"},
                                    "amount": {"type": "number"},
                                    "units": {"type": "string"},
                                    "status": {"type": "string"},
                                },
                            },
                        },
                        "required": ["employeeId"],
                    },
                },
            },
            "required": ["webhookId", "eventType", "companyDomain", "employees"],
        },
        "A time off request is approved.",
        0.75,
    ),
    (
        "time_off.denied",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "webhookId": {"type": "integer"},
                "eventType": {"type": "string"},
                "companyDomain": {"type": "string"},
                "employees": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "employeeId": {"type": "integer"},
                            "timeOff": {
                                "type": "object",
                                "description": "Time off request that was denied.",
                                "properties": {
                                    "id": {"type": "integer"},
                                    "type": {"type": "string"},
                                    "startDate": {"type": "string"},
                                    "endDate": {"type": "string"},
                                    "status": {"type": "string"},
                                },
                            },
                        },
                        "required": ["employeeId"],
                    },
                },
            },
            "required": ["webhookId", "eventType", "companyDomain", "employees"],
        },
        "A time off request is denied.",
        0.75,
    ),
    (
        "training_completed",
        _bhr_schema("training_completed", "Fields showing the completed training details."),
        "An employee completes a training record.",
        0.70,
    ),
    (
        "document_changed",
        _bhr_schema("document_changed", "Fields indicating which document category changed."),
        "A document in an employee's file is uploaded or updated.",
        0.70,
    ),
]


class BambooHRExtractor(ExtractorBase):
    slug = "bamboohr"
    docs_urls = [
        "https://documentation.bamboohr.com/docs/getting-started-with-webhooks",
    ]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, payload_schema, trigger_description, confidence in _EVENTS:
            yield {
                "vendor": "bamboohr",
                "vendor_display_name": "BambooHR",
                "category": "hris",
                "event_name": event_name,
                "event_namespace": None,
                "trigger_description": trigger_description,
                "payload_schema": payload_schema,
                "required_oauth_scopes": None,
                "required_subscription_event": None,
                "auth_method": "hmac-sha256",
                "signature_header": "X-BambooHR-Signature",
                "signature_algorithm_detail": (
                    "HMAC-SHA256 of the raw request body using the webhook's private key."
                ),
                "retry_policy": {
                    "max_attempts": None,
                    "backoff": "BambooHR retries failed webhook deliveries.",
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
                    "BambooHR webhook events are configured per-monitored-field. "
                    "The 'changed' event covers all user-configured field monitors. "
                    "Some events (time_off, training, documents) may require specific BambooHR plan tiers."
                ),
            }


register(BambooHRExtractor)

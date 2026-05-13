"""
gusto.py — Gusto Embedded Payroll webhook extractor (tier-2, llm-assisted).

Scope: Gusto Embedded Payroll webhook events for employees, payrolls, contractors,
       companies, and benefits.

Source: https://docs.gusto.com/embedded-payroll/docs/webhooks-overview

extraction_method: llm-assisted
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_DOCS_URL = "https://docs.gusto.com/embedded-payroll/docs/webhooks-overview"

def _gusto_schema(event_type: str, entity_type: str, entity_props: dict, required: list[str] | None = None) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "event_type": {"type": "string", "description": f"Event type: {event_type}."},
            "resource": {
                "type": "object",
                "description": "Resource metadata.",
                "properties": {
                    "uuid": {"type": "string", "description": "UUID of the affected resource."},
                    "type": {"type": "string", "description": f"Resource type: {entity_type}."},
                    "url": {"type": "string", "description": "API URL of the resource."},
                },
                "required": ["uuid", "type"],
            },
            "entity_uuid": {"type": "string", "description": "UUID of the entity (company, etc.) that owns the resource."},
            "timestamp": {"type": "string", "format": "date-time", "description": "ISO 8601 timestamp when the event occurred."},
            "entity_attributes": {
                "type": "object",
                "description": f"Key attributes of the {entity_type} at the time of the event.",
                "properties": entity_props,
                "required": required or [],
            },
        },
        "required": ["event_type", "resource", "timestamp"],
    }

_EMPLOYEE_PROPS = {
    "uuid": {"type": "string", "description": "Employee UUID."},
    "first_name": {"type": "string"},
    "last_name": {"type": "string"},
    "email": {"type": ["string", "null"]},
    "company_uuid": {"type": "string"},
    "onboarding_status": {"type": ["string", "null"]},
    "start_date": {"type": ["string", "null"]},
    "termination_date": {"type": ["string", "null"]},
    "is_terminated": {"type": "boolean"},
}

_CONTRACTOR_PROPS = {
    "uuid": {"type": "string"},
    "company_uuid": {"type": "string"},
    "type": {"type": "string", "enum": ["Individual", "Business"]},
    "first_name": {"type": ["string", "null"]},
    "last_name": {"type": ["string", "null"]},
    "business_name": {"type": ["string", "null"]},
    "email": {"type": ["string", "null"]},
    "start_date": {"type": ["string", "null"]},
}

_PAYROLL_PROPS = {
    "uuid": {"type": "string"},
    "company_uuid": {"type": "string"},
    "pay_period": {
        "type": "object",
        "description": "Pay period covered by this payroll run.",
        "properties": {
            "start_date": {"type": "string"},
            "end_date": {"type": "string"},
            "pay_schedule_uuid": {"type": "string"},
        },
    },
    "check_date": {"type": ["string", "null"], "description": "Date checks are issued."},
    "processed": {"type": "boolean", "description": "Whether this payroll has been processed."},
    "totals": {
        "type": ["object", "null"],
        "description": "Payroll total amounts.",
        "properties": {
            "company_debit": {"type": "string"},
            "employee_bonuses": {"type": "string"},
            "net_pay": {"type": "string"},
            "gross_pay": {"type": "string"},
            "employee_taxes": {"type": "string"},
            "employer_taxes": {"type": "string"},
        },
    },
}

_COMPANY_PROPS = {
    "uuid": {"type": "string", "description": "Company UUID."},
    "name": {"type": "string"},
    "ein": {"type": ["string", "null"], "description": "Employer Identification Number."},
    "entity_type": {"type": ["string", "null"]},
}

# (event_name, entity_type, entity_props, required, trigger_description, confidence)
_EVENTS = [
    ("employee.created", "Employee", _EMPLOYEE_PROPS, ["uuid", "company_uuid"],
     "A new employee is created in the company.", 0.90),
    ("employee.updated", "Employee", _EMPLOYEE_PROPS, ["uuid"],
     "An employee's profile or information is updated.", 0.85),
    ("employee.onboarded", "Employee", _EMPLOYEE_PROPS, ["uuid"],
     "An employee completes onboarding.", 0.85),
    ("employee.terminated", "Employee", _EMPLOYEE_PROPS, ["uuid", "is_terminated"],
     "An employee is marked as terminated in the system.", 0.90),
    ("employee.termination_cancelled", "Employee", _EMPLOYEE_PROPS, ["uuid"],
     "A previously submitted employee termination is cancelled.", 0.80),
    ("contractor.created", "Contractor", _CONTRACTOR_PROPS, ["uuid", "company_uuid"],
     "A new contractor (individual or business) is added to the company.", 0.85),
    ("contractor.updated", "Contractor", _CONTRACTOR_PROPS, ["uuid"],
     "A contractor's information is updated.", 0.80),
    ("payroll.created", "Payroll", _PAYROLL_PROPS, ["uuid", "company_uuid"],
     "A new payroll run is created for a pay period.", 0.85),
    ("payroll.updated", "Payroll", _PAYROLL_PROPS, ["uuid"],
     "A payroll run's data is changed before processing.", 0.80),
    ("payroll.submitted", "Payroll", _PAYROLL_PROPS, ["uuid", "processed"],
     "A payroll run is submitted for processing.", 0.90),
    ("payroll.cancelled", "Payroll", _PAYROLL_PROPS, ["uuid"],
     "A payroll run is cancelled before it is processed.", 0.85),
    ("company.created", "Company", _COMPANY_PROPS, ["uuid"],
     "A new company is provisioned via the Embedded API.", 0.85),
    ("company.updated", "Company", _COMPANY_PROPS, ["uuid"],
     "A company's configuration or details are updated.", 0.80),
    ("company.migration_completed", "Company", _COMPANY_PROPS, ["uuid"],
     "A company migration to the embedded platform is completed.", 0.75),
    ("form_i9.created", "FormI9", {
        "uuid": {"type": "string"},
        "employee_uuid": {"type": "string"},
        "company_uuid": {"type": "string"},
        "status": {"type": "string"},
    }, ["uuid", "employee_uuid"],
     "A Form I-9 employment eligibility verification is created for an employee.", 0.75),
    ("form_i9.updated", "FormI9", {
        "uuid": {"type": "string"},
        "employee_uuid": {"type": "string"},
        "status": {"type": "string"},
    }, ["uuid"],
     "A Form I-9's status or details are updated.", 0.70),
]


class GustoExtractor(ExtractorBase):
    slug = "gusto"
    docs_urls = [
        "https://docs.gusto.com/embedded-payroll/docs/webhooks-overview",
    ]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, entity_type, entity_props, required, trigger_description, confidence in _EVENTS:
            yield {
                "vendor": "gusto",
                "vendor_display_name": "Gusto",
                "category": "hris",
                "event_name": event_name,
                "event_namespace": event_name.split(".")[0],
                "trigger_description": trigger_description,
                "payload_schema": _gusto_schema(event_name, entity_type, entity_props, required),
                "required_oauth_scopes": None,
                "required_subscription_event": None,
                "auth_method": "hmac-sha256",
                "signature_header": "x-gusto-signature",
                "signature_algorithm_detail": (
                    "HMAC-SHA256 of the raw request body using the webhook subscription's shared secret."
                ),
                "retry_policy": {
                    "max_attempts": None,
                    "backoff": "Gusto retries failed webhook deliveries with exponential backoff.",
                    "total_retry_window": None,
                },
                "max_payload_size_bytes": None,
                "idempotency_key_header": "x-gusto-event-uuid",
                "event_id_header": "x-gusto-event-uuid",
                "delivery_guarantees": "at-least-once",
                "delivery": None,
                "docs_url": _DOCS_URL,
                "last_introspected_at": _TIMESTAMP,
                "source_extractor_version": "v0.1.0",
                "extraction_method": "llm-assisted",
                "extraction_confidence": confidence,
                "notes": (
                    "Gusto Embedded Payroll is the embedded platform product. "
                    "Swapped into v1 from Rippling per operator decision 2026-05-13 (sub 1.2 ToS audit)."
                ),
            }


register(GustoExtractor)

"""
pagerduty.py — PagerDuty webhook v3 extractor (tier-2, llm-assisted).

Scope: PagerDuty Webhook Subscriptions (v3). Covers incidents, services, alerts, and on-call.

Source: https://developer.pagerduty.com/docs/db0fa8c8984fc-overview
        https://developer.pagerduty.com/docs/ZG9jOjQ1MTg4ODQ0-overview

extraction_method: llm-assisted
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_DOCS_URL = "https://developer.pagerduty.com/docs/db0fa8c8984fc-overview"

def _pd_schema(event_type: str, resource_type: str, resource_props: dict, required_resource_fields: list[str] | None = None) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "event": {
                "type": "object",
                "description": "The webhook event envelope.",
                "properties": {
                    "id": {"type": "string", "description": "Unique event ID."},
                    "event_type": {"type": "string", "description": f"Event type identifier, e.g. {event_type}."},
                    "resource_type": {"type": "string", "description": f"Resource type, e.g. {resource_type}."},
                    "occurred_at": {"type": "string", "format": "date-time", "description": "When the event occurred (ISO 8601)."},
                    "agent": {
                        "type": ["object", "null"],
                        "description": "The user or service that triggered the event.",
                        "properties": {
                            "html_url": {"type": "string", "description": "Link to the agent in PagerDuty."},
                            "id": {"type": "string", "description": "Agent ID."},
                            "self": {"type": "string", "description": "API URL of the agent."},
                            "summary": {"type": "string", "description": "Name or summary of the agent."},
                            "type": {"type": "string", "description": "Agent object type."},
                        },
                    },
                    "client": {
                        "type": ["object", "null"],
                        "description": "The integration or client that sent the alert (if applicable).",
                        "properties": {
                            "name": {"type": "string", "description": "Client name."},
                        },
                    },
                    "data": {
                        "type": "object",
                        "description": f"The {resource_type} resource object.",
                        "properties": resource_props,
                        "required": required_resource_fields or [],
                    },
                },
                "required": ["id", "event_type", "resource_type", "occurred_at", "data"],
            },
        },
        "required": ["event"],
    }

_INCIDENT_PROPS = {
    "id": {"type": "string", "description": "Incident ID."},
    "title": {"type": "string", "description": "Incident title."},
    "status": {"type": "string", "enum": ["triggered", "acknowledged", "resolved"], "description": "Current incident status."},
    "urgency": {"type": "string", "enum": ["high", "low"], "description": "Incident urgency."},
    "incident_number": {"type": "integer", "description": "Human-readable incident number."},
    "html_url": {"type": "string", "description": "URL to the incident in the PagerDuty web app."},
    "self": {"type": "string", "description": "API URL for this incident."},
    "created_at": {"type": "string", "format": "date-time"},
    "updated_at": {"type": "string", "format": "date-time"},
    "service": {"type": "object", "description": "The service this incident belongs to."},
    "assigned_to": {"type": "array", "description": "Users or escalation policies assigned."},
    "teams": {"type": "array", "description": "Teams associated with this incident."},
    "priority": {"type": ["object", "null"], "description": "Incident priority level."},
    "resolve_reason": {"type": ["object", "null"], "description": "Reason for resolution, if available."},
}

_SERVICE_PROPS = {
    "id": {"type": "string", "description": "Service ID."},
    "name": {"type": "string", "description": "Service name."},
    "status": {"type": "string", "description": "Service status (active, warning, critical, maintenance, disabled)."},
    "html_url": {"type": "string"},
    "self": {"type": "string"},
    "created_at": {"type": "string", "format": "date-time"},
    "updated_at": {"type": "string", "format": "date-time"},
    "escalation_policy": {"type": "object", "description": "Escalation policy associated with the service."},
    "teams": {"type": "array", "description": "Teams that own this service."},
}

_ALERT_PROPS = {
    "id": {"type": "string", "description": "Alert ID."},
    "status": {"type": "string", "enum": ["triggered", "resolved"], "description": "Alert status."},
    "alert_key": {"type": "string", "description": "Deduplication key for grouping alerts."},
    "created_at": {"type": "string", "format": "date-time"},
    "updated_at": {"type": "string", "format": "date-time"},
    "incident": {"type": "object", "description": "The incident this alert was grouped into."},
    "service": {"type": "object", "description": "The service this alert belongs to."},
    "body": {"type": "object", "description": "Alert body including details and custom_details from the sending integration."},
}

_ONCALL_PROPS = {
    "user": {"type": "object", "description": "User going on or off call.", "properties": {
        "id": {"type": "string"},
        "summary": {"type": "string"},
        "type": {"type": "string"},
    }},
    "schedule": {"type": ["object", "null"], "description": "Schedule this on-call shift belongs to."},
    "escalation_policy": {"type": "object", "description": "Escalation policy for this on-call period."},
    "start": {"type": ["string", "null"], "format": "date-time", "description": "Start of the on-call period."},
    "end": {"type": ["string", "null"], "format": "date-time", "description": "End of the on-call period."},
}

# (event_name, resource_type, schema, trigger_description, confidence)
_EVENTS = [
    (
        "incident.triggered",
        "incident",
        _pd_schema("incident.triggered", "incident", _INCIDENT_PROPS, ["id", "title", "status"]),
        "A new incident is triggered on a subscribed PagerDuty service.",
        0.95,
    ),
    (
        "incident.acknowledged",
        "incident",
        _pd_schema("incident.acknowledged", "incident", _INCIDENT_PROPS, ["id", "status"]),
        "An incident transitions to acknowledged state when a responder takes ownership.",
        0.95,
    ),
    (
        "incident.resolved",
        "incident",
        _pd_schema("incident.resolved", "incident", _INCIDENT_PROPS, ["id", "status"]),
        "An incident is resolved and closed.",
        0.95,
    ),
    (
        "incident.unacknowledged",
        "incident",
        _pd_schema("incident.unacknowledged", "incident", _INCIDENT_PROPS, ["id", "status"]),
        "A previously acknowledged incident reverts to triggered state (timeout or manual action).",
        0.90,
    ),
    (
        "incident.delegated",
        "incident",
        _pd_schema("incident.delegated", "incident", _INCIDENT_PROPS, ["id"]),
        "An incident is delegated to a different escalation policy.",
        0.85,
    ),
    (
        "incident.escalated",
        "incident",
        _pd_schema("incident.escalated", "incident", _INCIDENT_PROPS, ["id"]),
        "An incident escalates to the next level of an escalation policy without acknowledgement.",
        0.90,
    ),
    (
        "incident.priority_updated",
        "incident",
        _pd_schema("incident.priority_updated", "incident", _INCIDENT_PROPS, ["id"]),
        "The priority level of an incident is changed.",
        0.85,
    ),
    (
        "incident.action_invocation.created",
        "incident",
        _pd_schema("incident.action_invocation.created", "incident", _INCIDENT_PROPS, ["id"]),
        "A response action (automation action) is invoked on an incident.",
        0.80,
    ),
    (
        "incident.action_invocation.terminated",
        "incident",
        _pd_schema("incident.action_invocation.terminated", "incident", _INCIDENT_PROPS, ["id"]),
        "An invoked automation action on an incident completes or is stopped.",
        0.80,
    ),
    (
        "incident.responder.added",
        "incident",
        _pd_schema("incident.responder.added", "incident", _INCIDENT_PROPS, ["id"]),
        "A responder is added to an incident.",
        0.85,
    ),
    (
        "incident.responder.replied",
        "incident",
        _pd_schema("incident.responder.replied", "incident", _INCIDENT_PROPS, ["id"]),
        "A responder responds to a request to join an incident.",
        0.80,
    ),
    (
        "service.created",
        "service",
        _pd_schema("service.created", "service", _SERVICE_PROPS, ["id", "name"]),
        "A new PagerDuty service is created.",
        0.90,
    ),
    (
        "service.updated",
        "service",
        _pd_schema("service.updated", "service", _SERVICE_PROPS, ["id"]),
        "A PagerDuty service's configuration is changed.",
        0.90,
    ),
    (
        "service.deleted",
        "service",
        _pd_schema("service.deleted", "service", _SERVICE_PROPS, ["id"]),
        "A PagerDuty service is deleted.",
        0.85,
    ),
    (
        "alert.triggered",
        "alert",
        _pd_schema("alert.triggered", "alert", _ALERT_PROPS, ["id", "status"]),
        "A new alert is triggered and grouped into an incident.",
        0.85,
    ),
    (
        "alert.resolved",
        "alert",
        _pd_schema("alert.resolved", "alert", _ALERT_PROPS, ["id", "status"]),
        "An alert is resolved, either manually or by an integration.",
        0.85,
    ),
    (
        "oncall.start",
        "oncall",
        _pd_schema("oncall.start", "oncall", _ONCALL_PROPS, ["user"]),
        "A user begins an on-call shift according to a schedule.",
        0.85,
    ),
    (
        "oncall.end",
        "oncall",
        _pd_schema("oncall.end", "oncall", _ONCALL_PROPS, ["user"]),
        "A user's on-call shift ends.",
        0.85,
    ),
]


class PagerDutyExtractor(ExtractorBase):
    slug = "pagerduty"
    docs_urls = [
        "https://developer.pagerduty.com/docs/db0fa8c8984fc-overview",
    ]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, resource_type, payload_schema, trigger_description, confidence in _EVENTS:
            yield {
                "vendor": "pagerduty",
                "vendor_display_name": "PagerDuty",
                "category": "ops",
                "event_name": event_name,
                "event_namespace": resource_type,
                "trigger_description": trigger_description,
                "payload_schema": payload_schema,
                "required_oauth_scopes": None,
                "required_subscription_event": None,
                "auth_method": "hmac-sha256",
                "signature_header": "X-PagerDuty-Signature",
                "signature_algorithm_detail": (
                    "HMAC-SHA256 of the raw request body using the webhook subscription's signing secret. "
                    "The header contains a v1 prefix: 'v1=<hex-digest>'."
                ),
                "retry_policy": {
                    "max_attempts": None,
                    "backoff": "PagerDuty retries failed webhook deliveries with exponential backoff.",
                    "total_retry_window": None,
                },
                "max_payload_size_bytes": None,
                "idempotency_key_header": "X-Webhook-Id",
                "event_id_header": "X-Webhook-Id",
                "delivery_guarantees": "at-least-once",
                "delivery": None,
                "docs_url": _DOCS_URL,
                "last_introspected_at": _TIMESTAMP,
                "source_extractor_version": "v0.1.0",
                "extraction_method": "llm-assisted",
                "extraction_confidence": confidence,
                "notes": "Webhook v3 (Webhook Subscriptions). v1/v2 extension-based webhooks are a separate legacy surface.",
            }


register(PagerDutyExtractor)

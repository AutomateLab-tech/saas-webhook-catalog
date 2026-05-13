"""
hubspot.py — HubSpot CRM webhooks extractor.

Scope decision (vendors.yaml): CRM object webhooks only.
Excludes CMS webhooks (separate product surface).

HubSpot v3 webhooks use subscriptionType = <objectType>.<triggerType>.
Supported object types from the v3 API reference:
  contact, company, deal, ticket, product, line_item, quote, goal_target,
  conversation, meeting, call, email, note, task, postal_mail, sms,
  whatsapp_message, feedback_submission

Supported trigger types:
  creation, deletion, propertyChange, associationChange, restore, merge

Note: The v4 journal-polling model is separate from the push-webhook model
documented here. This extractor covers the v3 push-webhook subscriptions
as confirmed from the HubSpot developer documentation.

extraction_method: manual-html
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
_DOCS_URL = "https://developers.hubspot.com/docs/guides/api/app-management/webhooks"

# CRM objects that support webhooks in v3.
# Each gets creation, deletion, propertyChange; associationChange only for objects that support associations.
_OBJECT_TYPES = [
    "contact",
    "company",
    "deal",
    "ticket",
    "product",
    "line_item",
    "quote",
    "goal_target",
    "conversation",
    "meeting",
    "call",
    "email",
    "note",
    "task",
    "feedback_submission",
]

# Objects that support associationChange
_ASSOCIATION_OBJECTS = {"contact", "company", "deal", "ticket", "quote"}

# Objects that support restore and merge
_RESTORE_MERGE_OBJECTS = {"contact", "company", "deal", "ticket"}

_TRIGGER_DESCRIPTIONS = {
    "creation": "Fires when a new {obj} record is created in the HubSpot CRM.",
    "deletion": "Fires when a {obj} record is deleted from the HubSpot CRM.",
    "propertyChange": "Fires when one or more properties on a {obj} record are updated.",
    "associationChange": "Fires when an association between a {obj} and another CRM object is added or removed.",
    "restore": "Fires when a previously deleted {obj} record is restored.",
    "merge": "Fires when two {obj} records are merged into one.",
}


class HubSpotExtractor(ExtractorBase):
    slug = "hubspot"
    docs_urls = [_DOCS_URL]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for obj in _OBJECT_TYPES:
            triggers = ["creation", "deletion", "propertyChange"]
            if obj in _ASSOCIATION_OBJECTS:
                triggers.append("associationChange")
            if obj in _RESTORE_MERGE_OBJECTS:
                triggers += ["restore", "merge"]

            for trigger in triggers:
                event_name = f"{obj}.{trigger}"
                desc_template = _TRIGGER_DESCRIPTIONS[trigger]
                trigger_description = desc_template.format(obj=obj.replace("_", " "))

                yield {
                    "vendor": "hubspot",
                    "vendor_display_name": "HubSpot",
                    "category": "crm",
                    "event_name": event_name,
                    "event_namespace": "crm",
                    "trigger_description": trigger_description,
                    "payload_schema": {
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "type": "array",
                        "description": "HubSpot webhook deliveries are batched; each POST body is a JSON array of event objects.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "eventId": {
                                    "type": "integer",
                                    "description": "Unique ID for this webhook event.",
                                },
                                "subscriptionId": {
                                    "type": "integer",
                                    "description": "ID of the subscription that triggered this event.",
                                },
                                "portalId": {
                                    "type": "integer",
                                    "description": "HubSpot portal (account) ID where the event occurred.",
                                },
                                "appId": {
                                    "type": "integer",
                                    "description": "ID of the HubSpot app that owns the subscription.",
                                },
                                "occurredAt": {
                                    "type": "integer",
                                    "description": "Unix timestamp (ms) when the event occurred.",
                                },
                                "subscriptionType": {
                                    "type": "string",
                                    "description": "Subscription type string, e.g. 'contact.creation'.",
                                },
                                "attemptNumber": {
                                    "type": "integer",
                                    "description": "Number of delivery attempts for this event (0-based).",
                                },
                                "objectId": {
                                    "type": "integer",
                                    "description": "ID of the CRM object that triggered the event.",
                                },
                                "changeSource": {
                                    "type": "string",
                                    "description": "Source of the change (e.g. 'CRM_UI', 'API', 'IMPORT').",
                                },
                                "propertyName": {
                                    "type": ["string", "null"],
                                    "description": "For propertyChange events, the name of the changed property.",
                                },
                                "propertyValue": {
                                    "type": ["string", "null"],
                                    "description": "For propertyChange events, the new value of the changed property.",
                                },
                            },
                            "required": ["eventId", "subscriptionId", "portalId", "appId", "occurredAt", "subscriptionType", "objectId"],
                        },
                    },
                    "auth_method": "hmac-sha256",
                    "signature_header": "X-HubSpot-Signature",
                    "signature_algorithm_detail": "SHA-256 hash of app_secret + request_body (v1); or HMAC-SHA256 of timestamp + body (v3 signature). Check X-HubSpot-Signature-Version header.",
                    "required_subscription_event": event_name,
                    "docs_url": _DOCS_URL,
                    "last_introspected_at": _TIMESTAMP,
                    "source_extractor_version": "v1.0",
                    "extraction_method": "manual-html",
                    "delivery_guarantees": "at-least-once",
                    "retry_policy": {
                        "max_attempts": None,
                        "backoff": "Exponential backoff; multiple retry attempts over time.",
                        "total_retry_window": None,
                    },
                    "required_oauth_scopes": None,
                    "notes": "HubSpot v3 push-webhook subscriptions. The v4 journal/polling model is a separate API surface.",
                }


register(HubSpotExtractor)

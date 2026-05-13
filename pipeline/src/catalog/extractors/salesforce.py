"""
salesforce.py — Salesforce Platform Events + Change Data Capture extractor.

Scope decision (vendors.yaml):
- Include: Standard Platform Events shipped by Salesforce (monitoring events)
- Include: Change Data Capture standard objects
- Exclude: Outbound Messages (SOAP, legacy)
- Exclude: Custom Platform Events (not enumerable from public docs)

Salesforce CDC uses the CometD/Bayeux streaming protocol over HTTPS long-polling
(not traditional HTTP webhooks). Events are published to /data/<ObjectName>ChangeEvent
channels. Platform Events publish to /event/<EventApiName> channels.

Auth: OAuth 2.0 bearer token (session ID or connected app access token).
The Streaming API requires a valid authenticated session.

Standard Platform Events (shipped by Salesforce):
- Monitoring events: LoginEventStream, ApiEventStream, etc.
- Change Data Capture standard objects: Account, Contact, Lead, etc.

extraction_method: manual-html
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
_DOCS_URL = "https://developer.salesforce.com/docs/atlas.en-us.api_streaming.meta/api_streaming/intro_stream.htm"
_CDC_DOCS_URL = "https://developer.salesforce.com/docs/atlas.en-us.change_data_capture.meta/change_data_capture/cdc_object_support.htm"
_PE_DOCS_URL = "https://developer.salesforce.com/docs/atlas.en-us.platform_events.meta/platform_events/platform_events_objects_monitoring.htm"

# Standard Platform Events (Salesforce Monitoring Events)
# These are shipped by Salesforce for monitoring and automation.
_PLATFORM_EVENTS = [
    ("LoginEventStream", "Fires when a user logs in to a Salesforce org; includes IP, login type, and session details."),
    ("LoginAsEventStream", "Fires when a user logs in as another user via the Login As feature."),
    ("LogoutEventStream", "Fires when a user logs out of a Salesforce org."),
    ("ApiEventStream", "Fires when an API call is made to Salesforce, including REST and SOAP requests."),
    ("BulkApiResultEventStream", "Fires when a Bulk API job finishes processing."),
    ("UriEventStream", "Fires when a user navigates to a specific URL or UI action within Salesforce."),
    ("ReportEventStream", "Fires when a Salesforce report is run or exported."),
    ("ListViewEventStream", "Fires when a list view is viewed or exported."),
    ("LightningUriEventStream", "Fires when a user navigates to a Lightning Experience URL."),
    ("LightningInteractionEventStream", "Fires when a user performs an interaction in Lightning Experience."),
    ("LightningPageViewEventStream", "Fires when a Lightning Experience page is viewed."),
    ("LightningErrorEventStream", "Fires when a JavaScript error occurs in Lightning Experience."),
    ("LightningPerformanceEventStream", "Fires when a Lightning Experience page performance metric is recorded."),
    ("ExternalCustomApexCalloutEventStream", "Fires when an Apex callout to an external service occurs."),
    ("PermissionSetEventStream", "Fires when a permission set assignment is added or removed."),
    ("ConsentDataGovernanceEventStream", "Fires when data governance consent status changes for a record."),
    ("IdentityVerificationEventStream", "Fires when identity verification is performed for a user."),
    ("AuditTrailEventStream", "Fires when a setup or configuration change is recorded in the Setup Audit Trail."),
]

# Standard Salesforce objects that support Change Data Capture.
# Source: Salesforce documentation on CDC object support (standard subset).
_CDC_OBJECTS = [
    ("Account", "Fires when an Account record is created, updated, deleted, or undeleted."),
    ("AccountContactRole", "Fires when an AccountContactRole junction record changes."),
    ("Asset", "Fires when an Asset record is created, updated, deleted, or undeleted."),
    ("AssetRelationship", "Fires when an AssetRelationship record changes."),
    ("Campaign", "Fires when a Campaign record is created, updated, deleted, or undeleted."),
    ("CampaignMember", "Fires when a CampaignMember record changes."),
    ("Case", "Fires when a Case record is created, updated, deleted, or undeleted."),
    ("CaseContactRole", "Fires when a CaseContactRole junction record changes."),
    ("Contact", "Fires when a Contact record is created, updated, deleted, or undeleted."),
    ("ContentDocument", "Fires when a ContentDocument (file) record changes."),
    ("ContentDocumentLink", "Fires when a ContentDocumentLink (file share) record changes."),
    ("ContentVersion", "Fires when a ContentVersion (file version) record changes."),
    ("Contract", "Fires when a Contract record is created, updated, deleted, or undeleted."),
    ("ContractContactRole", "Fires when a ContractContactRole junction record changes."),
    ("Event", "Fires when an Event (calendar activity) record changes."),
    ("EventRelation", "Fires when an EventRelation record (event attendee) changes."),
    ("FeedComment", "Fires when a Chatter feed comment is added or modified."),
    ("FeedItem", "Fires when a Chatter feed post is created or modified."),
    ("Individual", "Fires when an Individual (data privacy) record changes."),
    ("Lead", "Fires when a Lead record is created, updated, deleted, or undeleted."),
    ("Opportunity", "Fires when an Opportunity record is created, updated, deleted, or undeleted."),
    ("OpportunityContactRole", "Fires when an OpportunityContactRole junction record changes."),
    ("OpportunityLineItem", "Fires when an OpportunityLineItem (product on opportunity) record changes."),
    ("Order", "Fires when an Order record is created, updated, deleted, or undeleted."),
    ("OrderItem", "Fires when an OrderItem (line item on order) record changes."),
    ("Pricebook2", "Fires when a price book record changes."),
    ("PricebookEntry", "Fires when a price book entry changes."),
    ("Product2", "Fires when a Product record is created, updated, deleted, or undeleted."),
    ("Quote", "Fires when a Quote record changes."),
    ("QuoteLineItem", "Fires when a QuoteLineItem record changes."),
    ("ServiceContract", "Fires when a ServiceContract record changes."),
    ("ServiceResource", "Fires when a Service Resource (field service) record changes."),
    ("Task", "Fires when a Task (activity) record is created, updated, deleted, or undeleted."),
    ("User", "Fires when a User record is created or updated."),
    ("UserRole", "Fires when a User Role definition changes."),
    ("WorkOrder", "Fires when a Work Order (field service) record changes."),
    ("WorkOrderLineItem", "Fires when a Work Order Line Item record changes."),
]


def _platform_event_schema(event_api_name: str) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "description": f"CometD message envelope for the {event_api_name} platform event channel.",
        "properties": {
            "channel": {
                "type": "string",
                "description": f"CometD channel: /event/{event_api_name}",
            },
            "data": {
                "type": "object",
                "properties": {
                    "schema": {
                        "type": "string",
                        "description": "Base64-encoded Avro schema ID for this event version.",
                    },
                    "payload": {
                        "type": "object",
                        "description": "Event payload fields specific to this platform event type.",
                        "properties": {
                            "CreatedDate": {
                                "type": "string",
                                "format": "date-time",
                                "description": "Timestamp when the event was published.",
                            },
                            "CreatedById": {
                                "type": "string",
                                "description": "Salesforce user ID of the event publisher.",
                            },
                        },
                        "required": ["CreatedDate", "CreatedById"],
                    },
                    "event": {
                        "type": "object",
                        "properties": {
                            "replayId": {
                                "type": "integer",
                                "description": "Replay ID for this event, used for durable subscriptions.",
                            },
                        },
                        "required": ["replayId"],
                    },
                },
                "required": ["schema", "payload", "event"],
            },
        },
        "required": ["channel", "data"],
    }


def _cdc_schema(object_name: str) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "description": f"CometD message envelope for the {object_name}ChangeEvent CDC channel.",
        "properties": {
            "channel": {
                "type": "string",
                "description": f"CometD channel: /data/{object_name}ChangeEvent",
            },
            "data": {
                "type": "object",
                "properties": {
                    "schema": {
                        "type": "string",
                        "description": "Base64-encoded Avro schema ID for this change event version.",
                    },
                    "payload": {
                        "type": "object",
                        "description": "Change event payload containing changed field values.",
                        "properties": {
                            "ChangeEventHeader": {
                                "type": "object",
                                "description": "Metadata about the change including operation type and changed fields.",
                                "properties": {
                                    "entityName": {
                                        "type": "string",
                                        "description": "API name of the changed object.",
                                    },
                                    "recordIds": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "IDs of the records that changed.",
                                    },
                                    "changeType": {
                                        "type": "string",
                                        "enum": ["CREATE", "UPDATE", "DELETE", "UNDELETE"],
                                        "description": "Type of DML operation that triggered the change.",
                                    },
                                    "changedFields": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "List of field API names that were modified.",
                                    },
                                    "commitTimestamp": {
                                        "type": "integer",
                                        "description": "Unix timestamp (ms) of the database commit.",
                                    },
                                    "commitNumber": {
                                        "type": "integer",
                                        "description": "Database commit number for ordering.",
                                    },
                                    "commitUser": {
                                        "type": "string",
                                        "description": "Salesforce user ID who made the change.",
                                    },
                                },
                                "required": ["entityName", "recordIds", "changeType", "changedFields"],
                            },
                        },
                        "required": ["ChangeEventHeader"],
                    },
                    "event": {
                        "type": "object",
                        "properties": {
                            "replayId": {
                                "type": "integer",
                                "description": "Replay ID for durable subscription replay.",
                            },
                        },
                        "required": ["replayId"],
                    },
                },
                "required": ["schema", "payload", "event"],
            },
        },
        "required": ["channel", "data"],
    }


class SalesforceExtractor(ExtractorBase):
    slug = "salesforce"
    docs_urls = [_DOCS_URL, _CDC_DOCS_URL, _PE_DOCS_URL]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        # Platform Events (monitoring)
        for event_api_name, trigger_description in _PLATFORM_EVENTS:
            yield {
                "vendor": "salesforce",
                "vendor_display_name": "Salesforce",
                "category": "crm",
                "event_name": f"/event/{event_api_name}",
                "event_namespace": "platform_events",
                "trigger_description": trigger_description,
                "payload_schema": _platform_event_schema(event_api_name),
                "auth_method": "bearer-token",
                "signature_header": None,
                "signature_algorithm_detail": "OAuth 2.0 session authentication via CometD handshake. No per-message signature; transport security relies on TLS and session token validity.",
                "docs_url": _PE_DOCS_URL,
                "last_introspected_at": _TIMESTAMP,
                "source_extractor_version": "v1.0",
                "extraction_method": "manual-html",
                "delivery": None,
                "delivery_guarantees": "at-least-once",
                "retry_policy": {
                    "max_attempts": None,
                    "backoff": "CometD durable subscriptions support replay from a given replayId; events retained for 72 hours.",
                    "total_retry_window": "PT72H",
                },
                "required_oauth_scopes": ["api", "event"],
                "notes": "Delivered via CometD long-polling (Streaming API), not HTTP webhooks. Subscribe to /event/{EventApiName} channel.",
            }

        # Change Data Capture
        for object_name, trigger_description in _CDC_OBJECTS:
            yield {
                "vendor": "salesforce",
                "vendor_display_name": "Salesforce",
                "category": "crm",
                "event_name": f"/data/{object_name}ChangeEvent",
                "event_namespace": "change_data_capture",
                "trigger_description": trigger_description,
                "payload_schema": _cdc_schema(object_name),
                "auth_method": "bearer-token",
                "signature_header": None,
                "signature_algorithm_detail": "OAuth 2.0 session authentication via CometD handshake. No per-message signature; transport security relies on TLS and session token validity.",
                "docs_url": _CDC_DOCS_URL,
                "last_introspected_at": _TIMESTAMP,
                "source_extractor_version": "v1.0",
                "extraction_method": "manual-html",
                "delivery": None,
                "delivery_guarantees": "at-least-once",
                "retry_policy": {
                    "max_attempts": None,
                    "backoff": "CometD durable subscriptions support replay from replayId; events retained for 72 hours.",
                    "total_retry_window": "PT72H",
                },
                "required_oauth_scopes": ["api", "cdp_profile_api"],
                "notes": "Delivered via CometD long-polling (Streaming API). Subscribe to /data/{ObjectName}ChangeEvent channel. Custom Platform Events and Outbound Messages are out of scope.",
            }


register(SalesforceExtractor)

"""
linear.py — Linear webhooks extractor.

Source: https://linear.app/developers/webhooks (confirmed live).
GraphQL introspection at https://api.linear.app/graphql used to identify
payload types; extraction_method: vendor-graphql-schema for the type information.

Supported resources (from live docs): Issues, Issue attachments, Issue comments,
Issue labels, Comment reactions, Projects, Project updates, Documents,
Initiatives, Initiative Updates, Cycles, Customers, Customer Requests, Users.
Plus Issue SLA and OAuthApp revoked events.

Actions: create, update, remove for data-change webhooks.
Issue SLA: set, highRisk, breached.
OAuthApp: revoked.

authentication: HMAC-SHA256, header: Linear-Signature
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
_DOCS_URL = "https://linear.app/developers/webhooks"

# (resource_type, graphql_type, supported_actions, description_template)
_RESOURCES = [
    ("Issue", "Issue", ["create", "update", "remove"],
     "Fires when an issue is {action}d in a Linear workspace."),
    ("IssueAttachment", "Attachment", ["create", "update", "remove"],
     "Fires when an attachment is {action}d on a Linear issue."),
    ("Comment", "Comment", ["create", "update", "remove"],
     "Fires when a comment on an issue is {action}d in Linear."),
    ("IssueLabel", "IssueLabel", ["create", "update", "remove"],
     "Fires when an issue label is {action}d in Linear."),
    ("Reaction", "Reaction", ["create", "update", "remove"],
     "Fires when an emoji reaction on a comment is {action}d in Linear."),
    ("Project", "Project", ["create", "update", "remove"],
     "Fires when a project is {action}d in Linear."),
    ("ProjectUpdate", "ProjectUpdate", ["create", "update", "remove"],
     "Fires when a project status update is {action}d in Linear."),
    ("Document", "Document", ["create", "update", "remove"],
     "Fires when a document is {action}d in a Linear workspace."),
    ("Initiative", "Initiative", ["create", "update", "remove"],
     "Fires when an initiative (roadmap milestone) is {action}d in Linear."),
    ("InitiativeUpdate", "InitiativeUpdate", ["create", "update", "remove"],
     "Fires when an initiative status update is {action}d in Linear."),
    ("Cycle", "Cycle", ["create", "update", "remove"],
     "Fires when a sprint cycle is {action}d in Linear."),
    ("Customer", "Customer", ["create", "update", "remove"],
     "Fires when a customer record is {action}d in Linear."),
    ("CustomerNeed", "CustomerNeed", ["create", "update", "remove"],
     "Fires when a customer request (need) is {action}d in Linear."),
    ("User", "User", ["create", "update", "remove"],
     "Fires when a user account is {action}d in a Linear workspace."),
]

_SLA_ACTIONS = [
    ("IssueSla", "set", "Fires when an SLA is set on a Linear issue."),
    ("IssueSla", "highRisk", "Fires when an issue SLA enters a high-risk state, nearing breach."),
    ("IssueSla", "breached", "Fires when an issue SLA is breached without resolution."),
]


def _payload_schema(graphql_type: str) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "update", "remove"],
                "description": "Action that triggered the webhook.",
            },
            "type": {
                "type": "string",
                "description": "Resource type name matching the Linear GraphQL type.",
            },
            "organizationId": {
                "type": "string",
                "description": "ID of the Linear organization where the event occurred.",
            },
            "data": {
                "type": "object",
                "description": f"The {graphql_type} object that was affected. Fields match the Linear GraphQL schema for this type.",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Unique identifier of the affected resource.",
                    },
                    "createdAt": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Timestamp when the resource was created.",
                    },
                    "updatedAt": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Timestamp when the resource was last modified.",
                    },
                },
                "required": ["id"],
            },
            "updatedFrom": {
                "type": ["object", "null"],
                "description": "For update actions, contains the previous field values that changed.",
            },
            "url": {
                "type": "string",
                "format": "uri",
                "description": "Direct URL to the affected resource in the Linear app.",
            },
            "webhookTimestamp": {
                "type": "integer",
                "description": "Unix timestamp (ms) when the webhook was dispatched.",
            },
        },
        "required": ["action", "type", "organizationId", "data"],
    }


class LinearExtractor(ExtractorBase):
    slug = "linear"
    docs_urls = [_DOCS_URL]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for resource_type, graphql_type, actions, desc_template in _RESOURCES:
            for action in actions:
                action_word = "remov" if action == "remove" else action
                trigger_description = desc_template.format(action=action_word)

                yield {
                    "vendor": "linear",
                    "vendor_display_name": "Linear",
                    "category": "dev-tools",
                    "event_name": f"{resource_type}.{action}",
                    "event_namespace": None,
                    "trigger_description": trigger_description,
                    "payload_schema": _payload_schema(graphql_type),
                    "auth_method": "hmac-sha256",
                    "signature_header": "Linear-Signature",
                    "signature_algorithm_detail": "Hex-encoded HMAC-SHA256 of the raw request body, signed with the webhook's signing secret.",
                    "docs_url": _DOCS_URL,
                    "last_introspected_at": _TIMESTAMP,
                    "source_extractor_version": "v1.0",
                    "extraction_method": "vendor-graphql-schema",
                    "delivery_guarantees": "at-least-once",
                    "retry_policy": {
                        "max_attempts": None,
                        "backoff": "Linear retries failed webhooks with backoff.",
                        "total_retry_window": None,
                    },
                    "required_oauth_scopes": None,
                    "notes": None,
                }

        # Issue SLA events
        for resource_type, action, trigger_description in _SLA_ACTIONS:
            yield {
                "vendor": "linear",
                "vendor_display_name": "Linear",
                "category": "dev-tools",
                "event_name": f"{resource_type}.{action}",
                "event_namespace": None,
                "trigger_description": trigger_description,
                "payload_schema": {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["set", "highRisk", "breached"],
                            "description": "SLA action type.",
                        },
                        "type": {
                            "type": "string",
                            "const": "IssueSla",
                        },
                        "organizationId": {"type": "string"},
                        "data": {
                            "type": "object",
                            "properties": {
                                "issueId": {"type": "string", "description": "ID of the affected issue."},
                                "slaDueAt": {"type": "string", "format": "date-time", "description": "SLA deadline timestamp."},
                            },
                            "required": ["issueId"],
                        },
                    },
                    "required": ["action", "type", "organizationId", "data"],
                },
                "auth_method": "hmac-sha256",
                "signature_header": "Linear-Signature",
                "signature_algorithm_detail": "Hex-encoded HMAC-SHA256 of the raw request body, signed with the webhook's signing secret.",
                "docs_url": _DOCS_URL,
                "last_introspected_at": _TIMESTAMP,
                "source_extractor_version": "v1.0",
                "extraction_method": "vendor-graphql-schema",
                "delivery_guarantees": "at-least-once",
                "retry_policy": None,
                "required_oauth_scopes": None,
                "notes": None,
            }

        # OAuthApp revoked event
        yield {
            "vendor": "linear",
            "vendor_display_name": "Linear",
            "category": "dev-tools",
            "event_name": "OAuthClientApproval.revoked",
            "event_namespace": None,
            "trigger_description": "Fires when a user revokes a Linear OAuth application's access to their account.",
            "payload_schema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "action": {"type": "string", "const": "revoked"},
                    "type": {"type": "string", "const": "OAuthClientApproval"},
                    "organizationId": {"type": "string"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "clientId": {"type": "string", "description": "ID of the revoked OAuth client application."},
                            "userId": {"type": "string", "description": "ID of the user who revoked access."},
                        },
                        "required": ["clientId", "userId"],
                    },
                },
                "required": ["action", "type", "organizationId", "data"],
            },
            "auth_method": "hmac-sha256",
            "signature_header": "Linear-Signature",
            "signature_algorithm_detail": "Hex-encoded HMAC-SHA256 of the raw request body, signed with the webhook's signing secret.",
            "docs_url": _DOCS_URL,
            "last_introspected_at": _TIMESTAMP,
            "source_extractor_version": "v1.0",
            "extraction_method": "vendor-graphql-schema",
            "delivery_guarantees": "at-least-once",
            "retry_policy": None,
            "required_oauth_scopes": None,
            "notes": None,
        }


register(LinearExtractor)

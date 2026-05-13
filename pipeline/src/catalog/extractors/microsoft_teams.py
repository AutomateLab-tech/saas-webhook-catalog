"""
microsoft_teams.py — Microsoft Teams Graph change notifications extractor (tier-2, llm-assisted).

Scope: Microsoft Graph API change notifications for Teams resources (chats, messages, channels).
Excludes outgoing/incoming webhook templates (those are user-defined, not platform events).

Source: https://learn.microsoft.com/en-us/graph/webhooks
        https://learn.microsoft.com/en-us/graph/api/resources/webhooks

compliance: Respectful fetch cadence required on learn.microsoft.com (throttle.yaml: 0.5 rps).
docs_url must link to https://learn.microsoft.com/en-us/graph/webhooks

extraction_method: llm-assisted
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_BASE_DOCS_URL = "https://learn.microsoft.com/en-us/graph/webhooks"

# Common Graph change notification envelope schema
def _notification_schema(resource_data_description: str, resource_data_properties: dict) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "description": "Microsoft Graph change notification delivery envelope.",
        "properties": {
            "value": {
                "type": "array",
                "description": "Array of change notification objects in this delivery.",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Unique notification ID."},
                        "subscriptionId": {"type": "string", "description": "ID of the subscription that triggered this notification."},
                        "subscriptionExpirationDateTime": {"type": "string", "format": "date-time", "description": "Expiry time of the subscription."},
                        "changeType": {
                            "type": "string",
                            "enum": ["created", "updated", "deleted"],
                            "description": "The type of change that triggered the notification.",
                        },
                        "resource": {"type": "string", "description": "The resource path of the changed object."},
                        "tenantId": {"type": "string", "description": "The tenant (organization) ID."},
                        "clientState": {"type": ["string", "null"], "description": "Opaque client state value set at subscription time."},
                        "resourceData": {
                            "type": ["object", "null"],
                            "description": resource_data_description,
                            "properties": resource_data_properties,
                        },
                        "encryptedContent": {
                            "type": ["object", "null"],
                            "description": "Encrypted payload when subscription uses encryption.",
                            "properties": {
                                "data": {"type": "string", "description": "Encrypted data (base64)."},
                                "dataSignature": {"type": "string", "description": "Signature for verification."},
                                "dataKey": {"type": "string", "description": "Encrypted symmetric key."},
                                "encryptionCertificateId": {"type": "string"},
                                "encryptionCertificateThumbprint": {"type": "string"},
                            },
                        },
                    },
                    "required": ["id", "subscriptionId", "changeType", "resource"],
                },
            },
        },
        "required": ["value"],
    }


_CHAT_MESSAGE_PROPS = {
    "id": {"type": "string", "description": "Message ID."},
    "@odata.type": {"type": "string", "description": "OData type, e.g. #microsoft.graph.chatMessage."},
    "@odata.id": {"type": "string", "description": "OData resource URI."},
    "@odata.etag": {"type": "string", "description": "ETag for concurrency."},
}

_CHANNEL_PROPS = {
    "id": {"type": "string", "description": "Channel ID."},
    "@odata.type": {"type": "string", "description": "OData type, e.g. #microsoft.graph.channel."},
    "displayName": {"type": "string", "description": "Display name of the channel."},
}

_CHAT_PROPS = {
    "id": {"type": "string", "description": "Chat ID."},
    "@odata.type": {"type": "string", "description": "OData type, e.g. #microsoft.graph.chat."},
}

_MEMBER_PROPS = {
    "id": {"type": "string", "description": "Membership ID."},
    "@odata.type": {"type": "string", "description": "OData type, e.g. #microsoft.graph.conversationMember."},
}

_PRESENCE_PROPS = {
    "id": {"type": "string", "description": "User ID."},
    "@odata.type": {"type": "string", "description": "OData type, e.g. #microsoft.graph.presence."},
}

# (event_name, resource_path_pattern, change_types, trigger_description, confidence)
_EVENTS = [
    (
        "teams.channel.message.created",
        "/teams/{teamId}/channels/{channelId}/messages",
        _notification_schema("The chat message resource that was created.", _CHAT_MESSAGE_PROPS),
        "A new message is posted to a Teams channel that the subscription covers.",
        0.90,
    ),
    (
        "teams.channel.message.updated",
        "/teams/{teamId}/channels/{channelId}/messages",
        _notification_schema("The updated chat message resource.", _CHAT_MESSAGE_PROPS),
        "An existing message in a Teams channel is edited or has a reaction/reply added.",
        0.85,
    ),
    (
        "teams.channel.message.deleted",
        "/teams/{teamId}/channels/{channelId}/messages",
        _notification_schema("The deleted chat message resource reference.", _CHAT_MESSAGE_PROPS),
        "A message in a Teams channel is deleted (soft or hard delete).",
        0.85,
    ),
    (
        "teams.chat.message.created",
        "/chats/{chatId}/messages",
        _notification_schema("The chat message resource that was created.", _CHAT_MESSAGE_PROPS),
        "A new message is posted in a one-on-one or group chat.",
        0.90,
    ),
    (
        "teams.chat.message.updated",
        "/chats/{chatId}/messages",
        _notification_schema("The updated chat message resource.", _CHAT_MESSAGE_PROPS),
        "An existing message in a chat is edited or reacted to.",
        0.85,
    ),
    (
        "teams.channel.created",
        "/teams/{teamId}/channels",
        _notification_schema("The channel resource that was created.", _CHANNEL_PROPS),
        "A new channel is created within a subscribed Teams team.",
        0.90,
    ),
    (
        "teams.channel.updated",
        "/teams/{teamId}/channels",
        _notification_schema("The updated channel resource.", _CHANNEL_PROPS),
        "A Teams channel's properties (name, description) are modified.",
        0.85,
    ),
    (
        "teams.channel.deleted",
        "/teams/{teamId}/channels",
        _notification_schema("The deleted channel resource reference.", _CHANNEL_PROPS),
        "A channel is removed from a Teams team.",
        0.85,
    ),
    (
        "teams.chat.created",
        "/chats",
        _notification_schema("The chat resource that was created.", _CHAT_PROPS),
        "A new chat (one-on-one or group) is initiated.",
        0.85,
    ),
    (
        "teams.chat.updated",
        "/chats",
        _notification_schema("The updated chat resource.", _CHAT_PROPS),
        "A chat's properties or membership changes.",
        0.80,
    ),
    (
        "teams.channel.member.created",
        "/teams/{teamId}/channels/{channelId}/members",
        _notification_schema("The channel membership resource.", _MEMBER_PROPS),
        "A user is added as a member of a Teams channel.",
        0.85,
    ),
    (
        "teams.channel.member.deleted",
        "/teams/{teamId}/channels/{channelId}/members",
        _notification_schema("The channel membership resource that was removed.", _MEMBER_PROPS),
        "A user is removed from a Teams channel's membership.",
        0.85,
    ),
    (
        "teams.chat.member.created",
        "/chats/{chatId}/members",
        _notification_schema("The chat membership resource.", _MEMBER_PROPS),
        "A user is added to a group chat or one-on-one chat.",
        0.85,
    ),
    (
        "teams.chat.member.deleted",
        "/chats/{chatId}/members",
        _notification_schema("The chat membership resource that was removed.", _MEMBER_PROPS),
        "A user is removed from a chat.",
        0.80,
    ),
    (
        "teams.user.presence.updated",
        "/communications/presences/{userId}",
        _notification_schema("The presence resource for the user.", _PRESENCE_PROPS),
        "A subscribed user's availability or activity status changes in Teams.",
        0.80,
    ),
]


class MicrosoftTeamsExtractor(ExtractorBase):
    slug = "microsoft-teams"
    docs_urls = [
        "https://learn.microsoft.com/en-us/graph/webhooks",
        "https://learn.microsoft.com/en-us/graph/api/resources/webhooks",
    ]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, resource_path, payload_schema, trigger_description, confidence in _EVENTS:
            yield {
                "vendor": "microsoft-teams",
                "vendor_display_name": "Microsoft Teams",
                "category": "collaboration",
                "event_name": event_name,
                "event_namespace": "graph-change-notifications",
                "trigger_description": trigger_description,
                "payload_schema": payload_schema,
                "required_oauth_scopes": None,
                "required_subscription_event": None,
                "auth_method": "bearer-token",
                "signature_header": None,
                "signature_algorithm_detail": (
                    "Graph subscriptions use a clientState token returned in each notification "
                    "for validation. Encrypted payloads require a subscriber-provided certificate. "
                    "The subscriber verifies notifications by checking clientState against the value set at subscription time."
                ),
                "retry_policy": {
                    "max_attempts": None,
                    "backoff": "Microsoft Graph retries failed notifications with exponential backoff for up to 4 hours.",
                    "total_retry_window": "PT4H",
                },
                "max_payload_size_bytes": None,
                "idempotency_key_header": None,
                "event_id_header": None,
                "delivery_guarantees": "at-least-once",
                "delivery": None,
                "docs_url": _BASE_DOCS_URL,
                "last_introspected_at": _TIMESTAMP,
                "source_extractor_version": "v0.1.0",
                "extraction_method": "llm-assisted",
                "extraction_confidence": confidence,
                "notes": (
                    "Graph change notifications scope; excludes Teams incoming/outgoing webhook templates. "
                    "Subscriptions require Azure AD app registration and relevant Microsoft Graph permissions."
                ),
            }


register(MicrosoftTeamsExtractor)

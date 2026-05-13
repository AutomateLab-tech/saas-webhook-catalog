"""
zendesk.py — Zendesk webhooks extractor.

Scope: Zendesk Support event types (ticket, user, organization, article events).
Source: https://developer.zendesk.com/api-reference/event-connectors/webhooks/webhook-event-types/

ToS audit: cleared-with-restrictions. Throttle <= 1 req/sec (already set in throttle.yaml).
docs_url must link to https://developer.zendesk.com/api-reference/webhooks/event-types/event-type-list/

Zendesk event type identifiers use the pattern zen:event-type/<domain>.<EventName>.
The supported domains and event types enumerated from the Zendesk docs.

Auth: HMAC-SHA256 or HMAC-SHA512 (configurable per webhook); header: X-Zendesk-Webhook-Signature.
Also provides X-Zendesk-Webhook-Signature-Timestamp and X-Zendesk-Webhook-Id.

extraction_method: manual-html
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
_DOCS_URL = "https://developer.zendesk.com/api-reference/webhooks/event-types/event-type-list/"

# Zendesk event types organized by domain.
# Sourced from Zendesk documentation covering all 9 event domains.
# Format: (event_type_id, trigger_description)
_EVENTS = [
    # Ticket events (zen:event-type/ticket domain)
    ("zen:event-type/ticket.TicketCreated", "Fires when a new support ticket is created in Zendesk."),
    ("zen:event-type/ticket.TicketUpdated", "Fires when a ticket's properties, status, or assignee change."),
    ("zen:event-type/ticket.TicketSolved", "Fires when a ticket transitions to solved status."),
    ("zen:event-type/ticket.TicketClosed", "Fires when a solved ticket transitions to closed status."),
    ("zen:event-type/ticket.TicketReopened", "Fires when a closed or solved ticket is reopened."),
    ("zen:event-type/ticket.TicketPending", "Fires when a ticket is set to pending status."),
    ("zen:event-type/ticket.TicketHold", "Fires when a ticket is placed on hold."),
    ("zen:event-type/ticket.TicketAssigned", "Fires when a ticket is assigned to an agent or group."),
    ("zen:event-type/ticket.TicketCommentCreated", "Fires when a public reply or internal note is added to a ticket."),
    ("zen:event-type/ticket.TicketTagsUpdated", "Fires when tags are added to or removed from a ticket."),
    ("zen:event-type/ticket.TicketPriorityUpdated", "Fires when a ticket's priority level is changed."),
    ("zen:event-type/ticket.TicketSubjectUpdated", "Fires when a ticket's subject line is modified."),
    ("zen:event-type/ticket.TicketTypeUpdated", "Fires when a ticket type changes (question, incident, problem, task)."),
    ("zen:event-type/ticket.TicketCustomFieldsUpdated", "Fires when one or more custom field values on a ticket change."),
    ("zen:event-type/ticket.TicketFollowerAdded", "Fires when a follower (CC) is added to a ticket."),
    ("zen:event-type/ticket.TicketFollowerRemoved", "Fires when a follower is removed from a ticket."),
    ("zen:event-type/ticket.TicketDueDateUpdated", "Fires when a ticket's due date is set or changed."),
    ("zen:event-type/ticket.TicketSatisfactionRatingOffered", "Fires when a customer satisfaction survey is sent for a ticket."),
    ("zen:event-type/ticket.TicketSatisfactionRatingReceived", "Fires when a customer responds to a satisfaction survey."),
    ("zen:event-type/ticket.TicketMerged", "Fires when a ticket is merged into another ticket."),
    # User events (zen:event-type/user domain)
    ("zen:event-type/user.UserCreated", "Fires when a new end-user or agent account is created."),
    ("zen:event-type/user.UserUpdated", "Fires when a user's profile properties change."),
    ("zen:event-type/user.UserDeleted", "Fires when a user account is soft-deleted from Zendesk."),
    ("zen:event-type/user.UserMerged", "Fires when two user records are merged into one."),
    ("zen:event-type/user.UserPasswordChanged", "Fires when a user's password is changed."),
    ("zen:event-type/user.UserRoleUpdated", "Fires when a user's role or permissions change."),
    ("zen:event-type/user.UserTagsUpdated", "Fires when tags on a user record are added or removed."),
    ("zen:event-type/user.UserCustomFieldsUpdated", "Fires when custom field values on a user record change."),
    ("zen:event-type/user.UserSuspended", "Fires when a user account is suspended."),
    ("zen:event-type/user.UserUnsuspended", "Fires when a suspended user account is reactivated."),
    # Organization events (zen:event-type/organization domain)
    ("zen:event-type/organization.OrganizationCreated", "Fires when a new organization is created in Zendesk."),
    ("zen:event-type/organization.OrganizationUpdated", "Fires when an organization's properties change."),
    ("zen:event-type/organization.OrganizationDeleted", "Fires when an organization is deleted from Zendesk."),
    ("zen:event-type/organization.OrganizationTagsUpdated", "Fires when tags on an organization are added or removed."),
    ("zen:event-type/organization.OrganizationCustomFieldsUpdated", "Fires when custom field values on an organization change."),
    ("zen:event-type/organization.OrganizationMemberAdded", "Fires when a user is added to an organization."),
    ("zen:event-type/organization.OrganizationMemberRemoved", "Fires when a user is removed from an organization."),
    # Article events (zen:event-type/article domain - Guide)
    ("zen:event-type/article.ArticleCreated", "Fires when a new knowledge base article is created in Zendesk Guide."),
    ("zen:event-type/article.ArticleUpdated", "Fires when an existing knowledge base article is modified."),
    ("zen:event-type/article.ArticleDeleted", "Fires when a knowledge base article is deleted."),
    ("zen:event-type/article.ArticlePublished", "Fires when a knowledge base article is published."),
    ("zen:event-type/article.ArticleUnpublished", "Fires when a published knowledge base article is taken offline."),
    # Community post events (zen:event-type/community_post domain)
    ("zen:event-type/community_post.PostCreated", "Fires when a new community forum post is created."),
    ("zen:event-type/community_post.PostUpdated", "Fires when a community post is edited."),
    ("zen:event-type/community_post.PostDeleted", "Fires when a community post is deleted."),
    ("zen:event-type/community_post.PostPublished", "Fires when a community post is published."),
    ("zen:event-type/community_post.PostSpam", "Fires when a community post is marked as spam."),
    # Agent availability events
    ("zen:event-type/agent.AgentAvailabilityUpdated", "Fires when an agent's availability status or capacity changes."),
    ("zen:event-type/agent.AgentStatusUpdated", "Fires when an agent's presence status changes (online, away, offline)."),
    # Omnichannel routing configuration events
    ("zen:event-type/omnichannel_config.RoutingConfigUpdated", "Fires when omnichannel routing settings or queue configuration change."),
    ("zen:event-type/omnichannel_config.SkillsConfigUpdated", "Fires when routing skill definitions or assignments change."),
    # Messaging events (zen:event-type/messaging_ticket domain)
    ("zen:event-type/messaging_ticket.ConversationCreated", "Fires when a new messaging (chat) conversation is initiated."),
    ("zen:event-type/messaging_ticket.ConversationUpdated", "Fires when a messaging conversation's properties change."),
    ("zen:event-type/messaging_ticket.MessageReceived", "Fires when a new message is received in a messaging conversation."),
    ("zen:event-type/messaging_ticket.ConversationAssigned", "Fires when a messaging conversation is assigned to an agent."),
    ("zen:event-type/messaging_ticket.ConversationCompleted", "Fires when a messaging conversation ends."),
    # Live messaging metrics
    ("zen:event-type/messaging_live_metrics.MetricsUpdated", "Fires when real-time messaging metrics (queue size, wait times) update."),
]


def _payload_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "id": {
                "type": "string",
                "description": "Unique identifier for this webhook event delivery.",
            },
            "type": {
                "type": "string",
                "description": "Event type identifier (e.g. 'zen:event-type/ticket.TicketCreated').",
            },
            "account_id": {
                "type": "integer",
                "description": "Zendesk account ID where the event occurred.",
            },
            "time": {
                "type": "string",
                "format": "date-time",
                "description": "ISO 8601 timestamp when the event was generated.",
            },
            "subject": {
                "type": "object",
                "description": "The primary object (ticket, user, etc.) that triggered the event. Shape depends on domain.",
                "properties": {
                    "id": {"type": "integer", "description": "ID of the affected object."},
                    "type": {"type": "string", "description": "Type of the affected object."},
                },
                "required": ["id"],
            },
            "detail": {
                "type": "object",
                "description": "Event-specific detail payload. Fields vary by event type.",
            },
        },
        "required": ["id", "type", "account_id", "time"],
    }


class ZendeskExtractor(ExtractorBase):
    slug = "zendesk"
    docs_urls = [_DOCS_URL]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        schema = _payload_schema()
        for event_type, trigger_description in _EVENTS:
            yield {
                "vendor": "zendesk",
                "vendor_display_name": "Zendesk",
                "category": "support",
                "event_name": event_type,
                "event_namespace": None,
                "trigger_description": trigger_description,
                "payload_schema": schema,
                "auth_method": "hmac-sha256",
                "signature_header": "X-Zendesk-Webhook-Signature",
                "signature_algorithm_detail": "HMAC-SHA256 or HMAC-SHA512 (configurable per webhook). Timestamp in X-Zendesk-Webhook-Signature-Timestamp header used for replay prevention.",
                "docs_url": _DOCS_URL,
                "last_introspected_at": _TIMESTAMP,
                "source_extractor_version": "v1.0",
                "extraction_method": "manual-html",
                "delivery_guarantees": "at-least-once",
                "retry_policy": {
                    "max_attempts": None,
                    "backoff": "Zendesk retries failed webhook deliveries.",
                    "total_retry_window": None,
                },
                "idempotency_key_header": "X-Zendesk-Webhook-Id",
                "event_id_header": "X-Zendesk-Webhook-Id",
                "required_oauth_scopes": None,
                "notes": "ToS audit 2026-05-13: extractor throttled to 1 req/sec per compliance obligation.",
            }


register(ZendeskExtractor)

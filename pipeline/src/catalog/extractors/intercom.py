"""
intercom.py — Intercom webhooks extractor.

Source: https://developers.intercom.com/docs/references/webhooks/webhook-models/
Single page enumerates all topics. Confirmed 118 topics from live page fetch.

Auth: HMAC-SHA1, header X-Hub-Signature (format: sha1=<hex>).
Timeout: 5 seconds.

extraction_method: manual-html
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
_DOCS_URL = "https://developers.intercom.com/docs/references/webhooks/webhook-models/"

# All 118 topics confirmed from live fetch of the Intercom webhook models page.
# Format: (topic, paraphrased_description)
_TOPICS = [
    # Admin
    ("admin.added_to_workspace", "Fires when an admin user is added to an Intercom workspace."),
    ("admin.away_mode_updated", "Fires when an admin's away mode status changes."),
    ("admin.activity_log_event.created", "Fires when a new admin activity log entry is recorded."),
    ("admin.removed_from_workspace", "Fires when an admin is removed from an Intercom workspace."),
    ("admin.logged_in", "Fires when an admin logs in to Intercom."),
    ("admin.logged_out", "Fires when an admin logs out of Intercom."),
    # Article
    ("article.created", "Fires when a new Help Center article is created."),
    ("article.updated", "Fires when an existing Help Center article is modified."),
    ("article.published", "Fires when a Help Center article is published and becomes publicly visible."),
    ("article.unpublished", "Fires when a published Help Center article is taken offline."),
    ("article.deleted", "Fires when a Help Center article is permanently deleted."),
    # Call
    ("call.started", "Fires when a new call is initiated through Intercom."),
    ("call.ended", "Fires when an active call ends."),
    ("call.transcription_available", "Fires when a call transcription has been processed and is ready."),
    ("call.recording_available", "Fires when a call recording has been processed and is ready."),
    # Company
    ("company.created", "Fires when a new company record is created in Intercom."),
    ("company.deleted", "Fires when a company record is deleted from Intercom."),
    ("company.updated", "Fires when a company record's properties change."),
    ("company.contact.attached", "Fires when a contact is associated with a company."),
    ("company.contact.detached", "Fires when a contact is disassociated from a company."),
    # Contact
    ("contact.archived", "Fires when a contact is archived and removed from active lists."),
    ("contact.deleted", "Fires when a contact record is permanently deleted."),
    ("contact.email.updated", "Fires when a contact's email address changes."),
    ("contact.lead.added_email", "Fires when an email address is added to a lead contact."),
    ("contact.lead.created", "Fires when a new lead contact is created in Intercom."),
    ("contact.lead.signed_up", "Fires when a lead converts by signing up."),
    ("contact.lead.tag.created", "Fires when a tag is applied to a lead contact."),
    ("contact.lead.tag.deleted", "Fires when a tag is removed from a lead contact."),
    ("contact.lead.updated", "Fires when a lead contact's properties are updated."),
    ("contact.merged", "Fires when two contact records are merged into one."),
    ("contact.subscribed", "Fires when a contact opts into messaging subscriptions."),
    ("contact.unarchive", "Fires when an archived contact is restored to active status."),
    ("contact.unsubscribed", "Fires when a contact opts out of messaging subscriptions."),
    ("contact.user.created", "Fires when a new user contact is created in Intercom."),
    ("contact.user.tag.created", "Fires when a tag is applied to a user contact."),
    ("contact.user.tag.deleted", "Fires when a tag is removed from a user contact."),
    ("contact.user.updated", "Fires when a user contact's properties are updated."),
    # Conversation
    ("conversation.admin.assigned", "Fires when a conversation is assigned to a specific admin."),
    ("conversation.admin.closed", "Fires when an admin closes a conversation."),
    ("conversation.admin.noted", "Fires when an admin adds an internal note to a conversation."),
    ("conversation.admin.open.assigned", "Fires when an open conversation is assigned to an admin."),
    ("conversation.admin.opened", "Fires when an admin reopens a closed conversation."),
    ("conversation.admin.replied", "Fires when an admin sends a reply in a conversation."),
    ("conversation.admin.single.created", "Fires when an admin initiates a new outbound conversation."),
    ("conversation.admin.snoozed", "Fires when an admin snoozes a conversation."),
    ("conversation.admin.unsnoozed", "Fires when a snoozed conversation's reminder activates."),
    ("conversation.operator.replied", "Fires when a bot or operator sends an automated reply in a conversation."),
    ("conversation.deleted", "Fires when a conversation is deleted."),
    ("conversation_part.redacted", "Fires when a specific message part in a conversation is redacted."),
    ("conversation_part.tag.created", "Fires when a tag is added to a conversation part (message)."),
    ("conversation.priority.updated", "Fires when a conversation's priority level changes."),
    ("conversation.rating.added", "Fires when a customer submits a satisfaction rating on a conversation."),
    ("conversation.read", "Fires when a conversation is marked as read."),
    ("conversation.user.created", "Fires when a user initiates a new inbound conversation."),
    ("conversation.user.replied", "Fires when a user sends a reply in an existing conversation."),
    ("conversation.contact.attached", "Fires when a contact is linked to a conversation."),
    ("conversation.contact.detached", "Fires when a contact is unlinked from a conversation."),
    ("conversation.company.updated", "Fires when the company associated with a conversation changes."),
    # Content stat
    ("content_stat.banner", "Fires when engagement metrics for a banner are updated."),
    ("content_stat.carousel", "Fires when engagement metrics for a carousel are updated."),
    ("content_stat.chat", "Fires when engagement metrics for a chat message are updated."),
    ("content_stat.checklist", "Fires when engagement metrics for a checklist are updated."),
    ("content_stat.custom_bot", "Fires when engagement metrics for a custom bot are updated."),
    ("content_stat.email", "Fires when engagement metrics for an email campaign are updated."),
    ("content_stat.news_item", "Fires when engagement metrics for a news item are updated."),
    ("content_stat.post", "Fires when engagement metrics for a post are updated."),
    ("content_stat.push", "Fires when engagement metrics for a push notification are updated."),
    ("content_stat.series", "Fires when engagement metrics for a series campaign are updated."),
    ("content_stat.series.webhook", "Fires when engagement metrics for a series webhook step are updated."),
    ("content_stat.sms", "Fires when engagement metrics for an SMS campaign are updated."),
    ("content_stat.survey", "Fires when engagement metrics for a survey are updated."),
    ("content_stat.tooltip_group", "Fires when engagement metrics for a tooltip group are updated."),
    ("content_stat.tour", "Fires when engagement metrics for a product tour are updated."),
    # Event
    ("event.created", "Fires when a new custom event is tracked for a contact."),
    # API Activity
    ("api.request.completed", "Fires when an API request made by the workspace completes."),
    # Jobs
    ("job.completed", "Fires when a background import or export job finishes."),
    # Ping
    ("ping", "Fires as a test ping to verify the webhook endpoint is reachable."),
    # Subscription
    ("granular.unsubscribe", "Fires when a contact unsubscribes from a specific communication type."),
    ("granular.subscribe", "Fires when a contact subscribes to a specific communication type."),
    # Ticket
    ("ticket.created", "Fires when a new support ticket is created."),
    ("ticket.state.updated", "Fires when a ticket's state changes (e.g. in_progress to waiting_on_customer)."),
    ("ticket.note.created", "Fires when an internal note is added to a ticket."),
    ("ticket.admin.assigned", "Fires when a ticket is assigned to an admin."),
    ("ticket.team.assigned", "Fires when a ticket is assigned to a team."),
    ("ticket.contact.attached", "Fires when a contact is linked to a ticket."),
    ("ticket.contact.detached", "Fires when a contact is unlinked from a ticket."),
    ("ticket.attribute.updated", "Fires when a custom attribute on a ticket changes."),
    ("ticket.admin.replied", "Fires when an admin sends a reply on a ticket."),
    ("ticket.contact.replied", "Fires when a contact replies on their ticket."),
    ("ticket.closed", "Fires when a ticket is marked as closed."),
    ("ticket.rating.provided", "Fires when a contact submits a satisfaction rating for a ticket."),
    ("ticket.resolved", "Fires when a ticket is marked as resolved."),
    # Visitor
    ("visitor.signed_up", "Fires when a website visitor converts and signs up."),
    # Data Connector
    ("data_connector.execution.completed", "Fires when a data connector sync execution finishes."),
]


def _payload_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "const": "notification_event",
                "description": "Object type identifier; always 'notification_event' for Intercom webhooks.",
            },
            "app_id": {
                "type": "string",
                "description": "ID of the Intercom workspace where the event occurred.",
            },
            "data": {
                "type": "object",
                "description": "Wrapper containing the event item.",
                "properties": {
                    "type": {"type": "string", "description": "Data type discriminator."},
                    "item": {
                        "type": "object",
                        "description": "The affected Intercom object. Shape varies by topic.",
                    },
                },
                "required": ["type", "item"],
            },
            "links": {
                "type": "object",
                "description": "Hypermedia links related to the event.",
            },
            "id": {
                "type": "string",
                "description": "Unique ID for this notification event."},
            "topic": {
                "type": "string",
                "description": "Webhook topic identifier matching this row's event_name.",
            },
            "delivery_status": {
                "type": "string",
                "description": "Delivery status of this notification.",
            },
            "delivery_attempts": {
                "type": "integer",
                "description": "Number of delivery attempts made for this notification.",
            },
            "delivered_at": {
                "type": "integer",
                "description": "Unix timestamp when delivery was confirmed.",
            },
            "first_sent_at": {
                "type": "integer",
                "description": "Unix timestamp of the first delivery attempt.",
            },
            "created_at": {
                "type": "integer",
                "description": "Unix timestamp when this notification was created.",
            },
            "self": {
                "type": "string",
                "format": "uri",
                "description": "URL for this notification event resource.",
            },
        },
        "required": ["type", "app_id", "data", "topic"],
    }


class IntercomExtractor(ExtractorBase):
    slug = "intercom"
    docs_urls = [_DOCS_URL]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        schema = _payload_schema()
        for topic, trigger_description in _TOPICS:
            yield {
                "vendor": "intercom",
                "vendor_display_name": "Intercom",
                "category": "support",
                "event_name": topic,
                "event_namespace": None,
                "trigger_description": trigger_description,
                "payload_schema": schema,
                "auth_method": "hmac-sha1",
                "signature_header": "X-Hub-Signature",
                "signature_algorithm_detail": "40-byte hex HMAC-SHA1; header format is 'sha1=<hex>'. Endpoint must respond within 5 seconds.",
                "docs_url": _DOCS_URL,
                "last_introspected_at": _TIMESTAMP,
                "source_extractor_version": "v1.0",
                "extraction_method": "manual-html",
                "delivery_guarantees": "at-least-once",
                "retry_policy": None,
                "required_oauth_scopes": None,
                "notes": None,
            }


register(IntercomExtractor)

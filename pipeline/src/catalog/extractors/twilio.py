"""
twilio.py — Twilio webhook extractor (tier-2, llm-assisted).

Scope decision: Conversations events + Messaging (SMS/MMS) status callbacks.
Deferred: Voice TwiML callbacks, Studio events.

Source: https://www.twilio.com/docs/usage/webhooks
        https://www.twilio.com/docs/conversations/webhooks
        https://www.twilio.com/docs/sms/webhooks

extraction_method: llm-assisted
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_MESSAGING_DOCS_URL = "https://www.twilio.com/docs/usage/webhooks/messaging-webhooks"
_CONVERSATIONS_DOCS_URL = "https://www.twilio.com/docs/conversations/webhooks"

_MESSAGING_STATUS_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "description": "Twilio Messaging status callback payload (form-encoded POST).",
    "properties": {
        "MessageSid": {"type": "string", "description": "Unique message SID (e.g. SM...)."},
        "SmsSid": {"type": "string", "description": "Legacy alias for MessageSid."},
        "AccountSid": {"type": "string", "description": "Twilio account SID."},
        "From": {"type": "string", "description": "Sender phone number in E.164 format."},
        "To": {"type": "string", "description": "Recipient phone number in E.164 format."},
        "Body": {"type": ["string", "null"], "description": "Message body text (included on inbound only)."},
        "MessageStatus": {
            "type": "string",
            "enum": ["accepted", "scheduled", "queued", "sending", "sent", "failed", "delivered", "undelivered", "receiving", "received", "read"],
            "description": "Current delivery status of the message.",
        },
        "SmsStatus": {"type": "string", "description": "Legacy alias for MessageStatus."},
        "ErrorCode": {"type": ["string", "null"], "description": "Error code if delivery failed."},
        "ErrorMessage": {"type": ["string", "null"], "description": "Human-readable error description."},
        "NumMedia": {"type": "string", "description": "Number of media items attached (as string)."},
        "NumSegments": {"type": "string", "description": "Number of SMS segments used."},
        "MessagingServiceSid": {"type": ["string", "null"], "description": "SID of the messaging service used."},
    },
    "required": ["MessageSid", "AccountSid", "MessageStatus"],
}

_INBOUND_MESSAGE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "description": "Twilio inbound SMS/MMS webhook payload (form-encoded POST).",
    "properties": {
        "MessageSid": {"type": "string", "description": "Unique message SID."},
        "AccountSid": {"type": "string", "description": "Account SID."},
        "From": {"type": "string", "description": "Sender number in E.164 format."},
        "To": {"type": "string", "description": "Recipient number (your Twilio number)."},
        "Body": {"type": "string", "description": "Message body text."},
        "NumMedia": {"type": "string", "description": "Number of media items attached."},
        "MediaContentType0": {"type": ["string", "null"], "description": "MIME type of the first media item."},
        "MediaUrl0": {"type": ["string", "null"], "description": "URL of the first media item."},
        "FromCity": {"type": ["string", "null"]},
        "FromState": {"type": ["string", "null"]},
        "FromZip": {"type": ["string", "null"]},
        "FromCountry": {"type": ["string", "null"]},
        "ToCity": {"type": ["string", "null"]},
        "ToState": {"type": ["string", "null"]},
        "ToCountry": {"type": ["string", "null"]},
    },
    "required": ["MessageSid", "AccountSid", "From", "To", "Body"],
}

def _conv_schema(event_type: str, data_props: dict) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "description": f"Twilio Conversations webhook payload for {event_type}.",
        "properties": {
            "EventType": {"type": "string", "description": f"Event type identifier: {event_type}."},
            "AccountSid": {"type": "string", "description": "Twilio account SID."},
            **data_props,
        },
        "required": ["EventType", "AccountSid"],
    }

_CONVERSATION_PROPS = {
    "ConversationSid": {"type": "string", "description": "SID of the conversation."},
    "ConversationFriendlyName": {"type": ["string", "null"], "description": "Human-readable name of the conversation."},
    "ConversationAttributes": {"type": ["string", "null"], "description": "JSON string of custom attributes set on the conversation."},
    "ConversationDateCreated": {"type": "string", "description": "ISO 8601 creation timestamp."},
    "ConversationDateUpdated": {"type": "string", "description": "ISO 8601 last-updated timestamp."},
    "State": {"type": ["string", "null"], "enum": ["active", "inactive", "closed", None], "description": "Conversation state."},
}

_PARTICIPANT_PROPS = {
    "ConversationSid": {"type": "string", "description": "SID of the conversation."},
    "ParticipantSid": {"type": "string", "description": "SID of the participant."},
    "Identity": {"type": ["string", "null"], "description": "Chat identity of the participant."},
    "RoleSid": {"type": ["string", "null"], "description": "Role assigned to this participant."},
    "MessagingBinding": {"type": ["object", "null"], "description": "Binding details for SMS/WhatsApp participants."},
}

_CONV_MESSAGE_PROPS = {
    "ConversationSid": {"type": "string", "description": "SID of the conversation."},
    "MessageSid": {"type": "string", "description": "SID of the message."},
    "Index": {"type": "string", "description": "Position of the message in the conversation."},
    "Author": {"type": "string", "description": "Identity or address of the message author."},
    "Body": {"type": ["string", "null"], "description": "Message body text."},
    "Media": {"type": ["string", "null"], "description": "JSON array of media objects attached."},
    "Attributes": {"type": ["string", "null"], "description": "Custom attributes JSON string."},
    "DateCreated": {"type": "string", "description": "ISO 8601 timestamp."},
}

# (event_name, namespace, schema, docs_url, trigger_description, confidence)
_EVENTS = [
    # Messaging status callbacks
    ("message.queued", "messaging", _MESSAGING_STATUS_SCHEMA, _MESSAGING_DOCS_URL,
     "An outbound SMS/MMS is accepted and placed in the send queue.", 0.90),
    ("message.sent", "messaging", _MESSAGING_STATUS_SCHEMA, _MESSAGING_DOCS_URL,
     "An outbound SMS/MMS is successfully handed off to the carrier.", 0.95),
    ("message.delivered", "messaging", _MESSAGING_STATUS_SCHEMA, _MESSAGING_DOCS_URL,
     "An outbound SMS/MMS is confirmed delivered to the recipient's handset.", 0.95),
    ("message.failed", "messaging", _MESSAGING_STATUS_SCHEMA, _MESSAGING_DOCS_URL,
     "An outbound SMS/MMS delivery fails; ErrorCode indicates the reason.", 0.95),
    ("message.undelivered", "messaging", _MESSAGING_STATUS_SCHEMA, _MESSAGING_DOCS_URL,
     "An outbound SMS/MMS is not delivered after carrier attempts.", 0.90),
    ("message.received", "messaging", _INBOUND_MESSAGE_SCHEMA, _MESSAGING_DOCS_URL,
     "An inbound SMS or MMS is received on a Twilio phone number.", 0.95),
    # Conversations events
    ("onConversationAdded", "conversations", _conv_schema("onConversationAdded", _CONVERSATION_PROPS), _CONVERSATIONS_DOCS_URL,
     "A new conversation is created in a Twilio Conversations service.", 0.90),
    ("onConversationUpdated", "conversations", _conv_schema("onConversationUpdated", _CONVERSATION_PROPS), _CONVERSATIONS_DOCS_URL,
     "A conversation's properties or state are updated.", 0.85),
    ("onConversationRemoved", "conversations", _conv_schema("onConversationRemoved", _CONVERSATION_PROPS), _CONVERSATIONS_DOCS_URL,
     "A conversation is deleted from the service.", 0.85),
    ("onConversationStateUpdated", "conversations", _conv_schema("onConversationStateUpdated", {
        **_CONVERSATION_PROPS,
        "StateTo": {"type": "string", "description": "The new state the conversation transitioned to."},
        "StateFrom": {"type": "string", "description": "The previous state."},
    }), _CONVERSATIONS_DOCS_URL,
     "A conversation transitions between active, inactive, and closed states.", 0.85),
    ("onParticipantAdded", "conversations", _conv_schema("onParticipantAdded", _PARTICIPANT_PROPS), _CONVERSATIONS_DOCS_URL,
     "A participant is added to a conversation.", 0.90),
    ("onParticipantUpdated", "conversations", _conv_schema("onParticipantUpdated", _PARTICIPANT_PROPS), _CONVERSATIONS_DOCS_URL,
     "A participant's properties or role in a conversation are updated.", 0.85),
    ("onParticipantRemoved", "conversations", _conv_schema("onParticipantRemoved", _PARTICIPANT_PROPS), _CONVERSATIONS_DOCS_URL,
     "A participant is removed from a conversation.", 0.85),
    ("onMessageAdded", "conversations", _conv_schema("onMessageAdded", _CONV_MESSAGE_PROPS), _CONVERSATIONS_DOCS_URL,
     "A new message is sent in a conversation.", 0.90),
    ("onMessageUpdated", "conversations", _conv_schema("onMessageUpdated", _CONV_MESSAGE_PROPS), _CONVERSATIONS_DOCS_URL,
     "An existing message in a conversation is edited.", 0.85),
    ("onMessageRemoved", "conversations", _conv_schema("onMessageRemoved", _CONV_MESSAGE_PROPS), _CONVERSATIONS_DOCS_URL,
     "A message is deleted from a conversation.", 0.85),
]


class TwilioExtractor(ExtractorBase):
    slug = "twilio"
    docs_urls = [
        "https://www.twilio.com/docs/usage/webhooks",
        "https://www.twilio.com/docs/conversations/webhooks",
        "https://www.twilio.com/docs/sms/webhooks",
    ]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, namespace, payload_schema, docs_url, trigger_description, confidence in _EVENTS:
            yield {
                "vendor": "twilio",
                "vendor_display_name": "Twilio",
                "category": "communications",
                "event_name": event_name,
                "event_namespace": namespace,
                "trigger_description": trigger_description,
                "payload_schema": payload_schema,
                "required_oauth_scopes": None,
                "required_subscription_event": None,
                "auth_method": "hmac-sha1",
                "signature_header": "X-Twilio-Signature",
                "signature_algorithm_detail": (
                    "HMAC-SHA1 computed over the full callback URL concatenated with "
                    "sorted POST parameters (or raw body for JSON). "
                    "Uses the Auth Token as the HMAC key."
                ),
                "retry_policy": {
                    "max_attempts": None,
                    "backoff": "Twilio retries failed webhook deliveries with exponential backoff for up to 24 hours.",
                    "total_retry_window": "PT24H",
                },
                "max_payload_size_bytes": None,
                "idempotency_key_header": None,
                "event_id_header": None,
                "delivery_guarantees": "at-least-once",
                "delivery": None,
                "docs_url": docs_url,
                "last_introspected_at": _TIMESTAMP,
                "source_extractor_version": "v0.1.0",
                "extraction_method": "llm-assisted",
                "extraction_confidence": confidence,
                "notes": (
                    "Scope: Conversations events + Messaging status callbacks. "
                    "Voice TwiML callbacks and Studio events deferred to v2."
                ),
            }


register(TwilioExtractor)

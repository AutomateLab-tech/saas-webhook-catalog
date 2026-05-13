"""
discord.py — Discord Gateway events + interaction webhooks extractor (tier-2, llm-assisted).

Scope: Gateway events (delivery: websocket) + interaction webhooks (delivery: webhook).
Per ToS audit: trigger_descriptions must be paraphrased (no verbatim copy from Discord docs).
Per compliance: delivery field must be set per row.

Source: https://discord.com/developers/docs/topics/gateway-events
        https://discord.com/developers/docs/interactions/receiving-and-responding

extraction_method: llm-assisted
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_GATEWAY_DOCS_URL = "https://discord.com/developers/docs/topics/gateway-events"
_INTERACTION_DOCS_URL = "https://discord.com/developers/docs/interactions/receiving-and-responding"

# Common gateway dispatch envelope
_GATEWAY_ENVELOPE = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "description": "Discord Gateway dispatch payload envelope.",
    "properties": {
        "op": {"type": "integer", "description": "Gateway opcode; 0 for Dispatch events."},
        "d": {"type": ["object", "null"], "description": "Event data payload; structure varies per event type."},
        "s": {"type": ["integer", "null"], "description": "Sequence number for resuming sessions."},
        "t": {"type": ["string", "null"], "description": "Event type name (e.g. MESSAGE_CREATE)."},
    },
    "required": ["op"],
}

def _gateway_schema(event_properties: dict, required_fields: list[str] | None = None) -> dict:
    """Build a typed gateway schema with event-specific data properties."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "description": "Discord Gateway dispatch payload.",
        "properties": {
            "op": {"type": "integer", "description": "Opcode 0 for Dispatch."},
            "t": {"type": "string", "description": "Event name."},
            "s": {"type": ["integer", "null"], "description": "Sequence number."},
            "d": {
                "type": "object",
                "description": "Event data.",
                "properties": event_properties,
                "required": required_fields or [],
            },
        },
        "required": ["op", "t", "d"],
    }

_USER_OBJ = {
    "id": {"type": "string", "description": "User snowflake ID."},
    "username": {"type": "string", "description": "User's display name."},
    "discriminator": {"type": "string", "description": "4-digit discriminator (legacy; 0 for new usernames)."},
    "global_name": {"type": ["string", "null"], "description": "User's global display name."},
    "bot": {"type": ["boolean", "null"], "description": "Whether the user is a bot."},
}

_GUILD_MEMBER_OBJ = {
    "user": {"type": ["object", "null"], "description": "The underlying user object."},
    "nick": {"type": ["string", "null"], "description": "Member's nickname in the guild."},
    "roles": {"type": "array", "items": {"type": "string"}, "description": "Array of role IDs the member has."},
    "joined_at": {"type": "string", "format": "date-time", "description": "When the member joined the guild."},
    "premium_since": {"type": ["string", "null"], "format": "date-time", "description": "When the member started boosting."},
    "deaf": {"type": "boolean", "description": "Whether the member is deafened in voice."},
    "mute": {"type": "boolean", "description": "Whether the member is muted in voice."},
}

_MESSAGE_PROPS = {
    "id": {"type": "string", "description": "Message snowflake ID."},
    "channel_id": {"type": "string", "description": "ID of the channel this message was sent in."},
    "guild_id": {"type": ["string", "null"], "description": "ID of the guild, if applicable."},
    "author": {"type": "object", "description": "The author user object.", "properties": _USER_OBJ},
    "content": {"type": "string", "description": "Message content text."},
    "timestamp": {"type": "string", "format": "date-time", "description": "When the message was sent."},
    "edited_timestamp": {"type": ["string", "null"], "format": "date-time"},
    "tts": {"type": "boolean", "description": "Whether the message was sent with text-to-speech."},
    "mention_everyone": {"type": "boolean", "description": "Whether the message mentions @everyone."},
    "mentions": {"type": "array", "description": "Users mentioned in the message."},
    "mention_roles": {"type": "array", "items": {"type": "string"}, "description": "Role IDs mentioned."},
    "attachments": {"type": "array", "description": "Attached files."},
    "embeds": {"type": "array", "description": "Embedded content objects."},
    "type": {"type": "integer", "description": "Message type integer."},
}

_CHANNEL_PROPS = {
    "id": {"type": "string", "description": "Channel snowflake ID."},
    "type": {"type": "integer", "description": "Channel type integer."},
    "guild_id": {"type": ["string", "null"], "description": "Guild ID for guild channels."},
    "name": {"type": ["string", "null"], "description": "Channel name."},
    "topic": {"type": ["string", "null"], "description": "Channel topic text."},
    "nsfw": {"type": ["boolean", "null"], "description": "Whether the channel is NSFW."},
    "position": {"type": ["integer", "null"], "description": "Sort position of the channel."},
    "parent_id": {"type": ["string", "null"], "description": "Parent category ID."},
}

# (event_name, delivery, payload_schema, trigger_description, confidence)
_EVENTS: list[tuple] = [
    # ---- Gateway events (delivery: websocket) ----
    (
        "GUILD_CREATE",
        "websocket",
        _gateway_schema({
            "id": {"type": "string", "description": "Guild snowflake ID."},
            "name": {"type": "string", "description": "Guild name."},
            "icon": {"type": ["string", "null"], "description": "Icon hash."},
            "owner_id": {"type": "string", "description": "ID of the guild owner."},
            "member_count": {"type": "integer", "description": "Total number of guild members."},
            "channels": {"type": "array", "description": "Channels belonging to this guild."},
            "members": {"type": "array", "description": "Members visible to the bot."},
            "roles": {"type": "array", "description": "Roles in the guild."},
        }, ["id", "name"]),
        "Dispatched when a guild becomes available or the bot joins a new guild. Includes full guild state.",
        0.90,
    ),
    (
        "GUILD_UPDATE",
        "websocket",
        _gateway_schema({
            "id": {"type": "string", "description": "Guild snowflake ID."},
            "name": {"type": "string", "description": "Updated guild name."},
            "icon": {"type": ["string", "null"], "description": "Updated icon hash."},
            "owner_id": {"type": "string", "description": "Current owner ID."},
        }, ["id"]),
        "Dispatched when a guild's properties are changed, such as name, icon, or owner.",
        0.90,
    ),
    (
        "GUILD_DELETE",
        "websocket",
        _gateway_schema({
            "id": {"type": "string", "description": "Guild snowflake ID."},
            "unavailable": {"type": ["boolean", "null"], "description": "True if the guild is unavailable rather than deleted."},
        }, ["id"]),
        "Dispatched when the bot is removed from a guild or the guild becomes unavailable due to an outage.",
        0.90,
    ),
    (
        "GUILD_MEMBER_ADD",
        "websocket",
        _gateway_schema({**_GUILD_MEMBER_OBJ, "guild_id": {"type": "string", "description": "ID of the guild the member joined."}}, ["guild_id"]),
        "Dispatched when a new user joins a guild.",
        0.90,
    ),
    (
        "GUILD_MEMBER_UPDATE",
        "websocket",
        _gateway_schema({
            "guild_id": {"type": "string", "description": "Guild ID."},
            "roles": {"type": "array", "items": {"type": "string"}, "description": "Updated list of role IDs."},
            "user": {"type": "object", "description": "The updated user object.", "properties": _USER_OBJ},
            "nick": {"type": ["string", "null"], "description": "New nickname."},
        }, ["guild_id", "user"]),
        "Dispatched when a guild member's roles, nickname, or other properties are updated.",
        0.90,
    ),
    (
        "GUILD_MEMBER_REMOVE",
        "websocket",
        _gateway_schema({
            "guild_id": {"type": "string", "description": "Guild ID."},
            "user": {"type": "object", "description": "The user who was removed.", "properties": _USER_OBJ},
        }, ["guild_id", "user"]),
        "Dispatched when a member leaves a guild, is kicked, or is banned.",
        0.90,
    ),
    (
        "GUILD_BAN_ADD",
        "websocket",
        _gateway_schema({
            "guild_id": {"type": "string", "description": "Guild ID."},
            "user": {"type": "object", "description": "The banned user.", "properties": _USER_OBJ},
        }, ["guild_id", "user"]),
        "Dispatched when a user is banned from a guild.",
        0.90,
    ),
    (
        "GUILD_BAN_REMOVE",
        "websocket",
        _gateway_schema({
            "guild_id": {"type": "string", "description": "Guild ID."},
            "user": {"type": "object", "description": "The unbanned user.", "properties": _USER_OBJ},
        }, ["guild_id", "user"]),
        "Dispatched when a user's ban is lifted from a guild.",
        0.90,
    ),
    (
        "GUILD_ROLE_CREATE",
        "websocket",
        _gateway_schema({
            "guild_id": {"type": "string", "description": "Guild ID."},
            "role": {
                "type": "object",
                "description": "The newly created role.",
                "properties": {
                    "id": {"type": "string", "description": "Role ID."},
                    "name": {"type": "string", "description": "Role name."},
                    "color": {"type": "integer", "description": "Role color as integer."},
                    "hoist": {"type": "boolean", "description": "Whether the role is hoisted separately."},
                    "permissions": {"type": "string", "description": "Permissions bitfield string."},
                },
            },
        }, ["guild_id", "role"]),
        "Dispatched when a new role is created in a guild.",
        0.90,
    ),
    (
        "GUILD_ROLE_UPDATE",
        "websocket",
        _gateway_schema({
            "guild_id": {"type": "string", "description": "Guild ID."},
            "role": {"type": "object", "description": "The updated role object."},
        }, ["guild_id", "role"]),
        "Dispatched when a role's properties are modified.",
        0.85,
    ),
    (
        "GUILD_ROLE_DELETE",
        "websocket",
        _gateway_schema({
            "guild_id": {"type": "string", "description": "Guild ID."},
            "role_id": {"type": "string", "description": "ID of the deleted role."},
        }, ["guild_id", "role_id"]),
        "Dispatched when a role is deleted from a guild.",
        0.90,
    ),
    (
        "CHANNEL_CREATE",
        "websocket",
        _gateway_schema(_CHANNEL_PROPS, ["id", "type"]),
        "Dispatched when a new channel is created, including DMs opened with the bot.",
        0.90,
    ),
    (
        "CHANNEL_UPDATE",
        "websocket",
        _gateway_schema(_CHANNEL_PROPS, ["id"]),
        "Dispatched when a channel's properties are updated.",
        0.90,
    ),
    (
        "CHANNEL_DELETE",
        "websocket",
        _gateway_schema(_CHANNEL_PROPS, ["id"]),
        "Dispatched when a channel is deleted.",
        0.90,
    ),
    (
        "MESSAGE_CREATE",
        "websocket",
        _gateway_schema(_MESSAGE_PROPS, ["id", "channel_id", "author", "content"]),
        "Dispatched when a message is posted to a channel the bot can see.",
        0.90,
    ),
    (
        "MESSAGE_UPDATE",
        "websocket",
        _gateway_schema({**_MESSAGE_PROPS, "edited_timestamp": {"type": "string", "format": "date-time"}}, ["id", "channel_id"]),
        "Dispatched when a message is edited; may include only changed fields.",
        0.85,
    ),
    (
        "MESSAGE_DELETE",
        "websocket",
        _gateway_schema({
            "id": {"type": "string", "description": "Deleted message ID."},
            "channel_id": {"type": "string", "description": "Channel ID."},
            "guild_id": {"type": ["string", "null"], "description": "Guild ID if applicable."},
        }, ["id", "channel_id"]),
        "Dispatched when a single message is deleted.",
        0.90,
    ),
    (
        "MESSAGE_DELETE_BULK",
        "websocket",
        _gateway_schema({
            "ids": {"type": "array", "items": {"type": "string"}, "description": "Array of deleted message IDs."},
            "channel_id": {"type": "string", "description": "Channel ID."},
            "guild_id": {"type": ["string", "null"], "description": "Guild ID if applicable."},
        }, ["ids", "channel_id"]),
        "Dispatched when multiple messages are bulk-deleted from a channel.",
        0.90,
    ),
    (
        "MESSAGE_REACTION_ADD",
        "websocket",
        _gateway_schema({
            "user_id": {"type": "string", "description": "ID of the user who reacted."},
            "channel_id": {"type": "string", "description": "Channel ID."},
            "message_id": {"type": "string", "description": "Message ID."},
            "guild_id": {"type": ["string", "null"], "description": "Guild ID if applicable."},
            "emoji": {"type": "object", "description": "Partial emoji object.", "properties": {
                "id": {"type": ["string", "null"], "description": "Emoji ID for custom emojis."},
                "name": {"type": ["string", "null"], "description": "Emoji name."},
            }},
        }, ["user_id", "channel_id", "message_id", "emoji"]),
        "Dispatched when a user adds a reaction to a message.",
        0.90,
    ),
    (
        "MESSAGE_REACTION_REMOVE",
        "websocket",
        _gateway_schema({
            "user_id": {"type": "string", "description": "ID of the user who removed their reaction."},
            "channel_id": {"type": "string", "description": "Channel ID."},
            "message_id": {"type": "string", "description": "Message ID."},
            "emoji": {"type": "object", "description": "Partial emoji object."},
        }, ["user_id", "channel_id", "message_id", "emoji"]),
        "Dispatched when a user removes a reaction from a message.",
        0.90,
    ),
    (
        "PRESENCE_UPDATE",
        "websocket",
        _gateway_schema({
            "user": {"type": "object", "description": "Partial user object.", "properties": {"id": {"type": "string"}}},
            "guild_id": {"type": "string", "description": "Guild ID."},
            "status": {"type": "string", "enum": ["online", "idle", "dnd", "offline"], "description": "Current status."},
            "activities": {"type": "array", "description": "Array of activity objects."},
            "client_status": {"type": "object", "description": "Per-platform (desktop/mobile/web) status."},
        }, ["user", "guild_id"]),
        "Dispatched when a user's online status or activities change in a guild.",
        0.85,
    ),
    (
        "VOICE_STATE_UPDATE",
        "websocket",
        _gateway_schema({
            "guild_id": {"type": ["string", "null"], "description": "Guild ID."},
            "channel_id": {"type": ["string", "null"], "description": "Channel ID; null when leaving voice."},
            "user_id": {"type": "string", "description": "User ID."},
            "session_id": {"type": "string", "description": "Session ID for this voice connection."},
            "deaf": {"type": "boolean", "description": "Whether the user is server-deafened."},
            "mute": {"type": "boolean", "description": "Whether the user is server-muted."},
            "self_deaf": {"type": "boolean", "description": "Whether the user has deafened themselves."},
            "self_mute": {"type": "boolean", "description": "Whether the user has muted themselves."},
            "suppress": {"type": "boolean", "description": "Whether the user is suppressed in a stage channel."},
        }, ["user_id", "session_id"]),
        "Dispatched when a user joins, leaves, or changes state in a voice channel.",
        0.90,
    ),
    # ---- Interaction webhooks (delivery: webhook) ----
    (
        "INTERACTION_APPLICATION_COMMAND",
        "webhook",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "description": "Interaction payload for a slash command or context menu invocation.",
            "properties": {
                "id": {"type": "string", "description": "Interaction snowflake ID."},
                "application_id": {"type": "string", "description": "The application's ID."},
                "type": {"type": "integer", "description": "Interaction type (2 = APPLICATION_COMMAND)."},
                "data": {
                    "type": "object",
                    "description": "Command-specific data.",
                    "properties": {
                        "id": {"type": "string", "description": "Command ID."},
                        "name": {"type": "string", "description": "Command name."},
                        "type": {"type": "integer", "description": "Command type."},
                        "options": {"type": ["array", "null"], "description": "Array of resolved option values."},
                    },
                    "required": ["id", "name"],
                },
                "guild_id": {"type": ["string", "null"], "description": "Guild ID if invoked in a guild."},
                "channel_id": {"type": ["string", "null"], "description": "Channel ID."},
                "member": {"type": ["object", "null"], "description": "Guild member who invoked the command."},
                "user": {"type": ["object", "null"], "description": "User who invoked the command (in DM contexts)."},
                "token": {"type": "string", "description": "Continuation token valid for 15 minutes."},
                "version": {"type": "integer", "description": "Interaction version; currently 1."},
            },
            "required": ["id", "application_id", "type", "data", "token"],
        },
        "Sent to the application's registered interactions endpoint when a user invokes a slash command or context menu item.",
        0.90,
    ),
    (
        "INTERACTION_MESSAGE_COMPONENT",
        "webhook",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "description": "Interaction payload for a button click or select menu selection.",
            "properties": {
                "id": {"type": "string", "description": "Interaction ID."},
                "application_id": {"type": "string", "description": "Application ID."},
                "type": {"type": "integer", "description": "Interaction type (3 = MESSAGE_COMPONENT)."},
                "data": {
                    "type": "object",
                    "description": "Component interaction data.",
                    "properties": {
                        "custom_id": {"type": "string", "description": "Custom ID set by the developer on the component."},
                        "component_type": {"type": "integer", "description": "Component type (2=button, 3=select, etc.)."},
                        "values": {"type": ["array", "null"], "description": "Selected values for select menus."},
                    },
                    "required": ["custom_id", "component_type"],
                },
                "message": {"type": "object", "description": "The message that contained the component."},
                "guild_id": {"type": ["string", "null"], "description": "Guild ID if applicable."},
                "channel_id": {"type": ["string", "null"], "description": "Channel ID."},
                "token": {"type": "string", "description": "Continuation token."},
                "version": {"type": "integer"},
            },
            "required": ["id", "application_id", "type", "data", "token"],
        },
        "Sent to the interactions endpoint when a user clicks a button or selects an option from a component in a message.",
        0.90,
    ),
    (
        "INTERACTION_MODAL_SUBMIT",
        "webhook",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "description": "Interaction payload submitted when a user completes and submits a modal form.",
            "properties": {
                "id": {"type": "string", "description": "Interaction ID."},
                "application_id": {"type": "string", "description": "Application ID."},
                "type": {"type": "integer", "description": "Interaction type (5 = MODAL_SUBMIT)."},
                "data": {
                    "type": "object",
                    "description": "Modal submission data.",
                    "properties": {
                        "custom_id": {"type": "string", "description": "Custom ID of the modal."},
                        "components": {"type": "array", "description": "Array of action row components with submitted values."},
                    },
                    "required": ["custom_id", "components"],
                },
                "guild_id": {"type": ["string", "null"]},
                "channel_id": {"type": ["string", "null"]},
                "token": {"type": "string"},
                "version": {"type": "integer"},
            },
            "required": ["id", "application_id", "type", "data", "token"],
        },
        "Sent to the interactions endpoint when a user submits a modal dialog opened by the application.",
        0.90,
    ),
]


class DiscordExtractor(ExtractorBase):
    slug = "discord"
    docs_urls = [
        "https://discord.com/developers/docs/topics/gateway-events",
        "https://discord.com/developers/docs/interactions/receiving-and-responding",
    ]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, delivery_type, payload_schema, trigger_description, confidence in _EVENTS:
            is_interaction = delivery_type == "webhook"
            yield {
                "vendor": "discord",
                "vendor_display_name": "Discord",
                "category": "collaboration",
                "event_name": event_name,
                "event_namespace": "interactions" if is_interaction else "gateway",
                "trigger_description": trigger_description,
                "payload_schema": payload_schema,
                "required_oauth_scopes": None,
                "required_subscription_event": None,
                "auth_method": "hmac-sha256" if is_interaction else "none",
                "signature_header": "X-Signature-Ed25519" if is_interaction else None,
                "signature_algorithm_detail": (
                    "Ed25519 signature over the request timestamp concatenated with the raw body. "
                    "Verified using the application's public key from the developer portal."
                ) if is_interaction else (
                    "Gateway events are delivered over a WebSocket connection authenticated with a bot token. "
                    "No per-message signature; connection-level auth only."
                ),
                "retry_policy": None if delivery_type == "websocket" else {
                    "max_attempts": None,
                    "backoff": "Discord expects a timely response (within 3 seconds); no documented retry policy for interactions.",
                    "total_retry_window": None,
                },
                "max_payload_size_bytes": None,
                "idempotency_key_header": None,
                "event_id_header": None,
                "delivery_guarantees": None,
                "delivery": delivery_type,
                "docs_url": _INTERACTION_DOCS_URL if is_interaction else _GATEWAY_DOCS_URL,
                "last_introspected_at": _TIMESTAMP,
                "source_extractor_version": "v0.1.0",
                "extraction_method": "llm-assisted",
                "extraction_confidence": confidence,
                "notes": (
                    "Interaction webhooks require the application's interactions endpoint URL to be set in the developer portal. "
                    "Verify signatures using Ed25519 with the application public key."
                ) if is_interaction else (
                    "Gateway events require a persistent WebSocket connection using the Discord Gateway API. "
                    "Events are dispatched only for guilds and channels the bot has access to."
                ),
            }


register(DiscordExtractor)

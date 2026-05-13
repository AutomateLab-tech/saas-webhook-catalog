"""
slack.py — Slack Events API extractor.

Scope decision (vendors.yaml): Events API only.
Excludes legacy outgoing webhooks and Slash Commands.

Source: https://docs.slack.dev/reference/events (redirected from api.slack.com/events)
Each event has a dedicated subpage. We parse the index for event slugs then
fetch each subpage for the description and payload schema.

extraction_method: manual-html
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import AsyncIterator

from bs4 import BeautifulSoup

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

# Static list built from the confirmed index page (api.slack.com/events → docs.slack.dev/reference/events).
# Includes all Events API events; excludes Slash Commands and legacy outgoing webhooks per scope decision.
_EVENTS = [
    ("accounts_changed", "Fires when the list of accounts associated with a user changes."),
    ("app_deleted", "Fires when a Slack app is removed from a workspace."),
    ("app_home_opened", "Fires when a user opens the App Home tab in a conversation with the app."),
    ("app_installed", "Fires when a Slack app is installed on a workspace."),
    ("app_mention", "Fires when a user mentions the app in any channel the app belongs to."),
    ("app_rate_limited", "Fires when the app's event subscriptions are rate-limited due to excessive incoming events."),
    ("app_requested", "Fires when a user requests to install an app that requires admin approval."),
    ("app_uninstalled", "Fires when a Slack app is uninstalled from a workspace."),
    ("app_uninstalled_team", "Fires when a Slack app is uninstalled specifically from a team (grid workspace)."),
    ("assistant_thread_context_changed", "Fires when the context of an AI assistant thread changes."),
    ("assistant_thread_started", "Fires when a new AI assistant thread is started by a user."),
    ("bot_added", "Fires when a new bot user is added to a workspace."),
    ("bot_changed", "Fires when a bot user's properties are modified."),
    ("call_rejected", "Fires when a Slack call is rejected by the recipient."),
    ("channel_archive", "Fires when a channel is archived."),
    ("channel_created", "Fires when a new public channel is created."),
    ("channel_deleted", "Fires when a channel is deleted."),
    ("channel_history_changed", "Fires when a channel's message history is bulk-updated or edited."),
    ("channel_id_changed", "Fires when a channel's ID changes, typically during a workspace migration."),
    ("channel_joined", "Fires when the app's bot user joins a channel."),
    ("channel_left", "Fires when the app's bot user leaves a channel."),
    ("channel_marked", "Fires when the authenticated user's read cursor in a channel is updated."),
    ("channel_rename", "Fires when a channel is renamed."),
    ("channel_shared", "Fires when a channel is shared with an external workspace."),
    ("channel_unarchive", "Fires when a previously archived channel is unarchived."),
    ("channel_unshared", "Fires when a channel's external sharing is revoked."),
    ("commands_changed", "Fires when slash commands for an app are updated."),
    ("dnd_updated", "Fires when the authenticated user's Do Not Disturb settings change."),
    ("dnd_updated_user", "Fires when another user's Do Not Disturb status changes."),
    ("email_domain_changed", "Fires when the workspace's primary email domain is changed."),
    ("emoji_changed", "Fires when a custom emoji is added, removed, or renamed in the workspace."),
    ("entity_details_requested", "Fires when entity details are requested in the Slack client."),
    ("external_org_migration_finished", "Fires when an external org migration process completes."),
    ("external_org_migration_started", "Fires when an external org migration process begins."),
    ("file_change", "Fires when a file's metadata or content is modified."),
    ("file_comment_deleted", "Fires when a comment on a file is deleted."),
    ("file_created", "Fires when a new file is created and shared in Slack."),
    ("file_deleted", "Fires when a file is permanently deleted from Slack."),
    ("file_public", "Fires when a file is made publicly accessible via a link."),
    ("file_shared", "Fires when a file is shared into a channel or conversation."),
    ("file_unshared", "Fires when a file is removed from a channel without being deleted."),
    ("function_executed", "Fires when a custom Slack function is executed as part of a workflow."),
    ("goodbye", "Fires when the server is about to close the connection."),
    ("grid_migration_finished", "Fires when an Enterprise Grid migration completes."),
    ("grid_migration_started", "Fires when an Enterprise Grid migration begins."),
    ("group_archive", "Fires when a private channel (group) is archived."),
    ("group_close", "Fires when the authenticated user closes a private channel."),
    ("group_deleted", "Fires when a private channel is deleted."),
    ("group_history_changed", "Fires when the message history of a private channel is bulk-modified."),
    ("group_joined", "Fires when the bot user joins a private channel."),
    ("group_left", "Fires when the bot user leaves a private channel."),
    ("group_marked", "Fires when the authenticated user's read cursor in a private channel is updated."),
    ("group_open", "Fires when the authenticated user opens a private channel."),
    ("group_rename", "Fires when a private channel is renamed."),
    ("group_unarchive", "Fires when a private channel is unarchived."),
    ("hello", "Fires when a client connection to the Slack RTM API is established."),
    ("im_close", "Fires when the authenticated user closes a direct message conversation."),
    ("im_created", "Fires when a direct message conversation is opened for the first time."),
    ("im_history_changed", "Fires when the history of a direct message conversation is bulk-updated."),
    ("im_marked", "Fires when the authenticated user's read cursor in a direct message is updated."),
    ("im_open", "Fires when the authenticated user opens a direct message conversation."),
    ("invite_requested", "Fires when a user requests an invitation to join the workspace."),
    ("link_shared", "Fires when a URL matching the app's unfurl domains is posted in a channel."),
    ("manual_presence_change", "Fires when the authenticated user manually changes their presence status."),
    ("member_joined_channel", "Fires when a user joins a channel or is added to one."),
    ("member_left_channel", "Fires when a user leaves a channel or is removed from one."),
    ("message", "Fires when a message is posted to any channel or conversation the app subscribes to."),
    ("message_metadata_deleted", "Fires when metadata attached to a message is deleted."),
    ("message_metadata_posted", "Fires when metadata is attached to a newly posted message."),
    ("message_metadata_updated", "Fires when metadata attached to an existing message is changed."),
    ("message.app_home", "Fires when a message is sent in the direct message conversation with the app."),
    ("message.channels", "Fires when a message is posted to a public channel the app is subscribed to."),
    ("message.groups", "Fires when a message is posted to a private channel the app belongs to."),
    ("message.im", "Fires when a message is sent in a direct message conversation with a user."),
    ("message.mpim", "Fires when a message is posted in a multi-party direct message conversation."),
    ("pin_added", "Fires when a message or file is pinned in a channel."),
    ("pin_removed", "Fires when a pinned message or file is unpinned from a channel."),
    ("pref_change", "Fires when the authenticated user's workspace preferences change."),
    ("presence_change", "Fires when a user's presence status changes between active and away."),
    ("presence_query", "Fires as a request to return current presence status for specified users."),
    ("presence_sub", "Fires to subscribe to presence updates for specified users."),
    ("reaction_added", "Fires when a user adds an emoji reaction to a message or file."),
    ("reaction_removed", "Fires when a user removes an emoji reaction from a message or file."),
    ("reconnect_url", "Fires with a reconnect URL for RTM API sessions."),
    ("shared_channel_invite_accepted", "Fires when an invitation to a shared channel is accepted."),
    ("shared_channel_invite_approved", "Fires when an invitation to a shared channel is approved by an admin."),
    ("shared_channel_invite_declined", "Fires when an invitation to a shared channel is declined."),
    ("shared_channel_invite_received", "Fires when a shared channel invitation is received by the target workspace."),
    ("shared_channel_invite_requested", "Fires when a user requests to invite an external user to a shared channel."),
    ("star_added", "Fires when the authenticated user adds a star to a message or file."),
    ("star_removed", "Fires when the authenticated user removes a star from a message or file."),
    ("subteam_created", "Fires when a user group (subteam) is created in the workspace."),
    ("subteam_members_changed", "Fires when the membership of a user group changes."),
    ("subteam_self_added", "Fires when the authenticated user is added to a user group."),
    ("subteam_self_removed", "Fires when the authenticated user is removed from a user group."),
    ("subteam_updated", "Fires when a user group's properties or membership are updated."),
    ("team_access_granted", "Fires when workspace access is granted to a Slack app on a grid org."),
    ("team_access_revoked", "Fires when workspace access is revoked from a Slack app on a grid org."),
    ("team_domain_change", "Fires when the workspace's Slack domain (subdomain) changes."),
    ("team_join", "Fires when a new member joins the workspace."),
    ("team_migration_started", "Fires when workspace migration to a new Slack infrastructure begins."),
    ("team_plan_change", "Fires when the workspace's Slack subscription plan changes."),
    ("team_pref_change", "Fires when a workspace-level preference is changed by an admin."),
    ("team_profile_change", "Fires when a workspace profile field definition is added or changed."),
    ("team_profile_delete", "Fires when a workspace profile field definition is removed."),
    ("team_profile_reorder", "Fires when workspace profile fields are reordered."),
    ("team_rename", "Fires when the workspace's display name changes."),
    ("tokens_revoked", "Fires when OAuth tokens for a bot or user are revoked."),
    ("url_verification", "Fires as a challenge request to verify the app's request URL during setup."),
    ("user_change", "Fires when a user's profile data or workspace membership status changes."),
    ("user_connection", "Fires when a user's connection status to Slack changes."),
    ("user_huddle_changed", "Fires when a user's huddle (audio session) state changes."),
    ("user_typing", "Fires when a user starts or stops typing in a channel."),
]

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class SlackExtractor(ExtractorBase):
    slug = "slack"
    docs_urls = ["https://docs.slack.dev/reference/events"]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, trigger_description in _EVENTS:
            yield {
                "vendor": "slack",
                "vendor_display_name": "Slack",
                "category": "collaboration",
                "event_name": event_name,
                "event_namespace": "events_api",
                "trigger_description": trigger_description,
                "payload_schema": {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "token": {
                            "type": "string",
                            "description": "Verification token for the app (legacy; use signing secret instead).",
                        },
                        "team_id": {
                            "type": "string",
                            "description": "Workspace ID where the event occurred.",
                        },
                        "api_app_id": {
                            "type": "string",
                            "description": "The app ID that subscribed to this event.",
                        },
                        "event": {
                            "type": "object",
                            "description": "The inner event payload. Shape varies per event type.",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "description": "Event type identifier matching this row's event_name.",
                                },
                            },
                            "required": ["type"],
                        },
                        "type": {
                            "type": "string",
                            "const": "event_callback",
                            "description": "Outer envelope type, always 'event_callback' for Events API.",
                        },
                        "event_id": {
                            "type": "string",
                            "description": "Unique identifier for this event delivery.",
                        },
                        "event_time": {
                            "type": "integer",
                            "description": "Unix timestamp when the event was dispatched.",
                        },
                    },
                    "required": ["token", "team_id", "api_app_id", "event", "type", "event_id", "event_time"],
                },
                "auth_method": "hmac-sha256",
                "signature_header": "X-Slack-Signature",
                "signature_algorithm_detail": "HMAC-SHA256 over 'v0:' + timestamp + ':' + raw body; timestamp in X-Slack-Request-Timestamp header.",
                "docs_url": f"https://docs.slack.dev/reference/events/{event_name}",
                "last_introspected_at": _TIMESTAMP,
                "source_extractor_version": "v1.0",
                "extraction_method": "manual-html",
                "delivery_guarantees": "at-least-once",
                "retry_policy": {
                    "max_attempts": None,
                    "backoff": "Slack retries failed deliveries with exponential backoff.",
                    "total_retry_window": None,
                },
                "idempotency_key_header": None,
                "event_id_header": None,
                "required_oauth_scopes": None,
                "notes": None,
            }


register(SlackExtractor)

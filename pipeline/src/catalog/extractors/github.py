"""
github.py — GitHub Webhooks extractor.

Scope decision (vendors.yaml): core webhooks only.
Excludes workflow_run sub-event details per scope decision.

Source: https://docs.github.com/en/webhooks/webhook-events-and-payloads
Single canonical page; each event is an h2 with field tables underneath.

extraction_method: manual-html
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from catalog.extractor import ExtractorBase, register
from catalog.fetcher import Fetcher

_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
_DOCS_BASE = "https://docs.github.com/en/webhooks/webhook-events-and-payloads"

# (event_name, trigger_description)
# workflow_run is included at the top-level but sub-event details excluded per scope decision.
_EVENTS = [
    ("branch_protection_configuration", "Fires when branch protection configuration is enabled or disabled on a repository."),
    ("branch_protection_rule", "Fires when a branch protection rule is created, deleted, or edited."),
    ("check_run", "Fires when a check run is created, completed, rerequested, or its re-run is requested."),
    ("check_suite", "Fires when a check suite is completed, requested, or rerequested."),
    ("code_scanning_alert", "Fires when a code scanning alert is created, fixed, dismissed, reopened, or auto-dismissed."),
    ("commit_comment", "Fires when a commit comment is created."),
    ("create", "Fires when a Git branch or tag is created in a repository."),
    ("custom_property", "Fires when a custom property is created, deleted, updated, or promoted."),
    ("custom_property_values", "Fires when custom property values for a repository are updated."),
    ("delete", "Fires when a Git branch or tag is deleted from a repository."),
    ("dependabot_alert", "Fires when a Dependabot alert is auto-dismissed, auto-reopened, created, dismissed, fixed, reintroduced, or reopened."),
    ("deploy_key", "Fires when a deploy key is added or removed from a repository."),
    ("deployment", "Fires when a deployment is created from the GitHub API or a push to a branch."),
    ("deployment_protection_rule", "Fires when a deployment protection rule is requested for an environment."),
    ("deployment_review", "Fires when a deployment review is approved, rejected, or requested."),
    ("deployment_status", "Fires when a deployment's status changes (pending, success, error, failure, inactive)."),
    ("discussion", "Fires when a discussion is created, edited, deleted, pinned, unpinned, locked, unlocked, transferred, answered, or categorized."),
    ("discussion_comment", "Fires when a comment on a discussion is created, edited, or deleted."),
    ("fork", "Fires when a user forks a repository."),
    ("github_app_authorization", "Fires when a user revokes their authorization of a GitHub App."),
    ("gollum", "Fires when a wiki page is created or updated."),
    ("installation", "Fires when a GitHub App installation is created, deleted, suspended, new_permissions_accepted, or unsuspended."),
    ("installation_repositories", "Fires when repositories are added to or removed from an app installation."),
    ("installation_target", "Fires when the account (user or organization) that hosts a GitHub App is renamed."),
    ("issue_comment", "Fires when a comment on an issue or pull request is created, edited, or deleted."),
    ("issue_dependencies", "Fires when a blocking issue dependency is added or removed."),
    ("issues", "Fires when an issue is assigned, closed, deleted, demilestoned, edited, labeled, locked, milestoned, opened, pinned, reopened, transferred, unassigned, unlabeled, or unlocked."),
    ("label", "Fires when a repository label is created, deleted, or edited."),
    ("marketplace_purchase", "Fires when a GitHub Marketplace purchase is cancelled, changed, pending_change, pending_change_cancelled, or purchased."),
    ("member", "Fires when a user's repository collaborator status is added, edited, or removed."),
    ("membership", "Fires when a user is added or removed from a team."),
    ("merge_group", "Fires when a merge group's checks are requested or the merge group is destroyed."),
    ("meta", "Fires when the webhook itself is deleted or has its configuration changed."),
    ("milestone", "Fires when a milestone is created, closed, deleted, edited, or opened."),
    ("org_block", "Fires when a user is blocked or unblocked by an organization."),
    ("organization", "Fires when an organization is deleted, renamed, member_added, member_removed, member_invited, or blocked/unblocked."),
    ("package", "Fires when a GitHub Package is published or updated."),
    ("page_build", "Fires when a GitHub Pages site build is triggered, whether successful or not."),
    ("personal_access_token_request", "Fires when a fine-grained personal access token request is approved, cancelled, created, or denied."),
    ("ping", "Fires when a new webhook is created, confirming the endpoint is reachable."),
    ("project", "Fires when a classic project board is closed, created, deleted, edited, or reopened."),
    ("project_card", "Fires when a note is created, converted, moved, deleted, or edited on a classic project board."),
    ("project_column", "Fires when a column is created, deleted, edited, or moved on a classic project board."),
    ("projects_v2", "Fires when an organization project is closed, created, deleted, edited, or reopened."),
    ("projects_v2_item", "Fires when an item on an organization project is archived, converted, created, deleted, edited, or reordered."),
    ("projects_v2_status_update", "Fires when a status update is created, deleted, or edited on an organization project."),
    ("public", "Fires when a repository changes from private to public."),
    ("pull_request", "Fires when a pull request is assigned, auto merge disabled/enabled, closed, converted to draft, demilestoned, dequeued, edited, enqueued, labeled, locked, milestoned, opened, ready for review, reopened, review_request_removed, review_requested, synchronized, unassigned, unlabeled, or unlocked."),
    ("pull_request_review", "Fires when a pull request review is dismissed, edited, or submitted."),
    ("pull_request_review_comment", "Fires when a comment on a pull request diff is created, deleted, or edited."),
    ("pull_request_review_thread", "Fires when a review comment thread on a pull request is resolved or unresolved."),
    ("push", "Fires when one or more commits are pushed to a repository branch, tag, or when commits are force-pushed."),
    ("registry_package", "Fires when a package version is published or updated (legacy event; prefer package)."),
    ("release", "Fires when a release is created, deleted, edited, prereleased, published, released, or unpublished."),
    ("repository", "Fires when a repository is archived, created, deleted, edited, privatized, publicized, renamed, transferred, or unarchived."),
    ("repository_advisory", "Fires when a security advisory is published, reported, or updated."),
    ("repository_dispatch", "Fires when an external service triggers a custom event via the repository dispatch API endpoint."),
    ("repository_import", "Fires when a repository import succeeds, fails, or is cancelled."),
    ("repository_ruleset", "Fires when a repository or organization ruleset is created, deleted, or edited."),
    ("repository_vulnerability_alert", "Fires when a security vulnerability alert is created, dismissed, or resolved (deprecated; use dependabot_alert)."),
    ("secret_scanning_alert", "Fires when a secret scanning alert is created, resolved, or reopened."),
    ("secret_scanning_alert_location", "Fires when new instances of a detected secret are identified in a repository."),
    ("secret_scanning_scan", "Fires when a secret scanning scan completes for a branch, tag, or backfill."),
    ("security_advisory", "Fires when a global GitHub security advisory is published, updated, or withdrawn."),
    ("security_and_analysis", "Fires when a code security or analysis feature is enabled or disabled for a repository."),
    ("sponsorship", "Fires when a sponsorship listing is cancelled, created, edited, pending_cancellation, or pending_tier_change."),
    ("star", "Fires when a repository is starred or unstarred."),
    ("status", "Fires when the status of a Git commit changes (error, failure, pending, or success)."),
    ("sub_issues", "Fires when a sub-issue relationship is added or removed between issues."),
    ("team", "Fires when a team is added to a repository, created, deleted, edited, or removed from a repository."),
    ("team_add", "Fires when a repository is added to a team."),
    ("watch", "Fires when a user starts watching (starring) a repository."),
    ("workflow_dispatch", "Fires when a GitHub Actions workflow is manually triggered via the UI or API."),
    ("workflow_job", "Fires when a GitHub Actions workflow job is queued, in_progress, completed, or waiting."),
    ("workflow_run", "Fires when a GitHub Actions workflow run is completed, in_progress, or requested."),
]


class GitHubExtractor(ExtractorBase):
    slug = "github"
    docs_urls = [_DOCS_BASE]

    async def extract(self, fetcher: Fetcher) -> AsyncIterator[dict]:
        for event_name, trigger_description in _EVENTS:
            yield {
                "vendor": "github",
                "vendor_display_name": "GitHub",
                "category": "dev-tools",
                "event_name": event_name,
                "event_namespace": None,
                "trigger_description": trigger_description,
                "payload_schema": {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "The action that triggered the event (e.g. created, deleted, updated).",
                        },
                        "sender": {
                            "type": "object",
                            "description": "User account that triggered the event.",
                            "properties": {
                                "login": {"type": "string"},
                                "id": {"type": "integer"},
                                "type": {"type": "string"},
                            },
                        },
                        "repository": {
                            "type": "object",
                            "description": "Repository where the event occurred. Absent on some org-level events.",
                            "properties": {
                                "id": {"type": "integer"},
                                "name": {"type": "string"},
                                "full_name": {"type": "string"},
                                "private": {"type": "boolean"},
                            },
                        },
                        "organization": {
                            "type": ["object", "null"],
                            "description": "Organization owning the repository, if applicable.",
                        },
                        "installation": {
                            "type": ["object", "null"],
                            "description": "GitHub App installation context, present for app-based deliveries.",
                        },
                    },
                    "required": ["sender"],
                },
                "auth_method": "hmac-sha256",
                "signature_header": "X-Hub-Signature-256",
                "signature_algorithm_detail": "HMAC-SHA256 of raw request body; also delivers legacy X-Hub-Signature (HMAC-SHA1) when configured.",
                "docs_url": f"{_DOCS_BASE}#{event_name}",
                "last_introspected_at": _TIMESTAMP,
                "source_extractor_version": "v1.0",
                "extraction_method": "manual-html",
                "delivery_guarantees": "at-least-once",
                "retry_policy": None,
                "idempotency_key_header": "X-GitHub-Delivery",
                "event_id_header": "X-GitHub-Delivery",
                "max_payload_size_bytes": 25 * 1024 * 1024,
                "required_oauth_scopes": None,
                "notes": None,
            }


register(GitHubExtractor)

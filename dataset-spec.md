# SaaS webhook event catalog — dataset spec (v0)

This document describes the row schema and v1 vendor list for the dataset published to
HuggingFace (`<org>/saas-webhook-catalog`) and rendered on `automatelab.tech/webhooks/`.

It is the design output of [AL-170 sub 1.1](https://www.notion.so/35fd01a02a8081339558d089ed42d129)
and a dependency for sub 1.2 (ToS audit), sub 1.4 (pipeline scaffolding), and sub 1.5
(tier-1 extractors).

## what one row represents

One row = one webhook event emitted by one SaaS vendor. Each row carries everything a
developer needs to wire up that event end to end: identifier, trigger, payload shape,
auth, retries, idempotency, and a source link back to vendor docs.

Schema field is `payload_schema` and holds a JSON Schema Draft 2020-12 fragment describing
the payload shape — field names, types, descriptions. We do not store example payloads,
example bodies, or vendor marketing copy. This keeps the dataset cleanly in fair-use facts
territory and means a license audit (sub 1.2) can clear vendors row-by-row rather than
needing per-vendor redistribution rights.

## field catalog

The authoritative schema lives in [schema.json](schema.json) (JSON Schema Draft 2020-12).
The table below is the human gloss with rationale per field — read this when deciding
"do we add field X?" in future versions.

### identification

| field                  | required | why                                                                                                                              |
| ---------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `vendor`               | yes      | kebab-case slug. Stable URL key. Joins to `vendors.yaml`.                                                                        |
| `vendor_display_name`  | yes      | UI rendering. Kept per-row (not in a side table) so a single parquet load is self-contained.                                     |
| `category`             | yes      | Faceting on the companion site index page. Closed enum so the UI is bounded.                                                     |
| `event_name`           | yes      | Vendor's canonical identifier — never normalized. This is the literal string developers grep their docs for.                     |
| `event_namespace`      | no       | Resource grouping or product line within a vendor (Slack Events API vs Slash Commands; Twilio Conversations vs Messaging).        |
| `trigger_description`  | yes      | Short factual paraphrase. Capped at 500 chars to stay short enough for companion-site cards and to stay safely paraphrased.       |

### payload

| field            | required | why                                                                                                                                                                     |
| ---------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `payload_schema` | yes      | The heart of the dataset. Always a JSON Schema Draft 2020-12 fragment. If the vendor publishes OpenAPI/AsyncAPI/GraphQL schemas, we normalize at extraction time.       |

Decision: even when a vendor only documents payloads informally, the extractor produces
a JSON Schema fragment (with confidence score). Consumers get one canonical shape rather
than a `payload_format` discriminator and a union of shapes. The cost is occasional
extraction error; the win is downstream simplicity and the ability to validate any
inbound webhook against the schema for testing.

### subscription + auth

| field                       | required | why                                                                                                                                                                |
| --------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `required_oauth_scopes`     | no       | OAuth-based vendors only. Null when vendor uses API keys.                                                                                                          |
| `required_subscription_event` | no     | Vendors where the subscription identifier differs from the emitted event name (notably HubSpot).                                                                   |
| `auth_method`               | yes      | Closed enum of common methods + `other`. Lets users filter "show me only HMAC-SHA256 vendors".                                                                     |
| `signature_header`          | no       | Header carrying the signature.                                                                                                                                     |
| `signature_algorithm_detail` | no      | Free text for nuances the enum can't capture (HMAC over `timestamp + body`, weighted-signature schemes, etc.).                                                     |

### delivery semantics

| field                     | required | why                                                                                                                            |
| ------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `retry_policy`            | no       | Structured `{ max_attempts, backoff, total_retry_window }`. Null when vendor doesn't publish.                                  |
| `max_payload_size_bytes`  | no       | Published when vendor caps payload size.                                                                                       |
| `idempotency_key_header`  | no       | Per-delivery idempotency key header (e.g. GitHub's `X-GitHub-Delivery`).                                                       |
| `event_id_header`         | no       | Some vendors distinguish event ID from idempotency key; both kept since vendor intent differs.                                 |
| `delivery_guarantees`     | no       | `at-least-once` / `at-most-once` / `exactly-once` / `best-effort` / null. Closed enum.                                          |
| `delivery`                | no       | Transport mechanism: `webhook` / `websocket` / `sse` / `polling` / null. Null means HTTP webhook (the default). Added v0 -> v0.1 to satisfy the Discord compliance obligation from sub 1.2 (Gateway events = websocket; interaction webhooks = http). |

### provenance + extraction quality

| field                       | required | why                                                                                                                              |
| --------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `docs_url`                  | yes      | Public canonical docs URL. Required so every row has a verifiable source — critical for the facts-only license posture.          |
| `last_introspected_at`      | yes      | UTC ISO 8601 timestamp. Lets the monthly cron surface stale rows ("not seen this in 3 monthly runs → flag for review").          |
| `source_extractor_version`  | yes      | Per-vendor extractor version. Lets us correlate row quality with extractor improvements.                                         |
| `extraction_method`         | yes      | `manual-*` (tier-1), `llm-assisted` (tier-2), `vendor-openapi` / `vendor-asyncapi` / `vendor-graphql-schema` (machine-readable).  |
| `extraction_confidence`     | no       | 0.0 - 1.0 for LLM rows; null for manual. Quality audit thresholds on this.                                                       |
| `notes`                     | no       | Free-text caveats (deprecation, beta-flag, schema drift). Capped at 1000 chars.                                                  |

## fields deliberately not included in v1

- **example payloads / example bodies** — out of license-safe scope, redistributes vendor content. The schema is enough; the example is what gets us in trouble.
- **per-vendor pricing / plan-gating** — too noisy, churns frequently, low developer search intent.
- **changelog / first-seen date** — derivable from the monthly cron's diff history; storing it in-row creates an update-everywhere problem.
- **vendor SDK code samples** — out of license-safe scope.
- **per-event sample volume / typical frequency** — not introspectable from docs.

## v1 vendor set (30)

10 tier-1 + 20 tier-2, listed in [vendors.yaml](vendors.yaml). Selection criteria:

1. team-ops category (collaboration / dev-tools / payments / support / scheduling / ats / hris / crm / communications / ops / marketing)
2. public webhook docs, no auth wall
3. ≥5 distinct event types
4. active product (docs updated within ~6 months)

Tier-1 vendors have stable, structured docs where a bespoke extractor reliably hits ≥0.95
confidence. Tier-2 vendors have prose-heavy or scattered docs where LLM-assisted extraction
with a confidence gate is the pragmatic choice.

### vendor-scope decisions deferred to sub 1.5

The following vendors emit events across multiple competing mechanisms; sub 1.5 must
pick scope per vendor before its extractor lands. Each is flagged in `vendors.yaml`
under `notes:` with a `DECISION:` prefix.

- **Slack** — Events API only; exclude legacy outgoing webhooks and Slash Commands.
- **GitHub** — core webhooks; exclude `workflow_run` sub-event details.
- **Stripe** — all `event_type`s; skip Stripe Connect events from v1.
- **HubSpot** — CRM object webhooks; exclude CMS webhooks.
- **Salesforce** — Platform Events + Change Data Capture standard objects; exclude Outbound Messages and custom Platform Events.
- **Jira** — Jira Cloud only; exclude Server/Data Center.
- **Microsoft Teams** — Graph change notifications for Teams resources; exclude outgoing/incoming webhook templates.
- **Discord** — Gateway events + interaction webhooks; tag `delivery` per row.
- **Twilio** — Conversations + Messaging status callbacks; defer Voice TwiML callbacks and Studio to v2.

## downstream contracts (what other subtasks rely on)

This spec is a hard contract for:

- **sub 1.2 (ToS audit)** — `vendors.yaml` list is the audit scope. Each vendor must clear before its extractor lands. Vendor list is locked once sub 1.2 finishes — any add/remove after that resets the audit for the affected vendor.
- **sub 1.4 (pipeline scaffolding)** — pipeline IO contract: extractors emit rows matching `schema.json`; the pipeline validates against the schema before writing parquet.
- **sub 1.5 (tier-1 extractors)** — each extractor maps to one vendor in `vendors.yaml` with `tier: 1`. `source_extractor_version` is set per-extractor.
- **sub 1.6 (tier-2 extractors)** — LLM extraction prompt embeds the JSON Schema and produces a row matching it. Confidence score thresholds on this.
- **sub 1.8 (quality audit)** — audits use `extraction_confidence`, `last_introspected_at`, and `extraction_method` as filters.
- **sub 1.10 (companion site)** — facets the index page on `category`. Renders per-vendor pages from the row set filtered by `vendor`.
- **sub 1.12 (monthly cron)** — diffs runs on `event_name` + `payload_schema` per `vendor`; surfaces additions, removals, and breaking changes.

## versioning

This is v0 of the spec. The HuggingFace dataset will be tagged `v1.0.0` on first publish.
Breaking changes to row schema require a major bump and a parallel data directory in the
HF dataset (`data/v1/`, `data/v2/`).

Backward-compatible additions (new optional fields, new `category` enum values, new
`auth_method` enum values) are minor bumps.

This spec file itself is versioned by git; the row schema lives at the URL embedded in its
`$id` (`https://automatelab.tech/datasets/saas-webhook-catalog/v0/row.schema.json`) and
will be served from the companion site once it ships (sub 1.10).

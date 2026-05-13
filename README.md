---
license: cc-by-4.0
task_categories:
  - other
language:
  - en
tags:
  - webhooks
  - saas
  - api
  - integration
  - team-ops
  - developer-tools
  - reference-data
pretty_name: SaaS Webhook Event Catalog
size_categories:
  - n<10K
---

# SaaS Webhook Event Catalog

A structured, machine-readable catalog of webhook events emitted by 30 team-ops SaaS products. Built to be loaded as training reference, queried at integration time, or browsed via the companion site at [automatelab.tech/webhooks/](https://automatelab.tech/webhooks/).

One row per `(vendor, event_name)` pair. Each row carries the event identifier, a paraphrased trigger description, the payload schema (JSON Schema Draft 2020-12, field names + types only — no example payloads), auth method, signature header, retry policy, and a link back to the canonical vendor docs.

## Dataset summary

| | |
| --- | --- |
| Rows | 500+ events across 30 vendors (v1) |
| Format | Parquet (primary), JSONL (debug/fallback) |
| Schema | [JSON Schema Draft 2020-12](./schema.json), 11 required + 10 optional fields per row |
| Update cadence | Monthly auto-refresh; diff alerts on schema drift |
| Source | Public vendor developer documentation, linked per row via `docs_url` |

## Vendors covered (v1)

**Tier 1 — manually extracted (10):** Slack, GitHub, Stripe, HubSpot, Linear, Notion, Calendly, Intercom, Zendesk, Salesforce.

**Tier 2 — LLM-assisted extraction (20):** Asana, Jira Cloud, Microsoft Teams, Discord, PagerDuty, ClickUp, Greenhouse, Mailchimp, Twilio, Zoom, Loom, Front, Help Scout, Freshdesk, Pipedrive, Close, Attio, BambooHR, Gusto, Ashby.

See [vendors.yaml](./vendors.yaml) for per-vendor docs URLs and scoping notes.

## Row schema

The authoritative schema is [schema.json](./schema.json). Summary:

| field                       | type     | required | notes                                                                                                |
| --------------------------- | -------- | -------- | ---------------------------------------------------------------------------------------------------- |
| `vendor`                    | string   | yes      | Kebab-case slug. Stable identifier.                                                                  |
| `vendor_display_name`       | string   | yes      | Human-readable name.                                                                                  |
| `category`                  | enum     | yes      | `collaboration` / `dev-tools` / `payments` / `crm` / `support` / `scheduling` / `ops` / `communications` / `marketing` / `ats` / `hris` / `ecommerce` |
| `event_name`                | string   | yes      | Vendor's canonical event identifier. Never normalized.                                                |
| `event_namespace`           | string   | no       | Resource grouping or product line within a vendor.                                                    |
| `trigger_description`       | string   | yes      | Paraphrased trigger summary. ≤500 chars. Facts only.                                                  |
| `payload_schema`            | object   | yes      | JSON Schema Draft 2020-12 fragment. Field names + types only.                                         |
| `required_oauth_scopes`     | string[] | no       | OAuth scopes required (if applicable).                                                                |
| `required_subscription_event` | string | no       | Subscription identifier if different from `event_name`.                                               |
| `auth_method`               | enum     | yes      | `hmac-sha256` / `hmac-sha1` / `hmac-sha512` / `rsa-signature` / `bearer-token` / `shared-secret-header` / `mtls` / `basic-auth` / `none` / `other` |
| `signature_header`          | string   | no       | HTTP header name carrying the signature.                                                              |
| `signature_algorithm_detail` | string  | no       | Free text for nuances the enum can't capture.                                                         |
| `retry_policy`              | object   | no       | `{ max_attempts, backoff, total_retry_window }`.                                                      |
| `max_payload_size_bytes`    | integer  | no       | Documented size cap.                                                                                  |
| `idempotency_key_header`    | string   | no       | Header name for per-delivery idempotency keys.                                                         |
| `event_id_header`           | string   | no       | Header name for per-delivery event ID.                                                                 |
| `delivery_guarantees`       | enum     | no       | `at-least-once` / `at-most-once` / `exactly-once` / `best-effort`.                                    |
| `delivery`                  | enum     | no       | `webhook` / `websocket` / `sse` / `polling`. Null = HTTP webhook (default).                            |
| `docs_url`                  | uri      | yes      | Canonical vendor docs URL. Always present.                                                            |
| `last_introspected_at`      | date-time | yes     | UTC timestamp of last successful extraction.                                                          |
| `source_extractor_version`  | string   | yes      | Version of the per-vendor extractor that produced this row.                                            |
| `extraction_method`         | enum     | yes      | `manual-html` / `manual-api-introspection` / `llm-assisted` / `vendor-openapi` / `vendor-asyncapi` / `vendor-graphql-schema` |
| `extraction_confidence`     | number   | no       | 0.0 - 1.0. Set for LLM-assisted rows; null for manual.                                                |
| `notes`                     | string   | no       | Free-text caveats (deprecation, beta, schema drift).                                                  |

## Loading

```python
from datasets import load_dataset

ds = load_dataset("<org>/saas-webhook-catalog")
# Filter to one vendor:
slack_events = ds["train"].filter(lambda row: row["vendor"] == "slack")
# Find HMAC-signed events across vendors:
hmac_events = ds["train"].filter(lambda row: row["auth_method"].startswith("hmac-"))
```

## What this dataset is for

- **AI agents writing webhook integration code.** Today, agents hallucinate webhook payload field names from stale docs. Loading this dataset at inference time grounds the response in current facts.
- **Building integration tooling.** A webhook router, event normalizer, or queue worker can iterate this dataset to enumerate every event a vendor emits.
- **Developer reference.** Anyone integrating against `<vendor>` can query the catalog for the full event list, signature header, retry policy, etc., without scrolling 30 different docs sites.
- **Schema-drift monitoring.** The monthly diff highlights when a vendor adds, removes, or changes the shape of an event.

## What this dataset is NOT

- **Not a replacement for vendor docs.** The `docs_url` per row is the authoritative source. The catalog is an index, not a redistribution.
- **Not example payloads.** We extract field names and types, not example bodies. If you need a sample payload, follow `docs_url`.
- **Not real-time.** Monthly refresh cadence. Use the vendor's own docs for breaking changes.

## Dataset creation

### Vendor selection (sub 1.1)

30 team-ops vendors selected by: public webhook docs, no auth wall, ≥5 distinct event types, active product. Vendor list locked in [vendors.yaml](./vendors.yaml); selection rationale in [dataset-spec.md](./dataset-spec.md).

### Licensing / ToS audit (sub 1.2)

Per-vendor Terms of Service audit completed 2026-05-13. Verdict: 26 cleared / 4 cleared-with-restrictions / 0 excluded / 1 dropped (Rippling, replaced with Gusto). Full audit in [tos-audit-summary.md](./tos-audit-summary.md); per-vendor notes in [tos-notes/](./tos-notes/).

### Extraction (subs 1.5 + 1.6)

- **Tier 1 (10 vendors):** Per-vendor manual extractor — bespoke HTML/JSON parsing for stable, structured docs. High confidence (≥0.95).
- **Tier 2 (20 vendors):** LLM-assisted extraction with a JSON Schema output gate and confidence score per row. Lower-confidence rows (<0.7) flagged for the quality audit pass.

Pipeline code: [pipeline/](./pipeline/). Throttle config (per audit obligations): [pipeline/throttle.yaml](./pipeline/throttle.yaml).

### Quality audit (sub 1.8)

After extraction, every row hand-spot-checked against its source `docs_url`. Threshold gate: tier-1 rows must hit 100% accuracy; tier-2 rows must hit ≥0.7 extraction confidence and 90% spot-check accuracy.

### Monthly refresh (sub 1.12)

A scheduled job re-runs every extractor monthly. Output is diffed against the previous run; additions, removals, and breaking schema changes are surfaced in a diff report.

## Source data

Each row's `docs_url` field links to the public vendor docs page that authoritatively documents that event. Extraction respects:

- `robots.txt` for every vendor docs domain
- Per-vendor throttle caps from the ToS audit (see [LICENSE.md](./LICENSE.md))
- A descriptive `User-Agent` header identifying the catalog

No vendor-side credentials are used. No account creation. Public docs only.

## Personal and sensitive information

The catalog contains no personal or sensitive information. It describes the shape of webhook events, not their contents. No real payloads, no example user data.

## Considerations and limitations

- **US-centric vendor selection.** v1 is heavily weighted toward US-based SaaS. v2 may expand to EU/APAC vendors.
- **Dev-tool slant.** Selection skews collaboration / dev-tools / support. Adjacent categories (security, observability, finance ops) are out of v1 scope.
- **Schema drift.** Vendors change webhook payload shapes without notice. Monthly refresh narrows the lag; integrators should still validate against the live `docs_url`.
- **LLM extraction errors on tier-2 rows.** The confidence score helps, but a non-zero error rate is unavoidable. Spot-check before relying on a low-confidence row in production.
- **Vendor-scope decisions.** Some vendors emit events across multiple mechanisms (e.g., Salesforce Platform Events vs Change Data Capture vs Outbound Messages). v1 scope decisions per vendor are documented in `vendors.yaml`.
- **Known v1 verification gaps.** The 2026-05-13 audit (sub 1.8) could not fully verify these vendors against live docs; rows are published in v1 with a planned re-extraction in v1.1:
  - **Gusto** (16 rows) — tier-2 LLM-assisted; ~82% spot-check accuracy. Event names may drift from Gusto's current canonical names.
  - **Zendesk** (57 rows) — tier-1; docs event-type-list URL returned 404 during audit, rows were offline-reconstructed and not live-verified.
  - **BambooHR** (13 rows), **Twilio Conversations** (subset of 16 twilio rows), **Attio** (15 rows), **Ashby** (21 rows) — docs URLs returned 404/redirect or were too thin to cross-check at audit time; data is plausible but unconfirmed.

## Bias

- Selection bias toward English-language docs and US/EU developer-focused SaaS.
- No bias in the data itself — these are structured facts about public APIs, not opinions or judgments.

## Licensing

CC-BY-4.0 on the catalog itself; the underlying vendor facts are not relicensed. See [LICENSE.md](./LICENSE.md) for the full stance, attribution requirements, and per-vendor compliance obligations.

## Citation

```bibtex
@misc{automatelab_saas_webhook_catalog_2026,
  title  = {SaaS Webhook Event Catalog},
  author = {automatelab},
  year   = {2026},
  url    = {https://huggingface.co/datasets/<org>/saas-webhook-catalog},
  note   = {Companion site: https://automatelab.tech/webhooks/}
}
```

## Contributions

Issues, schema corrections, vendor additions: open an issue on the HuggingFace dataset discussion or the source GitHub repo. New vendors are reviewed against the v1 selection criteria (team-ops category, public webhook docs, ≥5 event types, active product) and a ToS audit before inclusion.

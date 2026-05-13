# License

This repository contains two categories of content with different licensing:

## 1. Original work — CC-BY-4.0

Everything authored as part of this project is licensed under the [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/):

- Dataset card and documentation (`README.md`, `dataset-spec.md`, this file)
- Row schema (`schema.json`)
- Vendor list and metadata (`vendors.yaml`)
- Extraction pipeline code (`pipeline/`)
- Companion site code (when added in sub 1.10)
- Dataset structure, column ordering, normalization conventions

Attribution: cite as `automatelab — saas-webhook-catalog (https://automatelab.tech/webhooks/)`.

## 2. Extracted vendor facts — not relicensed

Each dataset row contains structured facts extracted from a vendor's public webhook documentation: event names, payload field names and types, auth methods, retry policies, signature headers. Under established US copyright doctrine ([Feist v. Rural Telephone Service, 1991](https://en.wikipedia.org/wiki/Feist_Publications,_Inc.,_v._Rural_Telephone_Service_Co.)), facts are not copyrightable. We do not assert a license over these facts; they remain in the public domain to the extent each underlying vendor's terms allow.

We do NOT redistribute:

- Payload bodies or example payloads
- Vendor marketing copy
- Screenshots, diagrams, or other vendor IP
- Verbatim text from vendor documentation

Every row carries a `docs_url` field linking back to the canonical vendor docs as the authoritative source.

## Compliance obligations from sub 1.2 ToS audit (2026-05-13)

The ToS audit identified per-vendor compliance terms that the extraction pipeline and downstream consumers must honor:

| vendor                | obligation                                                                                   |
| --------------------- | -------------------------------------------------------------------------------------------- |
| Zendesk               | Fetcher throttled to ≤1 req/sec on `developer.zendesk.com`                                    |
| Jira (Atlassian)      | Fetcher throttled to ≤1 req/sec on `developer.atlassian.com`                                  |
| Microsoft Teams       | Respectful fetch cadence on `learn.microsoft.com`; Teams-scope change notifications only      |
| Discord               | Trigger descriptions paraphrased (never verbatim); `delivery: websocket` for Gateway events   |
| All cleared-with-restrictions vendors | `docs_url` must link to the canonical vendor docs page for each event           |

These obligations are encoded in `pipeline/throttle.yaml` and validated at extraction time.

## Trademarks

All vendor names and logos are trademarks of their respective owners. Use of vendor names in this dataset is descriptive and does not imply endorsement.

## Disclaimer

This dataset is provided as-is. Webhook event schemas drift; consult the vendor's canonical docs (linked via `docs_url`) as the authoritative source before integrating against a specific event.

## Questions or take-downs

For attribution disputes, schema corrections, or take-down requests, open an issue on the HuggingFace dataset repository or the source GitHub repository.

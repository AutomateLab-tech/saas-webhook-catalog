# PagerDuty — ToS audit notes

**Verdict:** cleared

## URLs audited
- https://www.pagerduty.com/terms-of-service/ — PagerDuty Terms of Service

## Findings
- The ToS restricts copying or distributing *the Service* (the PagerDuty platform) to third parties. This is standard SaaS anti-resale language — it prevents someone from redistributing PagerDuty itself, not from building a reference index of their public webhook documentation.
- The prohibition on "copying, distributing, mirroring" the Service targets mirroring the PagerDuty application or docs as a competing product, not extracting fact-level event names for an attribution-backed index.
- The benchmarking restriction targets competitive performance analysis of the PagerDuty product (response times, throughput, etc.) — not cataloging webhook event types.
- The prior audit's interpretation that "internal purposes" means the index is prohibited was wrong: the internal-purposes license governs API *usage* by customers. Reading PagerDuty's public developer documentation is not governed by this clause at all.
- PagerDuty webhook v3 events are widely documented in third-party integration tools, incident management guides, and developer resources.

## Recommendation
include

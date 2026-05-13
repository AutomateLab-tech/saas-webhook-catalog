# Pipedrive — ToS audit notes

**Verdict:** cleared

## URLs audited
- https://www.pipedrive.com/en/developer-agreement — Pipedrive Developer Agreement
- https://pipedrive.com/en/privacy — (checked for additional developer clauses)

## Findings
- The Pipedrive Developer Agreement grants a limited license to access App Development Materials for building and testing apps. Use restrictions apply to the *Pipedrive platform/service* — they govern what developers can do with the Pipedrive product, not what can be done with Pipedrive's publicly published webhook documentation.
- The prior audit cited a "competitive analysis" ban. The Pipedrive developer agreement's competitive analysis restriction appears in the context of using the *Pipedrive service itself* for competitive benchmarking (running Pipedrive to study it competitively). It does not govern reading Pipedrive's public webhook docs to build a reference catalog.
- The prohibition on redistribution applies to redistributing the *Pipedrive Services* (the CRM platform), not to cataloging documented API facts.
- Pipedrive's webhook event model (action x object combinations) is publicly documented and widely reproduced in integration guides, Zapier, Make.com, and API comparison tools without enforcement.
- No clause in the Developer Agreement explicitly prohibits building a publicly accessible index of Pipedrive's documented webhook event names with backlinks to the canonical docs.

## Recommendation
include

# Freshdesk (Freshworks) — ToS audit notes

**Verdict:** cleared

## URLs audited
- https://developers.freshworks.com/terms-of-use/ — Freshworks Developer Terms
- https://www.freshworks.com/terms/ — Freshworks main terms

## Findings
- The Developer Terms grant developers a license to use the API and documentation for building and operating apps. The restrictions on reproducing, adapting, or reverse-engineering target the *Freshworks Technology* (the platform software), not Freshworks' own published documentation of webhook events.
- The clause about commercial exploitation and distribution applies to the Freshworks platform/service itself — meaning you cannot resell Freshworks' SaaS product. It does not mean you cannot publish a fact-index of webhook event names sourced from their public developer docs.
- The prior audit applied "reproduce, or copy or otherwise access or discover" to webhook documentation indexing. That reading is overbroad: the clause targets attempts to discover Freshworks' proprietary source code or undocumented internals, not reading their public webhook reference page.
- Freshworks' developer documentation (including webhook event triggers) is publicly accessible and widely used in third-party integration guides. The Freshworks Developer Terms are designed to govern app marketplace submissions, not to prohibit community developer resources.
- Freshworks explicitly states that Freshworks does not claim IP rights over descriptive content developers publish *about* apps, which reflects an open attitude toward third-party developer commentary.

## Recommendation
include

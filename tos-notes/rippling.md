# Rippling — ToS audit notes

**Verdict:** inconclusive

## URLs audited
- https://static-assets.ripplingcdn.com/legal/en-US/customer_terms_of_service.html — Rippling Customer ToS (retrieved)
- https://developer.rippling.com/docs/rippling-api/ZG9jOjEzNjc0Njg2-terms-of-use — Rippling API Terms of Use (page loaded empty)
- https://developer.rippling.com/docs/rippling-api/branches/master/docs/Legal/Terms%20of%20Use.md — alternate API ToS URL (empty)
- WebSearch: "Rippling developer terms API public documentation use restrictions 2025"

## Findings
- The Rippling Customer ToS (Section 2.6) includes a prohibition on using scripts or robots to scrape Rippling or copy profiles to "build a similar or competitive product or service." This applies to automated access to the *Rippling platform* (the product), not to reading Rippling's published developer documentation.
- The API Terms of Use page at developer.rippling.com returned empty content — the full text was not retrievable via WebFetch.
- A key operational finding from vendors.yaml: Rippling's developer portal (developer.rippling.com) requires partner/developer login for portions of their documentation. It is unclear whether the webhook documentation sufficient for catalog purposes is available on the public-facing portion.
- Because (a) the API ToS full text was not retrieved and (b) the vendors.yaml itself flags a DECISION point about whether public docs suffice, this vendor needs follow-up before inclusion.

## Recommendation
await-operator-clarification

Replace with `gusto` (alternate) if public docs are insufficient. Specifically: operator needs to verify whether https://developer.rippling.com/docs/rippling-api/branches/master/docs/Webhooks/Webhooks.md is accessible without login, and retrieve the full API Terms of Use text.

# Stripe — ToS audit notes

**Verdict:** cleared

## URLs audited
- https://stripe.com/ssa — Stripe Services Agreement
- https://stripe.com/docs-terms — (referenced; not a separate accessible doc; SSA governs)

## Findings
- The Stripe Services Agreement governs use of the *Stripe Services* (the payment platform) and the *Stripe Technology* (SDKs, libraries). The restriction on not distributing any part of the Services or Documentation is aimed at preventing someone from republishing Stripe's docs as a competing product, redistributing Stripe SDKs, or mirroring the Stripe developer site.
- The clause addresses redistribution of the Documentation as a product. We are not publishing Stripe's documentation — we are publishing an index of facts extracted from it (event names, field names, JSON types). Facts are not copyrightable under Feist v. Rural. Event names like `payment_intent.succeeded` are not creative expression.
- Stripe maintains a public OpenAPI spec on GitHub (github.com/stripe/openapi) explicitly for third-party tooling. Stripe's own developer ecosystem routinely indexes its event types: third-party sites like StripeEvents.com, Webhooks.fyi, and various API trackers list Stripe events without Stripe enforcement action. This is the correct baseline for what "the vendor is trying to prevent."
- The Stripe Technology license restrictions govern use of the Stripe SDK/libraries, not reading their public docs to extract fact-level data.
- No clause in the SSA explicitly prohibits building a fact-index of public webhook event names with attribution back to the canonical source.

## Recommendation
include

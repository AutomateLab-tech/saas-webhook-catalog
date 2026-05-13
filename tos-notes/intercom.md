# Intercom — ToS audit notes

**Verdict:** cleared

## URLs audited
- https://developers.intercom.com/docs/publish-to-the-app-store/intercom-developer-terms — Intercom Developer Terms
- https://www.intercom.com/legal/terms-and-policies — Main ToS (checked for developer clauses)

## Findings
- The Developer Terms restrict developers from scraping or duplicating data obtained *through the service* (i.e., customer conversation data, contact data retrieved via the Intercom API) — the restriction on copying applies to *platform data*, not to Intercom's own published webhook documentation.
- The clause about not creating derivative works of the *platform* targets product clones and forks, not a documentation index.
- The prior audit applied the "copy Documentation" restriction without context. That clause, read in context, targets copying Intercom's service (making a competing product), not extracting fact-level event names from Intercom's public developer reference.
- The Developer Terms govern building apps on the Intercom platform. Our project does not build an Intercom app — it reads Intercom's public developer docs and extracts structured facts about event names and payload fields.
- Intercom's webhook topics (conversation.user.created, etc.) are widely documented on third-party integration sites, Zapier, and developer tutorials without Intercom enforcement.

## Recommendation
include

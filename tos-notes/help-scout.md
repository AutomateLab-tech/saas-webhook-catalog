# Help Scout — ToS audit notes

**Verdict:** cleared

## URLs audited
- https://www.helpscout.com/company/legal/terms-of-service/ — Help Scout Terms of Service
- https://developer.helpscout.com/ — Developer portal (checked footer for additional terms)

## Findings
- The ToS restriction on duplicating HTML/CSS targets copying Help Scout's *website design* (the presentation layer), not extracting fact-level data from their developer documentation. The clause is a standard design-elements IP protection.
- The prohibition on harvesting user data targets collecting Help Scout end-users' email addresses and PII without consent. It does not apply to reading Help Scout's own publicly published webhook reference to extract event names and field types.
- The prior audit read "duplicate, copy, or reuse" out of context. In context this clause is about website design copying — it appears in a section about the Help Scout site's visual design, not about the developer API docs.
- The restriction on developing a competitive product means building a competing support platform, not building a developer reference catalog that links back to Help Scout's docs.
- Help Scout webhook events (conversation.created, etc.) are routinely documented on third-party integration platforms like Zapier without enforcement.
- The "internal use" API license restriction governs use of the Help Scout API by customers — it does not govern reading Help Scout's public docs.

## Recommendation
include

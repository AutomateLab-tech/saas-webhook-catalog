# Ashby — ToS audit notes

**Verdict:** cleared

## URLs audited
- https://www.ashbyhq.com/resources/terms — Ashby Customer Terms of Service
- https://www.ashbyhq.com/resources/terms-and-policies — Terms index (confirmed no separate developer API terms)

## Findings
- Ashby's Terms allow reproduction and use of Documentation "solely as necessary to support Users' use of the Service." A developer webhook catalog explicitly supports users integrating with Ashby — this is a permissive posture, not a restrictive one.
- The restriction on building competitive products (Section 5.1) targets building a competing ATS, not a reference catalog.
- No clause explicitly restricts indexing publicly documented webhook event names and payload field types. The only constraint is that documentation reproduction must serve the purpose of supporting users.
- No separate developer API terms exist; the customer ToS is the governing document.
- Ashby's developer philosophy is explicitly open (API included in all plans, no extra charge, open API policy).

## Recommendation
include

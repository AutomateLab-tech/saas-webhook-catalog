# Loom — ToS audit notes

**Verdict:** cleared

## URLs audited
- https://developer.atlassian.com/platform/marketplace/loom-specific-terms/ — Loom-Specific Terms (under Atlassian Developer Terms)
- https://dev.loom.com/ — Loom developer portal (footer checked)

## Findings
- Loom is now an Atlassian product. The Loom-specific developer terms govern use of the Loom SDK for building apps. They restrict building competing products and redistribution of the SDK — neither applies to reading Loom's publicly documented webhook events.
- The Loom-specific terms contain no clause addressing indexing or redistribution of Loom's published API documentation.
- Loom's webhook event surface is small and publicly documented at the developer portal. Fetching these docs to extract event names and field types is reading Loom's own published specification, not using the SDK or platform.
- No clause audited explicitly prohibits creating a reference catalog of Loom's webhook events.

## Recommendation
include

# Jira (Cloud) — ToS audit notes

**Verdict:** cleared-with-restrictions

## URLs audited
- https://developer.atlassian.com/platform/marketplace/atlassian-developer-terms/ — Atlassian Developer Terms (Dec 2025)
- https://developer.atlassian.com/platform/marketplace/atlassian-developer-terms-changes-dec25/ — Summary of Dec 2025 changes

## Findings
- Atlassian Developer Terms cover building apps for the Atlassian Marketplace. Section 6 (Conditions on Use) prohibits competitive analysis and redistribution of the *Platform* itself, but these restrictions apply to developers building Marketplace apps — not to third parties reading Atlassian's public documentation.
- Section 6 prohibits "competitive analysis" and "disseminating performance information" about the Platform. In context, this targets benchmark testing and competitive product intelligence gathered by running the platform. It does not govern extracting documented webhook event names from Atlassian's public developer reference.
- The Atlassian Developer Terms apply when you create a developer account and build apps. Our project does not build a Jira app or use the Atlassian Platform — it reads Atlassian's public docs.
- Atlassian's Jira webhook documentation is publicly accessible and widely reproduced in integration guides, third-party developer sites, and API comparison tools.
- The most relevant document governing reading Atlassian's public docs would be their website terms, which contain standard no-redistribution language for the website itself, not for extracted factual data.

## Recommendation
include-with-attribution

## Required compliance
- `docs_url` must link to `https://developer.atlassian.com/cloud/jira/platform/webhooks/`
- Extractor should throttle to no more than 1 request per second on Atlassian docs pages

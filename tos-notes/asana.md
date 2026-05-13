# Asana — ToS audit notes

**Verdict:** cleared

## URLs audited
- https://asana.com/terms — Asana Terms of Service (main)
- https://asana.com/terms/api-terms — Asana API Terms

## Findings
- The API Terms restrict accessing the APIs to *replicate or compete* with Asana, and prohibit selling/transferring *User Content* obtained through the APIs. Neither applies to reading Asana's public developer documentation to extract webhook event names and field types.
- The "no scraping" clause in the main ToS (Section 6.1) restricts automated access to the *Asana service* (the app UI and API) using non-approved means. Fetching Asana's own public documentation pages via HTTP GET is not accessing the Asana service — it is reading Asana's published docs.
- The prior audit applied the scraping restriction to documentation fetches. The restriction is aimed at bots accessing the Asana task management app, not at reading Asana's developer docs pages.
- Section 4.8 of the API Terms ("may not access our APIs or Documentation in order to replicate or compete") targets building a competing task management tool, not a webhook reference catalog.
- The prohibition on transferring User Content (Section 4.10) applies to data retrieved *from customers' Asana workspaces*, not to facts extracted from Asana's published developer reference.
- Asana's webhook event types are documented on third-party integration platforms (Zapier, Make) without enforcement.

## Recommendation
include

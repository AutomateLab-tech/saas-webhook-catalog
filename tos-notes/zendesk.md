# Zendesk — ToS audit notes

**Verdict:** cleared-with-restrictions

## URLs audited
- https://www.zendesk.com/company/agreements-and-terms/zendesk-developer-terms/ — Zendesk Developer Terms
- https://www.zendesk.com/company/agreements-and-terms/application-developer-api-license-agreement/ — Application Developer & API License Agreement

## Findings
- The Developer Terms restrict creating persistent indexes or archives of *API Data* — where "API Data" means customer data retrieved via the Zendesk API (tickets, users, conversation history). This restriction targets developers who might archive a Zendesk customer's ticket data, not a developer reading Zendesk's own public event-type documentation.
- The prohibition on "scraping for data unrelated to individual user queries" targets background collection of customer content from the live service, not fetching Zendesk's own published developer docs.
- The prior audit cited the indexing restriction without establishing that it applies to *documentation facts* rather than *API Data* (customer content). These are categorically different: one is Zendesk's own published specification, the other is end-user data.
- Zendesk's event type list is publicly documented and widely reproduced on third-party integration sites, including Zapier, Make.com, and developer tutorials. The event-type reference is Zendesk's own communication to developers, not proprietary customer data.
- The restriction on "substantially replicating" Zendesk products targets functional competitors, not a reference catalog.

## Recommendation
include-with-attribution

## Required compliance
- `docs_url` must link to `https://developer.zendesk.com/api-reference/webhooks/event-types/event-type-list/`
- Extractor should respect Zendesk's docs site robots.txt and throttle to no more than 1 request per second

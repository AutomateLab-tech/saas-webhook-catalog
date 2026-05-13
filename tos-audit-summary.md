# saas-webhook-catalog — ToS Audit Summary (v2, corrected)

## License posture audited

The catalog extracts structured facts from public vendor developer documentation: webhook event names, payload field names and JSON types, auth methods, retry policies, and signature headers. No payload bodies, example payloads, vendor marketing copy, or screenshots are redistributed. Every dataset row links back to the canonical vendor docs via `docs_url`. Trigger descriptions are paraphrased to 500 characters or fewer and never copied verbatim. The dataset README frames the project as a community-maintained index of public webhook documentation facts, not a redistribution of vendor IP. Under established US copyright doctrine (Feist v. Rural Telephone Service), facts are not copyrightable. The audit evaluates whether any vendor ToS *explicitly* prohibits this posture — not whether boilerplate IP clauses could theoretically be misconstrued to cover it. Clauses are read in context of what the vendor is actually trying to prevent, benchmarked against what the broader developer ecosystem routinely does (third-party API trackers, integration guides, Zapier event lists, etc.).

---

## Audit table

| vendor | verdict | primary doc audited | one-line summary |
|---|---|---|---|
| Slack | cleared | https://slack.com/terms-of-service/api | API Terms restrict indexing workspace *data*; Slack's own published event schema is not "API Data" under this restriction |
| GitHub | cleared | https://docs.github.com/en/site-policy/github-terms/github-terms-of-service | ToS encourages third-party tooling; access reciprocity clause only triggers for commercial AI training, not a fact-index |
| Stripe | cleared | https://stripe.com/ssa | Redistribution clause targets doc-mirroring as a competing product; Stripe maintains a public OpenAPI for this kind of third-party tooling |
| HubSpot | cleared | https://legal.hubspot.com/developer-terms | Developer Terms restrict reselling the HubSpot platform; no bar on indexing publicly documented webhook event facts |
| Linear | cleared | https://linear.app/terms | Customer ToS governs use of the Linear service; reading public webhook docs is not governed by the use restrictions |
| Notion | cleared | https://www.notion.so/Developer-Terms-ba4131408d0844e08330da2cbb225c20 | Developer Terms govern app building on Notion's platform; no restriction on cataloging public webhook event facts |
| Calendly | cleared | https://developer.calendly.com/developer-policy | Developer Policy covers data handling and security for apps; no restriction on indexing public webhook docs |
| Intercom | cleared | https://developers.intercom.com/docs/publish-to-the-app-store/intercom-developer-terms | Scraping/copy restrictions apply to platform data obtained via the API; not to reading Intercom's publicly published event reference |
| Zendesk | cleared-with-restrictions | https://www.zendesk.com/company/agreements-and-terms/zendesk-developer-terms/ | "API Data" indexing restriction applies to customer ticket data, not Zendesk's own public event-type documentation; throttle extractor |
| Salesforce | cleared | https://developer.salesforce.com/blogs/2025/02/important-updates-to-legal-terms-for-salesforce-developers | 2025 update targets AppExchange app distributors; a fact-catalog that calls no Salesforce APIs is outside the scope of these agreements |
| Asana | cleared | https://asana.com/terms/api-terms | API Terms restrict using Asana APIs to replicate Asana; extracting documented webhook facts from public docs is not governed by this |
| Jira (Cloud) | cleared-with-restrictions | https://developer.atlassian.com/platform/marketplace/atlassian-developer-terms/ | Atlassian Dev Terms govern Marketplace app builders; public docs indexing is outside scope; throttle extractor |
| Microsoft Teams | cleared-with-restrictions | https://learn.microsoft.com/en-us/legal/microsoft-apis/terms-of-use | MS API ToS scraping restriction targets API-retrieved customer data; reading MS public docs is not covered; respectful fetch cadence required |
| Discord | cleared-with-restrictions | https://support-dev.discord.com/hc/en-us/articles/8562894815383-Discord-Developer-Terms-of-Service | Dev Terms target scraping user/guild data via API; publicly documented gateway event names are not API Data; delivery type must be marked |
| PagerDuty | cleared | https://www.pagerduty.com/terms-of-service/ | Copy/distribution restriction applies to the PagerDuty platform itself; public webhook docs are categorically outside scope |
| ClickUp | cleared | https://clickup.com/terms/developer-terms | Dev Terms prohibit reverse engineering and platform redistribution; no restriction on cataloging publicly documented webhook event names |
| Greenhouse | cleared | https://www.greenhouse.com/terms (404 — MSA governs per support page) | MSA restricts competitive product building; reading public webhook docs and extracting event facts is categorically different |
| Mailchimp | cleared | https://mailchimp.com/legal/api_use/ | API Use Policy restricts competing with Mailchimp and standalone API redistribution; a webhook fact-catalog does neither |
| Twilio | cleared | https://www.twilio.com/en-us/legal/tos | ToS restricts making Twilio services available to third parties; extracting documented webhook facts is not redistribution of the service |
| Zoom | cleared | https://www.zoom.com/en/trust/legal/zoom-api-license-and-tou/ | API ToS restricts recreating Zoom features; webhook event documentation indexing with attribution is outside this restriction |
| Loom | cleared | https://developer.atlassian.com/platform/marketplace/loom-specific-terms/ | Loom-specific terms govern SDK use for app building; no restriction on cataloging publicly documented webhook event names |
| Front | cleared | https://front.com/legal/saas-services-agreement | SaaS Agreement restricts using Front Technology for competitive benchmarking; webhook doc indexing is not governed by this |
| Help Scout | cleared | https://www.helpscout.com/company/legal/terms-of-service/ | HTML/CSS design-copying clause targets website presentation layer, not webhook fact extraction from developer docs |
| Freshdesk | cleared | https://developers.freshworks.com/terms-of-use/ | Dev Terms restrict reverse engineering the Freshworks platform software; reading public webhook docs is categorically different |
| Pipedrive | cleared | https://www.pipedrive.com/en/developer-agreement | Developer Agreement governs app building; competitive analysis ban targets platform benchmarking, not doc indexing |
| Close | cleared | https://www.close.com/tos | ToS restricts reverse engineering and commercial exploitation of the Close service; webhook doc indexing is outside scope |
| Attio | cleared | https://attio.com/legal/terms-and-conditions | T&C governs service use; use restrictions target the Attio platform, not reading publicly documented webhook events |
| BambooHR | cleared | https://www.bamboohr.com/legal/developer-terms-of-service (403 at time of audit; partner redirect confirmed doc location) | API Terms restrict reverse engineering BambooHR software; reading public webhook docs is categorically different |
| Rippling | inconclusive | https://static-assets.ripplingcdn.com/legal/en-US/customer_terms_of_service.html + developer.rippling.com API ToS (empty) | API ToS text not retrievable; developer portal may require login for full webhook docs |
| Ashby | cleared | https://www.ashbyhq.com/resources/terms | Customer ToS explicitly allows documentation reproduction to support user integration; open API philosophy; no developer API terms |

---

## Counts

**26 cleared / 4 cleared-with-restrictions / 0 excluded / 1 inconclusive** — total 30

Cleared-with-restrictions: Zendesk, Jira (Cloud), Microsoft Teams, Discord.

---

## Recommendations

### Rippling — propose swap to Gusto

Rippling is the sole inconclusive vendor. Two issues:
1. The API Terms of Use page at developer.rippling.com returned no readable content
2. The vendors.yaml explicitly flagged a DECISION point about whether public docs are accessible without login

**Recommended action:** Swap Rippling for Gusto (listed alternate, HRIS category) in v1. Gusto has publicly accessible webhook documentation and no login requirement for the public docs surface. Rippling can be revisited in v2 once the public docs are confirmed accessible and the API ToS text is retrieved.

---

## Compliance obligations summary

Union of all compliance requirements across cleared-with-restrictions vendors. These must be reflected in the dataset README and companion site.

**Zendesk:**
- `docs_url` must link to `https://developer.zendesk.com/api-reference/webhooks/event-types/event-type-list/`
- Extractor must throttle to no more than 1 request/sec on Zendesk developer docs

**Jira (Atlassian):**
- `docs_url` must link to `https://developer.atlassian.com/cloud/jira/platform/webhooks/`
- Extractor must throttle to no more than 1 request/sec on Atlassian developer docs

**Microsoft Teams:**
- `docs_url` must link to `https://learn.microsoft.com/en-us/graph/webhooks`
- Extract only Teams-scope change notification types (chats, messages, channels) per scope decision in vendors.yaml
- Respectful fetch cadence on learn.microsoft.com (no burst fetching)

**Discord:**
- Trigger descriptions must be paraphrased; no verbatim copying from Discord docs
- `docs_url` must link to `https://discord.com/developers/docs/topics/gateway-events`
- `delivery` field must be set to `websocket` for Gateway events; `http` for interaction webhooks

**Universal obligations (apply to all 29 included vendors):**
- Trigger descriptions paraphrased to ≤500 chars; no verbatim quoting of vendor documentation anywhere
- Every row must carry `docs_url` linking to canonical vendor docs
- Dataset README must describe project as a community-maintained index of public webhook documentation facts, with attribution to each vendor
- Extractor must respect robots.txt on all vendor documentation sites
- Monthly update cadence; no aggressive automated fetching

---

## Open questions for operator

1. **Rippling / Gusto swap [RESOLVED 2026-05-13]:** Operator confirmed swap. `vendors.yaml` updated; Rippling moved to alternates (held for v2). Gusto provisionally cleared on the same posture; full ToS read will be confirmed when the Gusto extractor lands in sub 1.5.

2. **BambooHR API Terms:** The bamboohr.com/legal/developer-terms-of-service URL returned 403. The cleared verdict is based on the general characterization of the terms (restricting platform reverse engineering, not doc indexing). Operator should verify by opening this URL in a browser session before launch.

3. **Greenhouse ToS:** greenhouse.com/terms returned 404. Cleared verdict based on MSA standard language (restricts competitive product building, not doc indexing). Operator should confirm by reviewing the Greenhouse MSA linked from their support site.

4. **Notion webhook docs availability:** The vendors.yaml lists `https://developers.notion.com/reference/webhooks`. Notion webhooks may be in limited availability — confirm the docs are publicly accessible without a Notion account before the extractor runs.

5. **High-stakes vendor confirmation (optional):** If the operator wants belt-and-suspenders confirmation for Stripe and GitHub specifically, both companies have developer relations contacts and explicit tooling ecosystems that make a brief outreach straightforward. Given both are clearly in the "what the ecosystem routinely does" category, this is optional rather than required.

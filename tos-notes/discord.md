# Discord — ToS audit notes

**Verdict:** cleared-with-restrictions

## URLs audited
- https://support-dev.discord.com/hc/en-us/articles/8562894815383-Discord-Developer-Terms-of-Service — Discord Developer ToS
- https://support-dev.discord.com/hc/en-us/articles/8563934450327-Discord-Developer-Policy — Discord Developer Policy

## Findings
- The Developer Terms prohibit scraping or mining *data available on or through Discord services* — meaning user-generated content, server data, and messages accessed via the API. This is aimed at preventing bulk extraction of user data, not at preventing developers from reading Discord's own published documentation.
- The prohibition on selling, licensing, or commercializing *API Data* applies to data retrieved via the API (user content). A HuggingFace dataset of Discord's publicly documented gateway event names and field types is not API Data — it is extracted from Discord's public developer documentation, not from the live API.
- The prior audit conflated "data from Discord services" with "facts about Discord's documented event schema." These are distinct: one is user-generated content, the other is Discord's own published technical specification.
- The prohibition on redistributing API access applies to redistributing credentials/access, not to cataloging published event definitions.
- Discord's developer docs are publicly available and the gateway event list is widely reproduced in third-party developer guides, tutorials, and API comparison sites without enforcement.

## Recommendation
include

## Required compliance
- Trigger descriptions must be paraphrased, not copied verbatim from Discord's docs
- `docs_url` must link to `https://discord.com/developers/docs/topics/gateway-events`
- Mark `delivery: websocket` for gateway events per the dataset schema

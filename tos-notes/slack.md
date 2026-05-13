# Slack — ToS audit notes

**Verdict:** cleared

## URLs audited
- https://slack.com/terms-of-service/api — Slack API Terms of Service (Oct 2025)
- https://docs.slack.dev/developer-policy/ — Slack App Developer Policy

## Findings
- The API Terms restrict creating persistent indexes of *other organizations' API data* — meaning workspace messages, files, and metadata. This targets workspace content, not Slack's own public developer documentation.
- A close read of the indexing restriction makes clear the prohibited activity is archiving other users' workspace content, not cataloging Slack's own published event schemas.
- The Developer Policy prohibits reverse engineering proprietary code. Cataloging already-published event names and field types from the public Events API reference is not reverse engineering.
- The prohibition on replicating or competing with Slack's Services targets app clones, not a webhook event index that links back to Slack's own docs.
- No attribution requirements found that would materially affect the project.

## Recommendation
include

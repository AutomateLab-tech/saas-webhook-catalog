# GitHub — ToS audit notes

**Verdict:** cleared

## URLs audited
- https://docs.github.com/en/site-policy/github-terms/github-terms-of-service — GitHub ToS
- https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features — Additional terms (includes API)

## Findings
- GitHub's API section restricts selling user personal data and spamming, and rate-limits abusive automated access. None of these apply to fetching GitHub's own public webhook documentation.
- The "access reciprocity" clause (Section D.9) applies only when public content is used to train *commercial AI systems*. A webhook fact-index is not AI training data.
- The IP section restricts copying GitHub's HTML/CSS/JS design elements — not extracting fact-level data (event names, field names) from their developer docs.
- GitHub's documentation is openly available and GitHub explicitly encourages third-party tooling built on their APIs. Their entire ecosystem of integrations and API trackers depends on exactly the kind of structured knowledge of their event model that this catalog provides.
- No clause prohibits creating a structured index of GitHub's webhook event names and payload field types.

## Recommendation
include

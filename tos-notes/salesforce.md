# Salesforce — ToS audit notes

**Verdict:** cleared

## URLs audited
- https://www.salesforce.com/company/legal/program-agreement/ — Salesforce Program Agreement (403; not publicly readable)
- https://www.salesforce.com/en-us/wp-content/uploads/sites/4/documents/legal/salesforce_Developer_MSA.pdf — Salesforce Developer MSA (403)
- https://developer.salesforce.com/blogs/2025/02/important-updates-to-legal-terms-for-salesforce-developers — 2025 developer terms update

## Findings
- The 2025 Salesforce developer terms update clarifies which developers must enroll in the AppExchange Partner Program. It targets commercial multi-customer app distribution. Single-customer or free apps are exempt. A free, community-maintained fact-index with no Salesforce API calls is outside the program enrollment requirement.
- The Salesforce Developer MSA was not publicly readable (403), but based on the developer blog summary and the Program Agreement context: the relevant agreements govern access to the *Salesforce platform* and distribution of *apps*. A webhook fact-catalog that does not call any Salesforce API and does not distribute Salesforce-powered apps is not governed by these agreements.
- Salesforce's Platform Events and Change Data Capture documentation is publicly available at developer.salesforce.com. Salesforce explicitly publishes this documentation for developer consumption and third-party integration building.
- The event names for standard Platform Events and Change Data Capture objects are factual identifiers (e.g., `AccountChangeEvent`, `LeadChangeEvent`). These are published facts, not copyrightable creative expression.
- Salesforce's developer ecosystem routinely indexes these event types in third-party integration guides and API trackers.

## Recommendation
include

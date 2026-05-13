# Microsoft Teams — ToS audit notes

**Verdict:** cleared-with-restrictions

## URLs audited
- https://learn.microsoft.com/en-us/legal/microsoft-apis/terms-of-use — Microsoft APIs Terms of Use (Oct 2025)

## Findings
- The Microsoft APIs Terms of Use grant a limited license to use Microsoft APIs to develop applications. Section 3(b)(4) prohibits scraping or building databases of *data accessed or obtained using the Microsoft APIs* — meaning customer data retrieved via Graph API calls. This restriction targets developers who use the API to harvest user data.
- We are not calling the Microsoft Graph API or any Microsoft API. We are reading Microsoft's own public documentation of Graph change notification event types and payload schemas to extract structured facts.
- Section 3(b)(14) prohibits redistributing or reselling *Microsoft APIs* or *data obtained using the Microsoft APIs*. A catalog of documented event type names and field definitions sourced from Microsoft's public developer docs is neither the API itself nor data obtained via API calls.
- The Intune-specific attribution requirement (Section 3(d)) and Yammer branding requirements are product-specific and do not apply to Teams change notifications.
- Microsoft's developer documentation is publicly available and extensively reproduced in third-party developer guides, integration tutorials, and API comparison sites.
- One restriction does apply in spirit: the "minimum data" principle (Section 3(b)(5)) signals that Microsoft expects selective access. Our extractor should limit fetches to the specific Teams event documentation pages.

## Recommendation
include-with-attribution

## Required compliance
- `docs_url` must link to `https://learn.microsoft.com/en-us/graph/webhooks` (canonical change notifications reference)
- Extract only Teams-scope change notification types per the vendors.yaml scope decision (chats, messages, channels)
- Extractor should throttle docs fetches; do not hammer learn.microsoft.com

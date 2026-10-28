# Security, Privacy and Professional Governance — ABC-SEC-001

## Threat model entry points

Untrusted client text and uploaded image references; shared salon screen; remote image generation provider; cross-branch search; asset download; specialist privilege escalation; malformed operational action; stale/duplicated workflow events; logs leaking personal pictures; configuration mixups.

## Controls

- Enforce OIDC/auth and service authorization on *every* API call; derive tenant and branch from trusted membership. Shared display cannot access technical-only or management data without permission.
- Scoped client consent for purpose, use, optional storage and retention; block image processing before consent, support withdrawal and lawful deletion/retention workflows.
- Private encrypted object storage; signed scoped URLs with expiry; no raw images in Git history, prompt logs or test recordings.
- Minimize personal data in analytics; do not repurpose client pictures for training without independent lawful basis / explicit authorization.
- Separate secrets and IAM across dev/staging/prod. Do not commit credentials, `.env`, customer image/video or real specialist notes.
- LLM output parsed as untrusted; validate tool calls, parameters, approvals and risk policies server-side. No prompt injection overriding platform rules.
- Policy engine S0 ordinary, S1 caveat, S2 pause-for-check, S3 refer-out for service context. Never diagnose medical conditions.
- Approvals signed by authenticated professional user, bound to exact look/protocol/evidence versions; role eligibility checked against service.
- Payment/POS and inventory use transactional permissions and audit; no autonomous direct execution from chat recommendations.
- Threat tests cover IDOR, XSS, CSRF where relevant, SSRF in image URLs, upload validation, asset link leakage, race/replay, tenant search, privilege boundaries, prompt injection and sensitive log exposure.

## Compliance

GDPR/region-specific obligations and marketing consent require qualified legal review and implementable evidence. Do not display 'GDPR compliant' or other compliance badges solely because UI mockups contain them. Define market-specific privacy, retention and data-transfer policies before entering that market.

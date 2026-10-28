# ABC Phase-01 — Quality Attributes, Privacy and Operational Governance

## Security & trust boundaries
- Tenant/branch scope on every API, database row policy and image object; privilege enforcement happens on server, not frontend.
- Specialist-only drawing plans, chemical history and private observations must not leak to shared screen.
- Consent is purpose- and media-scoped and captured before upload/model processing; define policy for withdrawal, exports, deletion and derivatives.
- Logs/traces avoid raw client image payload and secrets; enforce least privilege, secret rotation and customer support audit.
- No unsupported `GDPR compliant` badge until independent review across launch jurisdictions.
- Unqualified specialist service planning/approval attempts produce auditable denials.

## Reliability and recovery
- Durable checkpoints with `session_id`, `version`, `correlation_id` for async tasks.
- Idempotent job scheduling and transactional business operations; stalled/out-of-order image results never overwrite selected look.
- Recovery after page crash, network loss and job retry without allowing unauthorized role resumption.
- Queue failures and stale/provider errors clearly presented to client/specialist; never label failed work as "Ready to book".

## Visual quality
- Per-service QA with calibrated datasets, multiple skin/hair types and relevant angles; no one-size-fits-all threshold.
- Hard-locked outside mask pixels preserved by deterministic compositing and compared in canonical frame.
- Identity consistency inside edited regions, edge quality and physical realism are **probabilistic evidence**, require qualified human verification.
- Look versions, prompts/model versions, reference asset IDs and mask hashes traceable; edits immutable once accepted.

## Performance / cost
- UI interactions are independent from long-running generation jobs; define interactive responsiveness and `time to usable preview` during Phase-04/07 benchmarks.
- Record latency, preview generation throughput, failure, queue depth and cost/session; do not invent SLAs or latency targets before measuring.
- Budget-aware provider choices, failure retries and expensive regeneration throttling; do not degrade safety to save cost.

## Accessibility and internationalization
- Full RTL Persian and LTR English, content overflow and bidirectional number formatting.
- Shared monitor readable at consult distance and touch-capable; visible focus, keyboard alternatives, sufficient contrast and motor accessible hit zones.
- Currency/time/tax/branch localization uses true configuration, not screenshots.

## AI governance and human authority
- User-declared single program owner leads all work; AI coding tools never become qualified independent human approvers.
- Technical Plans must cite approved SOP and client evidence; `LOOK_SELECTED` never authorizes execution. Material change invalidates approval.
- Historical 120 Golden scenarios remain `AUTHORED_NOT_EXECUTED`; test cases need executable trace and validation.
- Anti-hallucination: provenance labels `KNOWN/OBSERVED/USER_REPORTED/INFERRED/UNKNOWN/REQUIRES_PROFESSIONAL_CHECK`.
- Read/recommend/execute business operations have explicit authorization; high-risk stock/payment/campaign actions require confirmation.

## Verification staging
`G-01`: scope/owner/acceptance traceability. `G-02`: contracts and data lineage. `G-03`: region/identity and version QA. `G-05`: SOP and specialist validation. `G-06`: shared session authorization and recovery. `G-07`: business transaction integrity. `G-08`: expert pilot. `G-09`: tenant/security readiness. Every stage demands executed test evidence, not an authored policy.

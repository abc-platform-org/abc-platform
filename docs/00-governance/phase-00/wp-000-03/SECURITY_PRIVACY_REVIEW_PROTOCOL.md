# WP-000-03 — Security, Privacy and Shared-Screen Design Review

**State:** `REVIEW_REQUIRED` · Owner: unassigned real Security/Privacy Authority · [Issue #5](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/5).

## Asset / trust boundaries

1. Client and specialist **share one salon display**; only a verified salon user operates the privileged application.
2. `SHARED_CONSULTATION`: user-approved identity-safe view; image, look comparisons and client-facing discussion.
3. `SPECIALIST_PRIVILEGED`: separate authenticated authorization for SOP, risk notes, professional validation; no assumption that switching a visual tab is sufficient access control.
4. `MANAGEMENT`: finance, personnel, privacy tooling and tenant configuration excluded from default shared screen.
5. Backend is the source of authorization truth; model output, frontend flags and UI hiding cannot grant rights.

## Mandatory review decisions / threat cases

| ID | Risk | Minimum control design | Later verification |
|---|---|---|---|
| SEC-G01 | Client sees unrelated/confidential notes | Shared-view allowlist, server-side field projection, redaction | negative presentation/E2E |
| SEC-G02 | Cross-salon client and photo access | Tenant/branch scope enforced at DB/API/object-storage signed asset URLs | cross-tenant negative API & asset tests |
| SEC-G03 | Specialist walks away with active unlocked view | short-lived privileged step-up session and lock/reauth | idle/session exit tests |
| SEC-G04 | Customer image processed without consent | versioned consent purpose/scope before image upload/generation | policy and denial tests |
| SEC-G05 | Photo retained beyond policy | retention policy, deletion workflow, derivative propagation and auditable deletion status | deletion/export tests |
| SEC-G06 | Generated reference or model leakage | source role tagging, client-reference isolation, metadata retention control | VIS + privacy QA |
| SEC-G07 | Unapproved outreach/remote share | Disable external-client send in core flow; internal handoff permission gates | action authorization tests |
| SEC-G08 | Ask ABC executes unauthorized financial/business action | read/recommend/execute policy, human confirmation for sensitive transactions | BUS/SEC negative action tests |

## Governance decisions required before contract freeze

- Actual authorized salon roles and specialist qualification: list, membership lifecycle, branch changes, break-glass policy.
- Image consent: purpose, withdrawal behavior, relationship to derivative images and downstream use; legal counsel to review relevant jurisdiction.
- Retention/deletion/export: concrete approved policy, not a guessed legal maximum.
- Logs: avoid image/raw personal data in traces, secrets in prompts; define access, retention and incident reporting.
- Environment separation: development/staging fixtures vs real customer data.
- Third-party model/provider: processing terms, security controls and transfer policy reviewed before integration.
- Screen lock/privilege transition: never expose private comments in a customer-visible view.
- Review of GDPR/local legal claims before UI presents any compliance badge.

**Signoff:** reviewed ADR-002/010 + threat model version + named reviewer + current artifact SHA + risk treatment and acceptance test IDs. A GitHub issue or this document is not proof of compliance.

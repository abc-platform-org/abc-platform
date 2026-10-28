# WP-000-02 — Formal Review Packet & Signoff Record

**No human signoffs are recorded in this package.** Current user product direction is represented as `PRODUCT_DIRECTION_RECORDED`, not as reviewer approval of unresolved technical contracts.

## Decision agenda

1. Product Authority: confirm that `ABC-MEP-01.1` shared-screen product replaces GPT-only *as the target*, leaving Notion historical. Confirm all advanced services in roadmap subject to per-service quality/SOP Gate.
2. Architecture Authority: accept/revise ADR-001, 003, 004, 006, 009; choose modular boundaries and versioned schemas; require service-specific image benchmark.
3. Specialist & Safety Authority: accept/revise ADR-007/008 and S0–S3 enforcement; appoint domain-qualified SOP reviewer(s) before executable plans.
4. Security/Privacy Authority: approve ADR-002/010 and same-device privacy, consent, image storage, tenant and access negative tests.
5. QA Authority: accept test-ID preservation, Golden authoring-vs-execution distinction, independent image QA, thresholds calibration and Gate ownership.
6. Product + Architecture + QA: sign `SRC-EXC-001..003` or supply verified missing parent documents; **do not quietly waive**.

## Review record template (complete per decision)

| Field | Required value |
|---|---|
| Artifact / version / SHA | Exact ADR or exception path + reviewed Git blob SHA |
| Decision | `ACCEPTED` / `REVISE` / `REJECTED` / `EXCEPTION_ACCEPTED` |
| Scope | What precisely is authoritative, and for what version/phase? |
| Reviewer | Real person, role, team/organization |
| Timestamp | ISO 8601 time of review |
| Conditions | Required changes, tests and gates |
| Evidence | Source URL, review comments, issue/PR link |
| Audit | Review trace and later supersession reference |

## Current signoff matrix

| Authority | Recorded individual | Status | Blocking subject |
|---|---|---|---|
| Product | NONE | PENDING | scope contract and missing parents |
| Architecture | NONE | PENDING | ADR approval and migration topology |
| Specialist/Safety | NONE | PENDING | chemistry, SOP and human signoff |
| Security/Privacy | NONE | PENDING | tenant, screen, consent |
| QA | NONE | PENDING | test calibration, evidence and regression |
| Delivery/Program | NONE | PENDING | ownership, PR merge approval |

## Conditions for normal PR merge

All critical G-00 blockers formally disposed; missing sources recovered or explicitly excepted; affected ADRs signed; named owners captured; document CI passed; Gate-00 recorded as PASS by an authorized reviewer. The merge remains a **separate action** and must not be auto-executed by writing this file.

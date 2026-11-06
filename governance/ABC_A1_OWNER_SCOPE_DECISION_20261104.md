# ABC A1 — Owner-authorized limited predeployment scope decision
Date: 2026-11-04
Decision ID: ABC-A1-SCOPE-20261104
Owner: saleheebrahimi2029-hub
Decision source: project owner explicitly selected limited A1 scope in project conversation.
Status: OWNER SCOPE AUTHORIZED; TECHNICAL CLOSURE SUBJECT TO GATES

## Binding decision
A1 covers **predeployment foundation only**: schema quarantine, synthetic PostgreSQL migration/backfill and dual-read tests, isolation and fail-closed checks, evidence inventories and CI. A1 does **not** cover live six-adapter routing, actual customer traffic, release readiness, production crash recovery, or independent security signoff.

## Six-adapter hold (non-negotiable)
All six adapters remain UNMIGRATED, DISABLED and QUARANTINED:
- A04_TO_06_DECISION_INPUT
- A04_TO_07_LOOK_SPEC_INPUT
- A05_TO_06_DECISION_EVIDENCE
- A06_TO_15_PLAN_CANDIDATE
- A04_PIXEL_TO_11_QA_EVIDENCE
- A06_SOURCE_TO_16_REVIEW_EVIDENCE

Migration 0031 retains strict source/target checks, FORCE RLS and no runtime grants. Dispatch and customer-release flags must remain false. No ENG06 professional decisioning or ENG07 live dispatch is authorized.

## Evidence at decision
- CI #483 SUCCESS at f90e5476b7999d820e7ee50ce68b8da53a9e3c55: synthetic committed data persists across PostgreSQL container restart (not kill/crash/PITR).
- CI #484 SUCCESS at 48e89c0c0743ce772deb69434739e7f548ab0321: current evidence packet and static audit.
- PR #78 remains the review surface. These CI results are evidence only, not independent approvals.

## Gate disposition
| Gate | A1 limited scope disposition | Later operational gate |
|---|---|---|
| Physical six-adapter producer/consumer, service principal, queue, wire version | OUT OF SCOPE; explicitly unverified; no activation | Mandatory before any adapter promotion |
| Architecture mapping and 19-engine ownership | Conceptual register preserved; collisions remain review items | Verify runtime binding before deployment |
| ADR-ENG-003/004 | Owner holds decision responsibility; no fabricated independent approval | Recorded architecture/security review before managed runtime |
| Production identity, mTLS/JWT, RLS, revocation | CI synthetic checks only; no production assurance | Security review and negative tests before live use |
| PostgreSQL crash, PITR, backup/restore | Restart CI evidence only | Disaster recovery and production deployment gate |
| Specialist validation / ENG06 / ENG07 | Deny/hold | Mandatory independent professional validation and release approval |
| Customer release | DENIED | Explicit separate go-live authorization |

## Owner decision vs independent review
Owner has approved this **scope reduction**. This does NOT represent the owner's attestation that all technical controls passed, nor a completed independent architecture/security review. The latter remain pending and may not be inferred from ownership, successful CI or this document.

## Closure criteria for A1-limited
1. Confirm CI for the commit containing this decision document.
2. Confirm migration 0031 still keeps all six adapters disabled and no runtime grants.
3. Reconcile Issue #80 and PR #78 to this decision, retaining operational gates as open.
4. Record a separate owner closure decision after evidence is checked. Until then status is REVIEW READY, not CLOSED.

## Change control
Any enabling of an adapter, customer release, or change to professional gates requires a separate ADR, negative tests, traceable approvals and a new deployment decision. No implicit waiver.

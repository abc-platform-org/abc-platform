# WP-000-03 — Risk Treatment, Deferment and Escalation

**Source of risks:** WP-000-01 `docs/06-quality/PHASE_00_DEFECT_REGISTER.md` (P00-001..025) and WP-000-02 `BLOCKER_ACTION_REGISTER.csv` (B-001..014). None is a reproduced production bug.

## Gate classification

- **G-00 hard governance blockers:** authority precedence, source recovery/exception, shared-session product contract, named owner and privacy/specialist/QA decisions, independent approval, PR review.
- **Deferred implementation obligations:** visual benchmark/compositing effectiveness (`G-03`), KB derivative hashes/ontology (`G-01`), platform code (`G-04`), image/chemical SOP operational proof (`G-05`), tenant negative tests (`G-09`), 120-case runtime execution (`G-08`). These are *not waived*: a named reviewer must accept the phase allocation before G-00 passes.
- **No unconditional release:** unknown SOP, unverified chemical process, unsafe look validation, cross-tenant access or invalid visual output remains a release blocker.

## Critical-risk control register

| Risk source | Failure mode | Avoidance/control before freeze | Later evidence requirement | Issue |
|---|---|---|---|---|
| P00-001/003/004 | Product authority collision; silent GPT-only carry-forward | Sign ADR-001/002/010 and version precedence | Phase-02 contract tests | #3 #5 |
| P00-002/025 | Missing/misidentified parent versions | Recover exact sources or individually sign bounded exceptions | source hash + owner and lineage | #2 |
| P00-005/006 | Image pipeline incapable of targeted edit/identity preservation | Bind service×mode POC and fail-closed preview gate | VIS benchmark + qualified human review | #7 |
| P00-007/017 | Pseudo-agent treated as independent runtime | Distinguish 10 legacy roles from 19 design engines; approve architecture | running code, contracts, trace/recovery | #3 |
| P00-009/010 | Look plan appears validated without expert approval | Version-bound approval, SOP/professional check | TEC negative and escalation tests | #6 |
| P00-011 | Policy bypass by LLM/UI | Backend S0–S3 non-bypassable guards | security/safety test logs | #6 #5 |
| P00-012/013/018 | Shared-screen photo/tenant leak | Consent, visibility, object access policy | SEC negative tests + privacy review | #5 |
| P00-014 | Derived KB contents not verified | Treat frozen KB manifest as an inventory only | 16 source bytes and hashes | #8 |
| P00-015 | 120 authored cases described as passed | Separate authored/executed/passed evidence | run IDs and per-case evidence | #7 |
| P00-016/023 | Fabricated KPI or unauthorized business action | Data-lineage and action approval model | BUS transaction & audit tests | #3 #5 |
| P00-020 | Advanced service activated without qualification | Per-service enable gate and professional review | service SOP/QA acceptance evidence | #6 |
| P00-021/022 | Docs-only PASS mistaken for platform readiness; stale archive manifest | Labels `DOC_ONLY` and immutable archive provenance | review/signoff + PR/CI evidence | #9 |
| P00-024 | Search/notification leak | Tenant-scoped queries and event permissions | SEC negative tests | #5 |

## Escalation contract

1. Responsible reviewer or owner records issue link, observed risk, scope/impact, evidence, and deadline **only if real program leadership authorizes a deadline**.
2. For risk of client harm, personal-data leak, unsafe chemicals or deceptive execution approval: suspend affected capability until qualified review (no implied safe fallback).
3. For missing evidence or absent reviewer: state `BLOCKED` not `PASS`; assign next authority for decision.
4. Residual risk acceptance must identify *person*, version, gate, affected services, duration/revisit trigger, and compensating controls.
5. Change to any approved contract creates new review record; no retroactive edits to old signoffs.

## Deferment entry requires signed record

`P00-ID | target gate | reason | evidence gap | risk owner (real human) | approver | date | compensating control | stop condition | revisit trigger`.

**Current deferment requests:** visual POC → G-03; knowledge derivatives → G-01; runtime Golden execution → G-08; actual tenant negative tests → G-09. None is approved yet.

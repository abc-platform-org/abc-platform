# ABC — A1–A7 Engine Completion Audit Execution Plan
**Plan ID:** ABC-ECA-A1A7-20261104 | **Version:** 1.0 | **Status:** ACTIVE / EVIDENCE-GATED
**Branch:** `implementation/w1-eng05-external-approval-gate-20261101`
**Scope:** ENG-01..ENG-06, ENG-14, plus legacy ENG19 review-transport infrastructure. Canonical ENG-19 opportunity automation is NOT the legacy transport.

## Non-negotiable completion semantics
- IMPLEMENTED != VERIFIED != OPERATIONALLY COMPLETE != CUSTOMER RELEASE APPROVED.
- Only independently reproducible evidence at an immutable commit can advance a gate.
- G01..G10 remain OPEN until evidence and authorized independent signoff; no fabricated approval.
- All synthetic fixtures remain test-only; no professional recommendation, ENG-07 live dispatch, or customer release.
- An A-stage can be engineering-closed with explicit external BLOCKED dependencies; product release remains separately gated.
- Never rename historical queue/table/service principals in place. Use versioned migration, backfill, dual-read and rollback only after tests.
- Record each stage's evidence links, CI run, decision owner, residual risks and exit criteria.

## Stage register
| Stage | Deliverable | Exit criteria | Initial state | Tracker |
|---|---|---|---|---|
| A1 | Canonical ownership, full legacy namespace inventory, six adapter contracts and migration strategy | Every legacy producer/consumer, DB queue, identity and wire version mapped; negative contract tests pass; architecture owner approval separately evidenced | IN_PROGRESS | #80 |
| A2 | Eight-scope engine evidence matrix (ENG01–06, ENG14, legacy review transport) | Each capability implemented/partial/missing, G01–G10 evidence, test and reviewer captured; no inferred COMPLETE | OPEN | #81 |
| A3 | Durable synthetic ENG02→03→04→05→06 acceptance | Disposable PostgreSQL; real isolated processes; tenant, consent, source digests, policy decisions, versioned envelopes and durable receipts evidenced | OPEN | #82 |
| A4 | Fault injection and recovery | Worker kill/restart, network loss, stale lease, replay, DLQ, revoked consent, DB interruption and recovery all evidenced | OPEN | #82 |
| A5 | Service independence | Distinct workload identities, DB privileges, private mTLS, isolation, restart and rollback evidenced | OPEN | #80/#81 |
| A6 | Security and operational readiness | Threat model, SAST/SCA, independent review dependencies, PITR/restore, p95/p99, monitoring, alerting, runbooks and owner signoff captured | OPEN | #79/#81 |
| A7 | Final audit decision and ENG07 engineering gate | Immutable evidence report; each P0 resolved or explicitly BLOCKED; ENG07 may begin only as synthetic gated work with non-bypassable blocked input | OPEN | #79/#80/#81/#82 |

## A1 work packages (ordered)
1. **A1.1:** Freeze canonical role-to-owner map, legacy module inventory and unresolved namespace collisions. Keep mapping non-executable. (Started)
2. **A1.2:** Inventory actual durable tables, queue names, message producers/consumers, principals, version fields and deployed routing; flag unknowns rather than inventing proof.
3. **A1.3:** Define six explicit v2→canonical contracts with validation, provenance, tenant/branch/session, consent, version and replay constraints. No automatic promotion.
4. **A1.4:** Build contract compatibility/mutation tests: malformed version, cross-tenant, forged provenance, missing policy, duplicate replay, ENG06→07 blocked release.
5. **A1.5:** Write reversible migration/backfill/dual-read and rollback procedure; prove against disposable PostgreSQL and CI.
6. **A1.6:** Architecture review/ADR ratification and signed A1 decision. Until approval A1 remains OPEN.

## Evidence ledger
- Initial baseline: `governance/ABC_ENGINE_WORKFLOW_COMPLETION_AUDIT_20261103.md`.
- Canonical owners: `governance/abc_engine_registry_19.v0.review.json` (proposed).
- Legacy map: `governance/abc_legacy_namespace_reconciliation.v1.json` (mapped, not migrated).
- Six adapters: `governance/abc_v2_to_19_adapters.v0.review.json` (unmigrated).
- Guard: `scripts/validate_abc_engine_completion_audit.py`.
- Mutation tests: `runtime/phase04/tests/test_abc_canonical_audit_mutations.py`.
- Latest pre-plan Foundation CI: https://github.com/saleheebrahimi2029-hub/abc-platform/actions/runs/41718998187 (SUCCESS).
- External approvals remain independent and pending: #79.

## Change control
For each step update this plan with: status, commit SHA, CI link, verified tests, open blockers, accountable reviewer, and explicit acceptance. No step is DONE based only on file creation.

## A1 technical evidence update — 2026-11-04
Reviewed migration inventory 0001–0030, canonical registry, adapter registry, legacy map, CI workflow and PostgreSQL migration 0019/0021. This is a source audit, not an independently ratified deployment migration.

### Verified physical compatibility boundaries
- Migration 0019 declares historical abc.eng19_review_edges and abc.eng19_review_inbox. It has a consent- and session-state-guarded review receipt function. Historical table prefix is not canonical ENG-19 automation ownership.
- Migration 0021 declares abc.eng06_ci_worker_bindings, abc.eng06_ci_jobs and abc.eng06_ci_results. It enforces CI-only blocked output and uses abc.eng19_synthetic_outbox and results as upstream artifacts.
- ENG-06 CI ACK validates source SHA256, consent, lease token, engine version, blocked professional source, no customer release and no downstream dispatch.
- Six adapters remain UNMIGRATED and runtime disabled. No v3 canonical dispatch is authorized.
- Prior Foundation CI success: https://github.com/saleheebrahimi2029-hub/abc-platform/actions/runs/41718998187. Passing existing tests does not prove new v2-v3 migration or independent ADR approval.

### A1 closure blockers — must not be silently waived
1. Complete static extraction of all 30 migration DDL objects, grants, identities, foreign keys, queue producers/consumers and wire versions; verify database catalog after migration.
2. Specify and implement each of six versioned compatibility adapters with strict tenant/branch/session/provenance/consent checks, negative contract tests and explicit no-release decisions.
3. Prove reversible migration with disposable PostgreSQL, dual-read/backfill, replay, crash/restart, idempotency, schema rollback and no destructive rename.
4. Obtain explicit architecture-owner approval of canonical roles and ADR-ENG-003/004; separate technical test evidence from independent signoff.

**A1 status remains IN_PROGRESS; A2–A7 remain OPEN.** This update does not authorize ENG-07, customer decisions or professional execution.

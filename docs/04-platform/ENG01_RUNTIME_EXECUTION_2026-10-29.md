# ENG-01 — Durable Orchestration Runtime / ENG01-WP-01

Date: 2026-10-29. Draft branch: engine/eng01-durable-orchestration-20261029; based on Phase04 foundation draft, no main merge, no frozen Phase02 contract edits.

## Runtime architecture and authority

ENG-01 is a deterministic, typed workflow control plane. A user, LLM, HTTP header or recommendation text cannot grant actor status, consent, specialist validation, financial receipts or an approved state transition.

OIDC verifier → Principal(issuer,subject) → authoritative PostgresStore.get (active membership, assigned specialist, branch/tenant RLS) → ENG01 inspect/canonical state graph → typed NextAction requirements. Only one recognized internal mutation is executable through PostgresStore.checkpoint_command with transactional CAS, idempotency and audit. ENG14 policy remains independent and mandatory.

## Delivered source and scope

- runtime/phase04/abc_foundation/eng01_consultation_machine.json: exact compiled snapshot of canonical 20 states and 102 transitions, retaining original actors and guard lists. scripts/validate_eng01.py enforces byte-for-byte semantic equality to original source machine.
- runtime/phase04/abc_foundation/eng01_orchestrator.py: validated deterministic state graph, inspected next actions, role/tenant assignment checks, strict deny on any unsupported or unsafe mutation.
- Only CREATED -> PAUSED uses actual Postgres durability. It must be verified by the DB itself with exact version, scoped membership, single audit and same-key replay. Other transitions, especially PAUSED -> CREATED resume, require atomic consent, policy, revocation and stale-result checks and are intentionally NOT executable through ENG01.
- Existing Phase04 proof of checkpoint resume is not sufficient to claim a complete ENG01 policy-safe resume.
- No new frozen v1 operation, external model call, paid API, media data, production service or customer release.
- New test suite covers immutable graph, no fake approval/actor rights, 404 non-enumeration, wrong role, duplicate/stale key, race and actual PostgreSQL audit.

## Work packages and exit evidence

| Work package | Current status | Proof needed |
| --- | --- | --- |
| WP01 Canonical graph/read-only NextAction + pause command | SOURCE_IMPLEMENTED, exact SHA CI pending | strict drift, scope, replay and PG concurrency |
| WP02 Authenticated typed commands for independent engines | NOT_STARTED | server-bound service identity, versioned input/output schema |
| WP03 All guarded, durable state transitions and orchestration event ledger | NOT_STARTED | transactional evidence and policy recheck in same DB transaction |
| WP04 Durable work scheduling, cancellation, timeout, jitter, poison DLQ, stale-output fencing | NOT_STARTED | independent worker / chaos replay |
| WP05 Traces, alerts, measured benchmarks | NOT_STARTED | SLI test, timeouts and deployment evidence |
| WP06 ENG14 non-bypassable policy + human validation, consultation chain | NOT_STARTED | end-to-end synthetic specialist gate + contract tests |

## Next engines in actual dependency order

1. ENG-02 — adaptive service-aware question registry, contradiction and stop criteria, strict answer schema, specialist review. Deterministic synthetic fixtures first.
2. ENG-03 — evidence provenance, typed input quality, consent-specific gating; NO real images until privacy gate.
3. ENG-04 — source-bounded Beauty Analysis with explicit unknowns and no fabricated probabilities; API/model adapter replaceable.
4. ENG-05 — approved versioned knowledge and service ontology; provenance, conflict handling and retrieval integration.
5. ENG-06 — eligibility hard filters, explainable ranking and traceable recommendation; no execution guarantee.
6. ENG-07 — look-spec generation only after source/decision version binding.

Each engine has independent code, contracts, test evidence and maturity gate. No fake microservice availability or claim that 19 engines are complete.

**Disposition:** ENG-01 PARTIAL IMPLEMENTATION, NOT RELEASED; ENG-02..06 NOT IMPLEMENTED in this branch; Phase04 IN_PROGRESS; no new paid infrastructure authorized.

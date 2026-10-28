# ABC — Phase 02 Architecture & Interface Contracts

**Version:** contract baseline `1.0.0-draft` · 2026-10-29  
**State:** `CONTRACTS_DRAFT_FOR_REVIEW`; not a deployed API, not formal Gate-02 PASS.  
**Owner:** `saleheebrahimi2029-hub` (all internal engineering and delivery responsibility); human specialist / security / privacy review evidence still mandatory when applicable.  
**Stacked branch:** `contracts/phase-02-interface-baseline-20261029` based on Phase-01 PR #10 (ultimately PR #1). `main` and Notion remain read-only.

## Artifacts

- `schemas/*.schema.json`: machine-checkable Draft-2020-12 contract definitions for session, consent, evidence, consultation, knowledge/analysis, recommendations, LookSpec and versions, media, visual jobs/QA, SOP, feasibility, technical plan, specialist validation, handoff, business action and ServicePack.
- `openapi.json`: planned HTTPS endpoints and bounded permissions; no routes deployed.
- `engine-io-registry.json`: ENG-01..19, their typed boundary contracts, owner and failure categories.
- `state-machines.json`: explicit allowed transitions, actors and prerequisite guards; validation in this baseline is structural, not authorization enforcement.
- `events.json`: durable event registry/envelopes, deduplication/ordering and outbox policy.
- `error-catalog.json`, `security-boundaries.md`, `workflows.md`, `versioning-and-migrations.md`, `contract-test-plan.md`, `architecture-decisions.md`, `gate-02-decision.md`.
- `examples/`: valid and invalid canonical fixtures.
- `scripts/validate_phase02.py`: JSON Schema 2020-12 contract validation and referential integrity + fixture tests; `.github/workflows/phase02-contract-integrity.yml`.

## Core design laws

1. **Typed contracts, no free-form prompt-owned product state.** LLM output is untrusted until schema, evidence, authorization and policy checks. A service/model/provider is replaceable.
2. **Tenant derived from verified auth**; never trust `tenant_id` in client request body. DB, object storage and search enforce scope.
3. **Image != LookSpec != feasibility != technical approval.** They have distinct typed entities and life cycles.
4. **Service-specific evidence:** facts are `KNOWN/OBSERVED/USER_REPORTED/INFERRED/UNKNOWN/REQUIRES_PROFESSIONAL_CHECK`; never promote unverified to OBSERVED.
5. **Hard safety interceptors:** no executable chemical parameters without versioned SOP, client evidence and human validation.
6. **Asynchronous visual workers** with immutable accepted versions, CAS version checks, QA before publication and stale-result protection.
7. **Transactions and operational truth** backed by receipts, not AI text; outbox/at-least-once plus idempotent consumers.
8. **One in-salon shared display**, professional note projection requires privileged reauthentication. No at-home portal or automatic external image sending.

## Non-guarantees / Gate-02 blockers

- Schemas are **draft interfaces**; product/ADR decisions and historic source exceptions in Gate-00 remain pending.
- Numeric SLOs/visual thresholds, model/provider choice, real SOP library, jurisdictional privacy details and qualified external reviews are not fabricated.
- Contract CI tests schema/fixture compatibility; no deployed service, running engine, human safety or Visual QA success inferred.
- Breaking contract changes require major version and migration plan; no silent mutation of historic output contracts OUT-01..17.

## Phase-02 MVP Salon OS and Studio coverage amendment

The refined draft contract package adds Clients, Appointment/Calendar, Staff, Service Catalog, Search, Branch, Notification and Salon Configuration schemas and routes, plus a separate `LookPreference` contract (shortlisting is never specialist approval). **Final draft inventory:** 34 JSON Schemas, 39 API paths / 41 operations, 25 events, 5 guarded state machines, 19 engine descriptors, 64 requirement crosswalks, 33 positive and 29 negative schema fixtures. See [coverage report](CONTRACT_COVERAGE_REPORT.md), [mapping](requirements-contract-map.csv) and [12-risk register](contract-risk-register.csv). These are contracts for future implementation, not deployed APIs.

# ADR-ENG-002 — ABC Engine v2 Architecture and Contract Freeze

**Decision date:** 2026-10-30  
**Decision class:** Engineering architecture baseline; **not** a production authorization, human specialist signature, or change to the frozen external v1 API.  
**Status:** FROZEN_FOR_V2_IMPLEMENTATION_IN_DRAFT_PR.  
**Applies to:** in-salon shared-screen consultation where a specialist and customer are physically together.

## Authoritative engine ownership

| Engine | Owns | Explicitly does not own | Inputs | Output |
| --- | --- | --- | --- | --- |
| ENG-04 | Evidence-grounded **Recommendation Intelligence**, consuming visual QA, references and controlled look attributes | Final look choice, treatment approval, knowledge source verification | ENG03 provenance, image/reference pointers, editable-region locks, target intent | Draft candidate look specs, evidence lineage, uncertainty, visual QA status |
| ENG-05 | **Decision Intelligence**: rank/deny candidates with knowledge evidence, specialist constraints and ENG14 policy | Generating new images, approving salon service, issuing human consent | ENG04 candidates/ref, reviewed knowledge refs, critical unknowns, ENG14 decision | Blocked/needs-review evaluation, exclusions, auditable justification |
| ENG-06 | **Technical Planning Intelligence**, **only after a selected-look lock** | Auto-executing treatments, asserting medical/salon qualification, issuing consent | Selected-look lock, ENG05 decision, current condition, SOP reference, specialist findings, purpose-bound consent | Blocked/awaiting-input/plan draft with procedure sequencing, checkpoints, stop conditions, aftercare, professional validation pending |

ENG-01 controls orchestration and state transitions; ENG-02 owns consultation/session records and consent provenance; ENG-03 owns durable evidence ingestion and Claim/Lease/ACK; ENG-14 independently evaluates service policy and professional safety. None may silently mint another engine's output, consent or signoff.

## Protocol and compatibility guarantees

- **v1 remains unchanged**: `abc.internal.engine.synthetic.v1` via `isolated_engine_service.py`, with current ENG04=Analysis, ENG05=Knowledge, ENG06=Decision non-media fixture semantics. It is NEVER routed to v2 by default and never allowed for customer release.
- **v2 draft is distinct**: `abc.internal.engine.v2.draft` with individually typed ENG04/05/06 JSON Schema 2020-12 ports. Strict unknown-field rejection, UUID correlation, exact tenant/branch/session/state_version scope, data provenance, no implicit downgrade, and negative contract tests.
- **v2 runtime is intentionally a fail-closed schema preflight**. No actual recommendation/decision/procedure executor is implemented here; `stub_response` returns `NOT_IMPLEMENTED`. Schema success is **not** feature completeness.
- Input media are controlled synthetic references only; no raw customer images, URL fetch, image generation or paid AI API. Draft result envelopes force `release_approved=false` and `execution_authorized=false`.
- Canonical external `contracts/v1`, 20-state/102-edge machine and 41-operation mapping are untouched. Version promotion needs consumer contracts, independent review, migration tests and rollback, never an in-place class rename.

## Chain and gating

```
ENG02 consent / in-person session
       |           ENG14 deny-by-default policy
ENG03 trusted evidence ------------|
       |                            |
AI Studio Visual QA → ENG04 Recommendation
                              ↓
                   ENG05 Decision + ENG14
                              ↓
         Specialist + client select/lock Look
                              ↓
                ENG06 Technical Plan draft
                              ↓
      Specialist SOP / qualifications / safety validation
                              ↓
        ENG01 policy-gated operational handoff
```

Cross-service calls must be signed workload/JWT audience- and mTLS certificate-bound at the private infrastructure layer. Caller-supplied identity fields in v2 schemas are **correlation data**, not proof of caller identity or access: the actual authenticated principal and tenant scopes must be enforced by ENG01/14 and private gateway before future dispatch. All incoming v2 connections are disabled as business operations until that runtime policy is built and tested.

## Planned v2 migration / rollback

1. Freeze v1 hash/contract behaviour and keep legacy synthetic callers on separate explicit v1 routing. No auto route switch.
2. Review 3 v2 port schemas, expected errors, tenant/session binding, look lock and all negative cases.
3. Implement per-engine v2 runtimes in isolated branches/processes (separate secrets, private endpoints, observability and fixtures); no shared in-process model broker.
4. Add exact contract-version negotiation with consumer-producer compatibility matrix; both sides reject unknown versions.
5. Run local synthetic E2E ENG03→ENG04→ENG05→LookLock→ENG06, fault injection, replay, cross-tenant and regression; then independently provision real PKI/private PostgreSQL.
6. Roll back by disabling v2 routing, preserving v1 fixture-only processing. No v2-generated state is migrated into v1 operational jobs without an explicit reviewed converter.
7. Obtain real professional/security signoffs and all engine G01–G10 gates before any commercial service claim.

## Approval scope and open blockers

Engineering design is fixed for further source-controlled development. Real managed CA/private service registration, role-bound OIDC and database cert identity, professional service SOP/consent signatures, representative image QA, distributed replay ledger and privacy signoff remain open. **ENG04/05/06 = IN_PROGRESS; release = BLOCKED**.

Previous proposal: `ADR_ENG_001_ENGINE_RESPONSIBILITY_REALIGNMENT_2026-10-30.md`. This ADR resolves target semantic ownership for design without retroactively treating v1 fixtures as v2 intelligence.

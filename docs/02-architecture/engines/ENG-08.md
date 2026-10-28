# ENG-08 — Visual Segmentation

Status: `SPECIFIED_ONLY`; release state `NOT_IMPLEMENTED_OR_NOT_VERIFIED`.

## Responsibility

allowed regions/masks/hard boundaries. This engine owns its **typed RegionMaskSet**, not the entire user-facing workflow.

## Input contract

Verified tenant/session context; stable versioned upstream data appropriate to the engine; evidence provenance; authorized actor; policy and configuration version; idempotency key if state is mutated. Specific schema file remains a Phase 02 deliverable and **is not fabricated here**.

## Output contract

`RegionMaskSet` with status, errors, source reference versions, trace/correlation IDs, and explicit uncertainty. Engine-level decisions are not automatically approved physical actions or professional sign-offs.

## Forbidden responsibilities

No cross-tenant reads; no self-granted specialist validation; no invented business action success; no mutation of unrelated visual state; no undocumented bypass of safety; no shadowing authoritative source. Only formally authorized domain owns persistent write transitions.

## Failure and recovery

Typed `BAD_INPUT`, `MISSING_EVIDENCE`, `POLICY_BLOCKED`, `CAPABILITY_UNAVAILABLE`, `STALE_VERSION`, and `UPSTREAM_FAILURE` where relevant. Retry only safe/idempotent operations; expose fallback and checkpoint through orchestrator.

## Implementation work package

Assign engineer and subtask in Phase 02; provide schema, API, module code, health/metric hooks and documented review. Initial test suite: **VIS-01**. No pass status recorded.

## Gate

Contract frozen with consumer review, negative tests, integration results and monitored failure handling before `RELEASED`.

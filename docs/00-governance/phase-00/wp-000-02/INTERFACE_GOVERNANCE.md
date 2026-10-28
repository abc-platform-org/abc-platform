# WP-000-02 — Interface Authority, Security and State Invariants

**Status:** Phase-02 contract requirements; not implemented or load-tested. References: ADR-001..010, MIG-01..20, AUTH-01..15, RES-01..13.

## Boundary 1 — Consultation and evidence

- ENG-02 proposes a **single decision-relevant next question** as a typed `QuestionProposal` with `service_profile_version`, `information_gap`, `decision_impact`, `burden`, `safety_priority`; the orchestrator manages `question_state` and retry logic.
- ENG-03 labels each `EvidenceRecord`: KNOWN, OBSERVED, USER_REPORTED, INFERRED, UNKNOWN, or REQUIRES_PROFESSIONAL_CHECK. Source, timestamp, actor and consent are mandatory where relevant.
- Any uncertain visual inference is barred from silently becoming a specialist observation; unanswered items remain UNKNOWN.

## Boundary 2 — Look and image assets

- `LookSpec`/`LookVersion` is the authority for the desired transformation. `PreviewAsset` is a generated candidate and never silently replaces it.
- Image edit commands specify immutable base image, selected LookSpec version, transform mode, allowed regions, hard-locked regions, masks, prior accepted state and idempotency key.
- The deterministic compositor can prove unchanged pixels **only for designated locked regions** under exact processing rules. Natural inside-mask geometry, identity continuity, lighting and multi-view consistency require benchmarked CV and expert evaluation; no deterministic guarantee.
- No preview reaches `QA_PASSED` without independently generated `VisualQAReport`, accepted test policy version, and an auditable decision.
- If the image generation job finishes against an older Look version, the result may be retained historically but cannot overwrite the selected newer version.

## Boundary 3 — Feasibility, safety, technical plan

- Visual QA success != real-world service feasibility != specialist validation != operational authorization.
- ENG-13 reports `FZ-1` plausible or `FZ-2` conditional until actual professional check; only ENG-16 can record `FZ-3` after verified specialist review, and only within an approved service scope.
- Technical draft references exact `look_version_id`, `sop_version_id`, required evidence and material instructions. Missing chemical history or SOP => require review, stop or advisory-only response, not fabricated formulation/time/concentration.
- Changing material inputs, Look version, SOP version or relevant professional findings makes the previous approval stale or invalid until reviewed.
- ENG-14 policy checks are enforced in the backend/transaction boundary, not only in generated text.

## Boundary 4 — Shared screen and tenant

- The user is a professional operating the system; the customer participates on the **same physical display**. No remote client sign-in, portal, default download/send, or automatic client sharing in the target MVP.
- Default view exposes only context needed for joint consultation; access to sensitive professional, billing or medical-like notes requires authenticated specialist role and screen/privacy precautions.
- Tenant ID is derived from authenticated membership at the backend, NOT free-text model input or an editable client payload. All row, search and asset access must enforce tenant/branch policy.
- Consent is scope/time/purpose bound; redact private data in traces; enforce deletion/retention and export policies before release.

## Boundary 5 — Operational handoff and business actions

- ENG-17 transmits internal `HandoffEnvelope` only after checking `validation_state`, role, target appointment/service, consent and transaction idempotency.
- Ask ABC authority tiers: `READ` (verifiable query), `RECOMMEND` (source-linked proposed action), `EXECUTE` (authorized and typically confirmed business command). No fabricated bookings, payments, stock or revenue.
- A validated beauty plan does not auto-charge money, reserve inventory or finalize a booking; the receiving business domain must authorize and record its own transaction.

## Phase-02 mandatory contracts

`ConsultationProfile`, `QuestionProfile`, `EvidenceRecord`, `LookSpec`, `LookVersion`, `EditCommand`, `RegionMask`, `PreviewAsset`, `VisualQAReport`, `FeasibilityResult`, `SafetyDecision`, `SOPVersion`, `TechnicalPlanDraft`, `SpecialistValidation`, `HandoffEnvelope`, `SalonAction`, `AuditEvent`, `ConsentRecord` — each must have schema version, object ID, tenant context, owner, allowed transitions, error states, privacy classification, tests and compatibility rules.

## Concurrency/failure tests before implementation signoff

1. Duplicate event idempotency; failed worker resumes without lost session state.
2. Stale image job cannot overwrite newer version; rejected QA cannot appear as accepted.
3. Cross-tenant or wrong-role read denied even when front-end hides no controls.
4. Missing SOP/professional check produces no approved executable chemical instructions.
5. Edited Look/SOP invalidates dependent technical plan approval.
6. Failed POS/calendar/inventory command never falsely displays completion; audit and reconciliation recorded.

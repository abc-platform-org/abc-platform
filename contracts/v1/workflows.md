# Phase-02 Durable Workflow / Orchestration Contracts

**Ownership:** ENG-01 orchestrates, ENG-14 supplies backend non-bypassable policy, ENG-16 records human approvals. No LLM sets authoritative session state.

## Critical path
```text
Authenticated specialist
 -> ConsultationSession.CREATED
 -> ConsentRecord.ACTIVE (photo features only)
 -> Service/Intent -> QuestionProfile -> EvidencePackage
 -> AnalysisResult -> RecommendationSet -> LookSpecification
 -> VisualJob async [Mask -> Generate -> Composite -> QA]
 -> QA-passed LookVersion -> client preference / LookSelected
 -> FeasibilityResult -> SOP-bound TechnicalPlan Draft
 -> SpecialistValidation (qualified human, exact version)
 -> HandoffRecord -> internal Appointment/WorkOrder domain receipts
```

## Engine composition and boundary
- ENG-02 question generation receives service/user evidence and current question history; never reads undisclosed private flags.
- ENG-03 checks input/provenance; ENG-04/05 produce service/evidence analysis and grounded knowledge; ENG-06 prioritizes with hard feasibility/safety filters.
- ENG-07 creates type-safe LookSpec and revision operations; ENG-08..11 process image asynchronously with locked regions, QA, non-stale CAS; ENG-12 persists immutable version graph.
- ENG-13 feasibility is advisory/conditional until professional findings; ENG-14 blocks unsafe paths; ENG-15 drafts verified SOP based sequence; ENG-16 validates **only after** qualified specialist actor confirmation.
- ENG-17 publishes internal sanitized handoff; ENG-18 computes source-linked business insights; ENG-19 proposes/executes only authorized and confirmed business actions.

## Outbox/consistency policy
- Session/event update and outbox entry are one DB transaction; consumer is at-least-once; dedupe key is `consumer_id:event_id`.
- Every state-mutation command requires `Idempotency-Key` + `expected_version`. Same key+same payload returns same result; same key+different payload rejects with `CONFLICT`.
- Job handles are immutable, correlating `session_id`, `look_version_id`, `input_hash` and `policy_version`. Late job result never becomes current unless CAS matches selected live version.
- Consent withdrawal cancels future processing and access; derivative deletion and trace retention follow the approved specific policy.
- Handoff/revenue mutations use transactional receipts; retries don't double-charge/double-book/double-debit.
- All engine model outputs pass schema validation and policy gate; parse-only pass does not establish semantic correctness.
- DLQ/manual intervention records retries, attempts, sanitized failure code, scoped actor and replay source.

## Reliability failure classes
`BAD_INPUT`, `NOT_AUTHORIZED`, `TENANT_SCOPE_VIOLATION`, `CONSENT_REQUIRED`, `MISSING_EVIDENCE`, `SAFETY_BLOCKED`, `SOP_UNAVAILABLE`, `HUMAN_APPROVAL_REQUIRED`, `STALE_VERSION`, `CONFLICT`, `VISUAL_QA_FAILED`, `MODEL_TIMEOUT`, `RETRYABLE_UPSTREAM_ERROR`, `CAPABILITY_UNAVAILABLE`. Detailed machine-readable catalogue: `error-catalog.json`.

## Authority separation
`LOOK_SELECTED` != `FEASIBLE` != `TECHNICAL_PLAN_VALIDATED` != `EXECUTION_AUTHORIZED`. Executable workflow must satisfy **all** qualified checks with version binding; pictures alone are never sufficient proof.

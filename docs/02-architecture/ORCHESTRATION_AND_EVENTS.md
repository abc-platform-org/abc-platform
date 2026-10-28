# Durable Orchestration & Eventing

## Operating model

The orchestrator calls typed engines; engines return immutable results. It does not delegate workflow authority to free-form LLM text. Persist each major checkpoint, correlate jobs to session and selected look version, and record a replay-safe event. Safety policy intercepts input, recommendation, preview publication, professional plan, and operational action as required.

## Main workflow

1. Validate actor/tenant/branch/session/consent.
2. Identify intent/service; load authorized contextual facts.
3. Ask one decision-critical adaptive question at a time, with stop condition.
4. Ingest/QA reference and client images.
5. Fan out safe evidence-based analysis and knowledge retrieval where independent; join results deterministically and preserve unknowns.
6. Apply hard filters and qualitative decision cascade.
7. Build look specification; visualize asynchronously with idempotent job.
8. QA output, optionally request correction; keep accepted versions immutable.
9. Lock selected look; assess service feasibility separately from picture quality.
10. Draft SOP-grounded conditional technical plan.
11. Authenticated specialist reviews/edits/validates; invalidation on relevant upstream changes.
12. Emit authorized handoff and business operations; close or pause session.

## Required events

`SESSION_CREATED`, `CONSENT_RECORDED`, `INTENT_SET`, `QUESTION_ASKED`, `ANSWER_RECORDED`, `INPUT_QA_COMPLETED`, `ANALYSIS_READY`, `RECOMMENDATIONS_READY`, `LOOK_SPEC_VERSIONED`, `VISUAL_JOB_CREATED`, `PREVIEW_QA_COMPLETED`, `LOOK_SELECTED`, `FEASIBILITY_REVIEWED`, `PLAN_DRAFTED`, `PLAN_VALIDATED`, `VALIDATION_INVALIDATED`, `HANDOFF_CREATED`, `SESSION_CLOSED`, `ACTION_APPROVAL_REQUESTED`, `ACTION_CONFIRMED`, `POLICY_BLOCKED`.

## Event envelope

```json
{
  "event_id": "uuid", "event_type": "LOOK_SELECTED", "event_schema_version": "1.0.0",
  "tenant_id": "tenant-from-trusted-context", "session_id": "uuid",
  "actor": {"user_id": "uuid", "role": "SPECIALIST"},
  "aggregate_version": 12, "occurred_at": "ISO8601",
  "correlation_id": "uuid", "payload": {"look_version_id": "uuid"}
}
```

## Delivery and recovery

Use transactional outbox, at-least-once delivery with deduplication, bounded retries with jitter, dead-letter review, cancel-on-consent-revocation and stale-result suppression. State cannot be reconstructed only from conversational memory. Define SLIs later with measured GPU/model latency, error rates and recovery tests.

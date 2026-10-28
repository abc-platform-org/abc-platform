# Phase 02 — Strict Contract Hardening Audit (2026-10-29)

**Scope:** Draft interface specification and synthetic contract fixtures. **Not** 19 engine implementations or complete runtime, security, performance, visual QA or expert SOP assurance.

## Findings

12 substantive defects/holes were reproduced by deterministic contract analysis (including state reachability, malformed QA statuses, client-provided approval bypasses and missing event type validation). All are **patched at the contract/schema layer** in this PR, with new executable negative checks; see [defect ledger](STRICT_AUDIT_DEFECTS.csv). No claim that runtime versions are fixed because **runtime implementations do not exist yet**.

## Test coverage additions

- 53 additional explicit consultation transitions, making **102**; reachability assertion and guarded resume/safety return checks.
- Synthetic field-level validators: **33 positive / 39 negative** core fixtures.
- Version-specific event payloads: **25 positive / 77 negative**, one matching positive fixture for every registered type and missing-key/extra-field rejection for every type plus unknown event type.
- API: **41/41 operations** with explicit domain policy guards and 401/403 response definitions; no caller-side business approval shortcut or asserted specialist qualification.
- Schema: QA pass evidence and reference/isolation/identity checks; hard source hash/session binding; confirmed handoff receipt; validated plan blocked-step refusal.
- **Expected synthetic validation cases:** 33+39+25+77 = **174**. Count does not measure runtime behavior, real-client safety, visual quality or event consumer execution.

## Hard runtime release restrictions

- No live client photo data until authenticated tenant isolation, consent, retention/deletion review and tests.
- No chemical or procedural execution without qualified specialist and manufacturer-grounded SOP.
- No deployed preview quality claims before independent real-image benchmark.
- No completed handoff, payment, stock mutation or appointment claim without real domain receipt.
- No G02 **formal** PASS merely from CI; owner must review exact reviewed commit and unresolved release risks.
- More bugs may be found during actual implementation. A global **zero-bug guarantee is not technically defensible** with draft contracts only.

## Outstanding design consideration

Hard coded API status/guard metadata is a normative implementation requirement; tests must verify *server behavior*, not merely API text. Full event consumer replay/idempotency, OpenAPI semantic lint, concurrency race tests and code security tests belong to Phase-04+ implementation gates.

## Additional security finding: event producer identity

12th defect: Event envelopes did not bind `event_type` to a versioned `producer_engine_id` and mandatory trace ID. This permitted a schema-valid event to falsely claim a domain event from a different engine. Added per-type producer discriminator, required `trace_id` and 26 further negative tests (25 mismatched producer engines + missing trace). Runtime permissions must still enforce outbox provenance; schema validation alone does not authenticate publishers.

# Engine Contract Template — ABC-CONTRACT-001

Each ENG-* must have its own versioned contract file under `/contracts/engines` in actual implementation.

```yaml
engine_id: ENG-XX
contract_version: 1.0.0
owner_role: engineering-owner-to-assign
purpose: explicitly bounded responsibility
non_goals: []
input_schema_ref: schemas/XXX.input.schema.json
output_schema_ref: schemas/XXX.output.schema.json
authz_scope: tenant_and_specialist_policy
idempotency_key: required_for_state_mutation
workflow_states: []
safety_interceptors: []
error_codes: []
retry_policy: explicitly_defined
service_level_objectives: TBD_AFTER_BENCHMARK
telemetry:
  required: [correlation_id, trace_id, engine_version, model_version, duration, outcome]
test_suites: []
release_evidence: null
```

## Rules

- Only typed validated messages cross boundaries. `UNKNOWN` evidence stays unknown.
- Errors and timeouts use structured codes. Retries do not duplicate plans, images, sales, bookings or notifications.
- Model-generated free text is advisory; only authorized domain services commit state.
- No engine may self-issue `SPECIALIST_VALIDATED` other than a validation service receiving authenticated human approval.
- No module creates an unapproved booking, payment, marketing campaign or inventory change.
- A contract-breaking change requires explicit major schema/version change, migration, canary and compatibility test.

## Error classes

`BAD_INPUT`, `MISSING_EVIDENCE`, `NOT_AUTHORIZED`, `TENANT_SCOPE_VIOLATION`, `POLICY_BLOCKED`, `CAPABILITY_UNAVAILABLE`, `MODEL_TIMEOUT`, `VISUAL_QA_FAILED`, `SOP_UNAVAILABLE`, `HUMAN_APPROVAL_REQUIRED`, `OUTDATED_VERSION`, `CONFLICT`, `RETRYABLE_UPSTREAM_ERROR`.

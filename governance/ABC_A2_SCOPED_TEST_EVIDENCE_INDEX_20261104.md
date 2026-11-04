# A2 — Scoped Test Evidence Inventory (non-attesting)
Generated 2026-11-04. This is an evidence index, NOT a gate PASS or independent review.

## CI provenance
- CI #498 / commit `58d45503c5f94bb5fbcf1545a8e7a7ad69dd8069`: completed SUCCESS, foundation job SUCCESS, log includes 630 + 16 unittest totals and A2 ledger structural validation.
- CI #500 / commit `c82f95a3c1d495174af11a3321a0102f12dc0491`: foundation job reported SUCCESS, overall workflow was still in_progress when inspected. Its log includes 630 + 16 unittest totals and A2 ledger validation. **Do not call the run successful until GitHub reports completed/success.**
- CI #501 / commit `30c2b9b2dcd1b7ece32c72649192a78065b46e5e`: queued at inspection.
- Test totals are aggregated across suites. No automatic attribution of a passing test to a specific gate is authorized.

## Engine test-file candidates (existence verified by A2 validator)
| Scope | Test files | Attribution |
|---|---|---|
| ENG-01 | test_eng01.py; test_eng01_pg_command.py; test_eng_service_identity.py | Candidate only |
| ENG-02 | test_eng02_consultation.py; test_eng02_signed_pg.py; test_eng02_precapture_http.py; test_pg_outbox.py | Candidate only |
| ENG-03 | test_eng03_durable_pipeline.py; test_eng03_06_pipeline.py | Candidate only |
| ENG-04 | test_eng04_isolated_worker.py; test_eng04_scoped_real_visual.py; test_eng04_visual_qa_real_pixels.py | Candidate only |
| ENG-05 | test_eng05_professional_sources.py; test_eng05_external_authority_pg_integration.py; test_eng05_revocation_race.py | Candidate only |
| ENG-06 | test_eng06_pg_deployed_contract.py; test_eng06_fault_injection_acceptance.py; test_eng06_pg_isolation_negative.py | Candidate only |
| ENG-14 | test_eng14_professional_gate.py; test_eng14_transition_gate.py; test_answer_consumer_eng14.py | Candidate only |
| LEGACY_REVIEW_TRANSPORT | test_eng19_actual_mtls_handoff_pg.py | Candidate only; not canonical ENG-19 |

## Evidence claim template for each of the 80 gates
Every claim must contain:
1. `scope_id`, canonical `gate_id`, exact requirement and pass threshold.
2. `source_sha`, `test_file`, exact `test_case` / assertion, relevant contract and migration.
3. `workflow_run_id`, `job_id`, `job_conclusion`, immutable job/run link.
4. Reproduction command, environment, fixtures and negative cases.
5. Reviewer identity, reviewer authority basis, signature/attestation digest and review timestamp.
6. Explicit limitations, external dependencies and release decision.

**Disallow:** deriving PASS from a filename, a total test count, a green workflow, synthetic-only test without required real deployment evidence, or a self-issued reviewer attestation.

## Closure decision
Current 80 gates OPEN; 8 scopes PARTIAL; no independent signoff issuer provisioned. CI green is necessary but not sufficient. A2 stays BLOCKED until the above evidence is recorded and independently adjudicated. Production and customer release remain FALSE.

# WP-000-03 — QA Evidence, Governance Review and Phase Gate Runbook

**State:** `EVALUATION_POLICY_PROPOSED / QA_REVIEW_PENDING`. [Issue #7](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/7).

## Status vocabulary

| Status | Meaning | Acceptable artifact |
|---|---|---|
| `DOCUMENTED` | Requirement or scenario written | stable source/ID, file SHA |
| `DOCUMENT_CI_PASS` | Structural lint / cross-links / CSV integrity passed | workflow run, job conclusion |
| `CONTRACT_APPROVED` | Named authority signed API/state semantics | ADR/review record with exact SHA |
| `IMPLEMENTED` | Actual running code exists | code commit and component name |
| `EXECUTED` | Test actually ran | test suite, runner, time, artifact |
| `TEST_PASS` | Measured assertion passed in stated environment | per-case results, logs/visual evidence |
| `RELEASE_APPROVED` | Authorized reviewer accepts applicable release Gate | signed gate decision and evidence |

**Never equate** `DOCUMENT_CI_PASS` with runtime engine quality, chemical safety or executed Golden tests.

## Golden and visual evaluation

- Preserve original 120 `ABC-TC-*` IDs; productization v1.2 overlay remains a candidate until source exception/precedence approval.
- Record `AUTHORED_NOT_EXECUTED` for 120; no 120/120 claim.
- Compile test mapping to `ABC-F01..18`, `AIS-001..026`, `PRD-001..020` once platform test files exist.
- `VIS` suites: per-region pixel lock (outside-mask), identity drift, reference-feature-only transfer, multiview consistency, accepted state restoration and version/Undo.
- `PQ` suites: question usefulness, non-repeat, stop condition, contradiction and specialist evidence.
- `TEC` suites: source-specific SOP, lack-of-data escalation, plan version invalidation, human-only validation, no invented chemical values.
- `SEC/BUS/SES`: negative tenant access, shared screen projection, business authorization, stale async results, idempotent retries and recovery.

## Review path

1. QA authority accepts test ontology and evidence types, still no runtime PASS.
2. Phase 02 maps contracts to test scenarios and assigns actual owners.
3. Phase 04 builds runnable harness and fake/synthetic development fixtures; real client photos need consent.
4. Per-service benchmarks and specialist panels calibrate metric thresholds before a release Gate.
5. Execution results include `test_run_id, code_sha, engine/model_version, dataset_version, environment, evaluator, timestamp, pass/fail, exceptions, artifacts`.
6. Test runner, QA reviewer and domain specialist independence documented.
7. Failures block relevant service, not automatically all unrelated capabilities; privacy/tenant unsafe defects block affected exposure until addressed.

## G-00 versus future Gate proof

At **G-00** require a *reviewed test strategy, QA accountable person, evidence taxonomy and responsible later Gate*. Do **not** demand the full 120 tests execute before platform code exists. At G-03/G-05/G-08/G-09 require the appropriate real benchmark/run evidence.

## Formal review

Reviewer gives explicit decision, real role, artifact SHA, linked issue and conditions in `APPROVAL_LEDGER.csv`. No review recorded at this writing.

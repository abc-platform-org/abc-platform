# Release Gate Policy — ABC-GATES-001

## Gate definitions

| Gate | Scope | Evidence required | Failure blocks |
|---|---|---|---|
| G-00 | Source / authority rebaseline | Sources, versions, conflicts, coverage | Contract freeze |
| G-01 | Requirement / engine contracts | Schemas, interfaces, ADR, threat model | Implementation |
| G-02 | Input & consultation/analysis | Question/evidence and image quality tests | Recommendation flow |
| G-03 | Visual quality | mask/pixel/identity/version/human review | Visual release |
| G-04 | Decision | filter/candidate/knowledge consistency | Look selection |
| G-05 | Technical plan | SOP source, evidence checks, expert review, invalidation | Execution handoff |
| G-06 | Shared physical session | role/consent/durable state/recovery | Pilot session |
| G-07 | Business handoff | validated operations and real metrics | Salon OS release |
| G-08 | Pilot | security, expert QA, regression, incident/rollback | MVP launch |
| G-09 | SaaS | multi-tenant isolation, load, data privacy, DR | International launch |

## Gate result record

```yaml
gate_id: G-03
release_candidate: null
status: NOT_RUN # PASS | FAIL | BLOCKED | NOT_RUN
criteria_version: 1.0
required_tests: []
test_run_urls: []
human_reviewers: []
open_blockers: []
decision_by: null
decision_at: null
```

No acceptance rates or latency thresholds invented. Threshold calibration process: representative dataset → benchmark run → error analysis → safety/quality reviewer signoff → freeze threshold → release regression. Report confidence intervals and failure distribution if statistically justified.

## Required continuous tests

Every PR: docs/schema lint + unit + relevant integration checks. Every engine release: contract + benchmark + regression + safety. Each preproduction release: E2E, tenant boundary, shared-screen privacy, recovery and human service review. Image-only QA metrics cannot substitute for specialist review.

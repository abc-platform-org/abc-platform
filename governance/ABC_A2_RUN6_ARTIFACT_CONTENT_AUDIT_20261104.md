# ABC A2 — Independent artifact-content audit, Run #6

Audit date: 2026-11-04. Evidence source: ten ZIP archives downloaded from GitHub Actions run `41885089016`, immutable source SHA `db7fc5d16d12c6ef0e354a19fe0ca262e3049e99`.

## Independently inspected ZIP contents

| Scope | unittest count from logs | JUnit testcase elements | Skipped | SHA256 log verification |
|---|---:|---:|---:|---|
| ENG-01 | 33 | 32 | 0 | PASS |
| ENG-02 | 50 | 50 | 0 | PASS |
| ENG-03 | 56 | 56 | 0 | PASS |
| ENG-04 | 23 | 23 | 0 | PASS |
| ENG-05 | 20 | 20 | 0 | PASS |
| ENG-06 | 19 | 19 | 0 | PASS |
| ENG-14 | 31 | 31 | 0 | PASS |
| LEGACY_REVIEW_TRANSPORT | 49 | 48 | 0 | PASS |
| Security & reliability | 76 across six test logs | not produced | 0 | PASS |
| Performance | 1 JSON report | not applicable | not applicable | not applicable |

**Finding A2-JUNIT-001 (blocking):** 2 of 8 JUnit XML files undercount actual unittest cases. ENG-01 reports 32 of 33; legacy review transport reports 48 of 49. The log parser assumes one-line test results, but some unittest test cases have output split across lines. The CI job succeeded despite this discrepancy. The workflow has now been amended to fail closed on mismatched counts; that new commit must be executed and then the parser corrected.

**Finding A2-SEC-002:** security and reliability evidence consists of six successful test logs and SHA256 manifests; no per-test JUnit or structured gate-to-negative-case assertions were produced. This is a traceability gap, not a claim that the security tests failed.

**Finding A2-PERF-003:** performance JSON was inspected. 1,200 synthetic JSON serialization roundtrips: p50=0.024836 ms, p95=0.026329 ms, p99=0.038862 ms, max=0.052929 ms; Python 3.12.15. The report correctly declares `production_slo_valid=false`, `engine_end_to_end_performance_verified=false`, and `threshold_status=NOT_DEFINED`. Therefore G07 is not approved.

## Independent approval boundary
This artifact inspection is a technical evidence review, **not** an independent authorized architectural, security, legal or qualified salon-professional attestation. An AI assistant cannot impersonate independent reviewers or issue their signatures. All G01–G10 remain OPEN pending their specific required proof and authorized review. Do not mark the 80 gates PASS, close A2, enable ENG-06 customer decisions, or release to production.

## Required next acceptance
1. Fix JUnit multiline parsing and rerun all eight scopes, requiring exact test-count parity and no skipped/failed/error cases.
2. Export structured security/reliability test-case assertions and connect them to individual G05/G06 evidence.
3. Replace JSON microbenchmark with real scoped engine workload benchmark and documented SLO thresholds.
4. Obtain independent architecture, security, operations and qualified professional/legal reviews through authenticated GitHub review identities; preserve signed review IDs and exact source SHA.

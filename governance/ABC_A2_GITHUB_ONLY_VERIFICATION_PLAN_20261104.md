# A2 GitHub-only Engineering Verification Plan
Date: 2026-11-04. GitHub repository and Actions are the exclusive development and verification workspace. No external server is a prerequisite for engineering tests.

## Verified baseline
Foundation CI #498 through #503 all completed SUCCESS. Latest successful workflow #503 on commit `150ea7e792c2d3a7fa70eaffdecab8bd68fb5728`. This establishes repository CI integrity only, not independent engine completion.

## CI implementation sequence
1. Run engine-specific suites in isolated GitHub Actions jobs for ENG-01, ENG-02, ENG-03, ENG-04, ENG-05, ENG-06, ENG-14 and legacy review transport. Store machine-readable JUnit XML per scope as artifacts; retain workflow run, commit and job ID.
2. Provision disposable PostgreSQL service containers and synthetic fixtures in Actions. Never use real customer images, identities, consent records or production credentials.
3. Run separate negative/security suites for tenant isolation, RLS, managed identity contract, replay, revocation, fail-closed ENG-14 and ENG-06/ENG-07 dispatch denial.
4. Add controlled fault injection: lease expiry/fencing, duplicate delivery, database restart, network interruption, retry/ACK, dead-letter recovery. Use deterministic seeds and bounded retries.
5. Benchmark p95/p99 only with documented hardware, test load, sample size, thresholds and reproducible raw results; do not conflate runner metrics with production SLOs.
6. Export per-test case IDs, assertions and artifact checksums. Map each G01–G10 to exact test evidence or explicit BLOCKED gap.
7. Review changes through protected PRs, CODEOWNERS and required checks. Independent security/professional approvals require authorized reviewers; no automatic self-attestation.
8. Record an explicit A2 engineering audit decision and retain deployment/production readiness as separate blocked gates where not demonstrated.

## Required CI artifacts
- `a2/<scope>/junit.xml`, `a2/<scope>/coverage.xml` when supported.
- `a2/<scope>/test-manifest.json`: commit, run, job, environment, test IDs, result, suite.
- `a2/security/negative-results.json`, `a2/reliability/fault-results.json`, `a2/performance/benchmark.json`.
- `a2/evidence-index.json`: immutable artifact digest, gate mapping and reviewer disposition.

## Closure policy
Do not grant PASS solely because a GitHub workflow is green. Independent runtime isolation beyond CI, authorized professional/legal review and customer release remain explicitly unverified until independently evidenced. A2 is OPEN until the required engineering proof and signed audit decision are recorded.

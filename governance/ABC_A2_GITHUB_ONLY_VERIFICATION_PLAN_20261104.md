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

The [A2 scoped workflow](../.github/workflows/a2-scoped-engines.yml) generates these files in the runner workspace. Open the matching run's Artifacts section and match the run ID and commit in the downloaded evidence.

| Artifact name prefix | Runner output | Purpose |
| --- | --- | --- |
| a2-⟨scope⟩ | *a2/⟨scope⟩/junit.xml* and *a2/⟨scope⟩/coverage.xml* when supported | Test results and coverage |
| a2-⟨scope⟩ | *a2/⟨scope⟩/test-manifest.json* | Commit, run, job, environment, test IDs, result and suite |
| a2-⟨scope⟩ | *a2/⟨scope⟩/evidence-index.json* | Output SHA-256 digests and current gate disposition for that scope |
| a2-security-reliability | *a2/security/negative-results.json* and *a2/reliability/fault-results.json* | Negative and fault-injection evidence |
| a2-performance-baseline | *a2/performance/benchmark.json* | Synthetic JSON serialization measurements |

The [A2 closure packet workflow](../.github/workflows/a2-closure-packet-integrity.yml) emits *a2/decision-review/validated-evidence-index.json*. The closure decision records gate mapping and independent reviewer dispositions.

## Closure policy
Do not grant PASS solely because a GitHub workflow is green. Independent runtime isolation beyond CI, authorized professional/legal review and customer release remain explicitly unverified until independently evidenced. A2 is OPEN until the required engineering proof and signed audit decision are recorded.

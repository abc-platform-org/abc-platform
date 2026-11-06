# A2 final-closure evidence requirements and disposition

Scope: ENG-01/02/03/04/05/06/14 and legacy review transport. Owner-delegated AI technical evaluation, **not independent attestation**.

## Verified
Run #9 `41886638487` at `0acf7c24d573381a9e10590303e327fd99e24fcf`: 10/10 jobs success; 10 artifacts; 281/281 unittest/JUnit cases aligned; six security/reliability logs and 76 test executions; matching SHA256 manifests. This proves **selected synthetic CI suites**, not completion of all gates.

## Closure checklist (all require direct, immutable proof)
| Gate | Required proof | Present assessment |
|---|---|---|
| G01 architecture | architecture ADRs, actual code boundaries, dependency diagrams, architecture reviewer | OPEN |
| G02 domain | explicit per-engine acceptance criteria, positive/negative acceptance and specialist workflows | OPEN |
| G03 contracts | versioned request/response schemas, compatibility and contract failure tests | OPEN |
| G04 independence | separately deployed processes, unique identities, network isolation and failure isolation logs | OPEN |
| G05 security/privacy | threat model, tenant/RLS, authz, consent, replay/revocation, penetration review | OPEN |
| G06 reliability | durable queue, lease/fencing, DB restart, network partition, recovery and dead letter proof | OPEN |
| G07 performance | real engine workload, p95/p99, reproducible load, thresholds, resource profile | OPEN |
| G08 professional | qualified salon professional signs sources, procedures, feasibility and stop conditions | OPEN |
| G09 operations | trace IDs, metrics, logs, alerting, backup/restore, RTO/RPO and runbooks | OPEN |
| G10 independent signoff | authenticated independent reviewers, source SHA, decision and date | OPEN |

## Work in progress
Workflow now generates per-case `test-manifest.json` and `evidence-index.json` with SHA256 for each scope. These files are *engineering evidence only*, not signed attestations. They must be validated on a new GitHub Actions run before reliance.

## Explicit release constraints
No production credentials, customer images or personal data in CI. No unapproved ENG-06 to ENG-07 dispatch. No professional advice without specialist validation. Do not change 80 OPEN gates to PASS on the basis of a green CI run or an owner-delegated AI assessment.

## Reviewer decision protocol
For each gate record: scope, gate, immutable SHA, exact artifact digest, test assertion, environment, reviewer GitHub identity, professional qualification if applicable, independent-of-author flag, timestamp, APPROVE/REJECT, conditions. Independent signoff must come from actual authorized reviewers. If owner chooses to waive independence, document the governance exception separately; it does not become independent signoff.

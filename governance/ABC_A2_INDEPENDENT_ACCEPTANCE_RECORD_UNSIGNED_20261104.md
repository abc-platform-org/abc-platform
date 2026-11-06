# ABC A2 — Independent acceptance record (unsigned)
Version: 2026-11-04. This is an evidence-collection template, NOT an approval.

## Review boundary
- Project: ABC, synthetic-only test execution.
- ENG-06 customer execution and ENG-07 dispatch: DENIED until separate authorization.
- Owner delegation does not substitute for independent professional, security, or operations approval.
- Every review must reference immutable commit SHA, GitHub Actions run ID, artifact SHA256, precise test scope and deployment identity.

## G04 — independent deployed engines
Reviewer: UNASSIGNED. Decision: OPEN.
Evidence required: actual independently deployed ENG-03/04/05/06 process/service identities; separate secrets and DB grants; network restrictions; health probes; kill/restart and neighbor survival; cross-tenant and cross-engine denial. Synthetic Python process tests do not satisfy this gate.

## G06 — operational recovery
Reviewer: UNASSIGNED. Decision: OPEN.
Evidence required: controlled network partition, process crash, DB outage, backup/restore, durable queue recovery, duplicate/replay prevention, consent revocation during recovery, measured RTO/RPO and incident trace. Local fixture fault tests are supporting evidence only.

## G07 — end-to-end performance
Reviewer: UNASSIGNED. Decision: OPEN.
Evidence required: real synthetic ENG-02→ENG-03→ENG-04→ENG-05→ENG-06 transaction trace, measured p50/p95/p99 and error rates under explicit concurrency, hardware, warmup and duration, published acceptance thresholds. JSON serialization timing is not E2E performance.

## G08 — qualified domain review
Reviewer name/qualification: UNASSIGNED. Decision: OPEN.
Required review: professional-source authenticity/version, contraindications, feasibility, procedure parameters, stop conditions, material suitability, uncertainty handling, specialist validation and safety escalation. Reviewer must personally inspect artifacts; AI cannot attest on their behalf.

## G09 — observability/operations
Reviewer: UNASSIGNED. Decision: OPEN.
Required review: trace correlation, metrics, actionable alerts, runbook, backup restoration and recovery drills, retention, secrets rotation and failure visibility.

## G10 — independent signoff
Reviewer identity: UNASSIGNED. Decision: OPEN.
Must include signed scoped decision, reviewer role and independence, evidence hashes, exceptions and expiry/revalidation date. No self-approval.

## Decision rules
PASS requires reproducible evidence plus authorized reviewer disposition; FAIL requires remediation and rerun; insufficient proof stays OPEN. Green CI alone cannot close A2. Zero-cost CI is preferred; never silently create paid services. Do not touch unrelated projects.

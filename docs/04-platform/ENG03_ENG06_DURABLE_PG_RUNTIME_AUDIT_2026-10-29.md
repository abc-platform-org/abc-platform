# ABC — ENG-03 Durable Executor and ENG-04/05/06 Synthetic PostgreSQL Runtime Audit
**Audit date:** 2026-10-29  
**Branch:** `engine/eng03-durable-pipeline-20261029`  
**Pull request:** [#34](https://github.com/saleheebrahimi2029-hub/abc-platform/pull/34), **DRAFT**, stacked on #33 -> #32 -> #31 -> #29 -> P04 #23.  
**Release gate:** **NOT APPROVED / SYNTHETIC-ONLY**. `main` and frozen `contracts/v1` unchanged. No customer data or paid provider or deployed cloud.

## 1. Executable chain

`ENG02` already records verified synthetic answers, version-checked session progression, ENG14 `eng14.synthetic.1` policy evidence and `ANSWER_RECORDED` outbox atomically. A distinct answer subscriber (PR #33) projects only tenant/branch/session/event/answer IDs and enqueues an `eng03_input_jobs` row in one transaction.

**ENG-03:** New `abc_eng03_worker` database identity, independent `ENG03Executor` Python runtime, and admin-issued tenant/consumer binding. PostgreSQL selects only authorized jobs under row lock with `FOR UPDATE SKIP LOCKED` and records bounded attempts, fresh random lease token and expiration. `ACK` is written in the **same PostgreSQL transaction as** the source-bound evidence ledger row and downstream durable job; rollback cannot create a false success. Stale/expired lease and second claimant are denied; terminal failure or third expired lease moves to `DLQ`. A restricted SECURITY DEFINER broker exposes the original answer only when a live lease, policy approval, prior ANSWER_RECORDED projection, correct tenant and synthetic-only service all match. ENG03 never receives general SELECT privileges on ENG02/ENG14/membership/consent tables.

**Evidence integrity:** Each synthetic report retains its source answer ID, event ID, question profile, branch, session, aggregate version, ENG14 policy approval and full canonical evidence JSON. The PostgreSQL evidence-insert trigger independently checks the trusted source row, policy, active lease, reported vs unknown classification, source type and value. A consumer-scoped SHA256-derived deterministic evidence ID prevents two independently authorized subscribers of one source event from overwriting each other; a composite `(consumer_id,evidence_id)` foreign key prevents cross-consumer downstream linking. Only USER_REPORTED/UNKNOWN synthetic non-media facts; no OBSERVED or professional diagnosis is fabricated.

**ENG-04 + ENG-05 + ENG-06:** A *second*, independent `abc_pipeline_worker` database identity receives a leased `eng04_06_jobs` row. The job snapshots authorized provenance-bound ledger entries up to its aggregate version and checks stored SHA256 integrity before invoking the separate domain components `SyntheticBeautyAnalysis`, `SyntheticKnowledgeEngine` and `SyntheticDecisionEngine`. Missing questions are explicitly UNKNOWN, not filled by inference. ENG05 accepts no real sources and uses only a labelled TEST_FIXTURE_ONLY catalog. ENG06 produces no candidate while required variables are incomplete, critical answers unknown or review-required; even safe-looking synthetic candidates are conditional, never approved treatments. Results, aggregate provenance digest and ACK commit atomically. Restricted database trigger independently rejects invented/unapproved options, unverified fixtures, unknown/critical inputs, wrong version/scope and stale jobs.

**These are separate logical engines executed in one synthetic-only pipeline process, NOT separately deployed ENG04, ENG05, and ENG06 production services.**

## 2. Code and migration scope

- `runtime/phase04/migrations/0012_eng03_executor_pipeline.sql`: RLS FORCED; six runtime-role credentials overall; per-worker admin-controlled tenant bindings; ENG03 leased job extension; evidence ledger/source validation trigger; ENG04/05/06 downstream jobs/results/decision-gate; a narrow source broker; no public API.
- `abc_foundation/eng03_executor.py`: claim/lease/complete/fail with bounded retry and atomic evidence handoff; consumer-bound workload.
- `abc_foundation/eng04_06_pipeline.py`: source-scoped synthetic analysis/knowledge/decision worker, durable results and ACK, consumer-bound; no real-media input.
- `abc_foundation/staging_engine_workers.py`: private-only no-HTTP worker entrypoints; verifies private/synthetic environment, distinct expected DB role, TLS-mode DSN, administrative binding and scope.
- `tests/test_eng03_durable_pipeline.py`: real PostgreSQL 16 negative and positive integration scenarios, including concurrent claim, expired/fenced lease, crash retry, forged source/policy, unauthorized DB table access, revocation, two consumers sharing one answer without evidence collision, per-tenant binding, source acknowledgement/ledger, missing knowledge, invalid decisions, full four synthetic answers and no automatic professional authorization.

Prior 0001–0011 migration contents and Phase02 contracts remain unchanged. Migration checksums are pinned by the staging migrator.

## 3. Verified results and evidence

- **Verified exact executable-code HEAD** `ba04afdcddab9ce0ec68667af9803baec4b0be83`: [Foundation CI #40866034276](https://github.com/saleheebrahimi2029-hub/abc-platform/actions/runs/40866034276) **SUCCESS — 226/226 Python integration/unit tests**, disposable PostgreSQL 16 with migration **0001–0012**, independent staging migrator journal/checksum/repeatability, RLS role and source restrictions, physical PostgreSQL trigger checks, two authorized subscribers of one answer, crash fencing, 3-attempt DLQ, private startup guards, Docker non-root and zero-paid-API synthetic walkthrough. [Documentation integrity #40866034252](https://github.com/saleheebrahimi2029-hub/abc-platform/actions/runs/40866034252) **SUCCESS**.
- Additional source validation rejects an invented analysis source or an ungated ENG06 candidate at the database level. The analysis worker lacks SELECT privileges on ENG03 fencing-token columns. Four required fields must be known for candidate generation; test-only knowledge provenance and source-specific facts are checked on final results.
- [All PR #34 CI runs](https://github.com/saleheebrahimi2029-hub/abc-platform/pull/34/checks). Earlier failed candidate runs caught unbound shared-worker consumer claim, global evidence ID collision, malformed SQL, ENG06 early generation while maintenance was unknown, and a PL/pgSQL alias collision; these were corrected and retested. **An earlier failure is not counted as a success.**

## 4. Critical non-release blockers

1. **Workload authenticity:** Current `abc_eng03_worker` and `abc_pipeline_worker` are separate role credentials per engine class, but a compromised credential can choose a different admin-active consumer binding. Runtime tenant binding is **NOT cryptographically proven** by a managed service identity. Production requires per-consumer/tenant workload identities bound to actual DB roles, managed issuer, lifecycle/rotation and private TLS/mTLS with network segmentation and penetration testing.
2. **Policy:** ENG14 enforcement in this runtime covers only *the synthetic ANSWER_RECORDED path*, not all 102 ENG01 state transitions, S0–S3 professional risk categories, consent revocation or verified qualifications. The disabled unguarded resume remains blocked.
3. **Domain maturity:** ENG03 does not inspect actual images or media. ENG04 has no computer-vision model. ENG05's catalog is expressly not a reviewed professional knowledge source. ENG06 emits conditional synthetic test candidates, not product recommendations. Real specialist approval and consent remain mandatory.
4. **Privacy and governance:** Synthetic evidence JSON still contains its test answer values; production needs purpose consent, DSR, retention/erase, encryption/KMS, cross-region tenancy boundaries and independently audited data minimization. CI-only DB and test keys must never be reused for clients.
5. **Runtime:** No real Render/managed Postgres workload provisioning, rotation, logging/metrics, private production SLOs, backup/restore drill, multi-tenant chaos/soak tests or independent security signoff exists. The approved product remains unbuilt for release.
6. **Architecture:** No separate network-authenticated deployments for ENG04, ENG05 and ENG06; the offline synthetic components are imported within the single analysis worker. Versioned service-to-service commands and canonical post-analysis event contracts remain distinct follow-on work.

## 5. Exit gate

To approve an operational multi-engine product: managed per-service (and per-consumer) identities, mTLS and secrets; tamper-resistant signed ENG14 decisions and full intervention on authoritative transitions; tenant-safe schema RLS/roles and end-to-end provenance attestation; separate ENG04/05/06 runtimes; real consent/purpose limits; verified specialist/catalog; complete failure/delivery/replay/chaos and recovery tests; observability, SLO, cost authorization and formal release signoffs.

**Current classification: `ENG03_PG_EXECUTOR=CI_CANDIDATE`; `ENG04_05_06_PG_SYNTHETIC_PIPELINE=CI_CANDIDATE`; `ENG14_FULL_POLICY=NOT_IMPLEMENTED`; `P04=IN_PROGRESS`; `RELEASE=BLOCKED`.**

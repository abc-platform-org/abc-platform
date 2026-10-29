# ABC — ENG03 Durable Worker + ENG04/05/06 Synthetic PostgreSQL Chain
**Engineering date:** 2026-10-29. **Draft branch:** `engine/eng03-durable-pipeline-20261029`; stacked PR #34 on PR #33 → #32 → #31 → #29 → Phase04 #23. **No merge into main. Frozen Phase02 contracts unchanged.**

## Mission and complete end-to-end test boundary

This slice turns the previous ENG03 metadata-only pending queue into a **real independent PostgreSQL job executor** and moves the existing deterministic ENG04/05/06 synthetic modules into an independently claimed/acknowledged PostgreSQL pipeline. It is not a trained multi-model analysis product and is not a real salon recommendation. Source facts are synthetic; no client PII, image, live camera, paid model/API, external managed workload IdP or Render deployment.

```text
Human + ENG02 signed identity -> ENG01/ENG14 policy-bound answer transaction
 -> canonical ANSWER_RECORDED outbox
 -> independent abc_answer_worker (ack + projection + ENG03 job)
 -> independent abc_eng03_worker claim/lease/fenced read
 -> restricted DB source broker: original ENG02 answer, event, version, ENG14 ALLOW
 -> provenance-only synthetic ENG03 evidence ledger + ENG04/05/06 job (one transaction + ENG03 ACK)
 -> independent abc_pipeline_worker claim/lease
 -> ENG04 structural report + ENG05 explicitly versioned test-source lookup
 -> ENG06 strictly conditional hard filter
 -> bound SQL result guard + durable result and ACK (one transaction)
```

## Implementation inventory

- **Migration 0012** introduces administrator-provisioned `eng03_worker_bindings`, `abc_eng03_worker` and `abc_pipeline_worker` SQL identities with separate passwords (provided by staging migrator only). These roles have no `BYPASSRLS`, no grant management or membership/consent/ENG02-table access. Roles see only active admin-bound consumers/tenants via forced RLS, and each process additionally pins its consumer ID for all claims and ACK operations.
- `eng03_input_jobs` now has states `QUEUED_PENDING_ENGINE/LEASED/ACKED/DLQ`, lock/lease token/time, attempts, retry backoff and bounded dead-letter after three explicit failures **or expired-crash leases**. All claims use `FOR UPDATE SKIP LOCKED`. Stale/expired/revoked leases cannot commit effects.
- A **restricted SECURITY DEFINER SQL source broker** checks session login role, an active admin consumer binding, the exact leased job token, subscription-derived event/projection, original answer, immutable policy approval and synthetic service. This is the only ENG03 source-read path: no blanket SELECT on ENG02 or client records.
- **ENG03 evidence ledger** stores a draft-v1 evidence artifact together with source event ID, original answer ID, question field, source kind and ENG14 decision ID. Unknowns stay UNKNOWN/NOT_AVAILABLE. A second privileged database trigger independently prevents a forged answer value, false OBSERVED classification, missing or substituted ENG14 proof, wrong tenant/session/lease, and wrong question/attribute; it is not a model-generated assertion.
- The ENG03 worker transaction inserts deduplicated evidence and a `eng04_06_jobs` message **together with the ENG03 ACK**. The analysis worker is a different SQL identity and cannot change evidence source, ENG02 answers, ENG14 decisions or ENG03 queues.
- **ENG04/ENG05/ENG06 worker** uses a second durable lease, reads only evidence from its admin-authorized scoped ledger, re-computes evidence SHA-256 fingerprints, synthesizes UNKNOWN for questions not yet answered and invokes the deterministic synthetic-only modules. ENG05 refuses real/unverified knowledge; an exact labelled fixture `synthetic:offline-catalog/test-v1` is allowed in tests only. ENG06 never generates a candidate from an incomplete four-variable profile or known safety flag.
- A **database-side result trigger** prevents a model/user-supplied candidate from being upgraded to professional approval, a real service being substituted or incomplete/critical-unknown evidence yielding a candidate. Even a passing synthetic fixture is always `CONDITIONALLY_PASSED` with `PROFESSIONAL_CHECK_REQUIRED`. Result INSERT and pipeline ACK commit together.
- `staging_engine_workers.py` provides guarded background worker startup candidates (no listener) with explicit synthetic/private mode, a separately authenticated DB role, TLS DSN and admin-approved consumer/tenant binding. No Render service has been created.
- Staging migration checks now require **six separate runtime role passwords**: app, event worker, orchestrator, answer worker, ENG03 worker, analysis worker. The exact 0012 migration hash is tracked by the existing checksum journal, tested on a disposable fresh PG16 database.

## Negative and failure tests

Integration tests cover signed human/service ENG02 answer producer → outbox and answer worker → source broker → ENG03 claims → evidence proof → analysis claim → evidence/knowledge/recommendation result, including a complete four-question fixture; unread/unknown variables; stale leases; parallel claims; restart/retry; three failures or repeated crashes to DLQ; revocation of admin binding; wrong DB principal; direct attempts to forge ENG14 proof or fake `OBSERVED` evidence; invented or professionally-approving ENG06 options; cross-consumer contamination; and write-result/ACK rollback.

**Evidence note:** A green CI run proves deterministic synthetic code+DB behavior and role-scoped isolation in disposable PG16. It does **not** establish physical service feasibility, trained multimodal beauty analysis, performance guarantees, commercial security or compliance approval. Exact-head CI results must be attached to PR #34 before any gate is marked tested.

## Security threats and still-open release gates

1. **Per-workload deployment identity:** `abc_eng03_worker` is a distinct constrained DB role, but in CI all synthetic consumers share that login and the role may hold multiple admin-granted consumer bindings. A compromised role could select another *admin-authorized* consumer. Production requires per-tenant/per-workload DB principals, private network and managed service identity, not an app-selected consumer string.
2. **Managed external workload identity and mTLS:** None is deployed. Separate PostgreSQL accounts and a SQL broker do not replace independently signed workload identity, rotation or TLS/mTLS across live hosts.
3. **ENG14 beyond answer scope:** ENG14 only protects the synthetic ENG02 QUESTION/ANSWER mutation and synthetic derived results. Full 102-transition ENG01 S0–S3 policy governance, active consent, verified specialist qualification, overrides, expiry and emergency revocation remain not implemented.
4. **Real ENG03/ENG04/ENG05/ENG06:** No media input QA, camera/computer vision, professional ontology, SOP/chemical safety, clinical-style performance assessment, expert-verified service packs, real business decisions, human validation UI or production latency benchmarks.
5. **Outbox and delivery:** Delivery guarantees are **at least once**. SQL effects+ACK are transactional and deduplicated; this does not imply exactly-once external side effects. Lease exhaustion goes to DLQ rather than silently inventing success.
6. **Privacy and cloud:** Customer data, actual Render deployment, paid model APIs and production credentials remain explicitly prohibited until independently approved privacy/security and cost gates. No direct worker can write commercial outcome or service/handoff release state.

**Disposition:** ENG03 worker and ENG04/05/06 synthetic pipeline = **CODE IMPLEMENTED / CI TESTED IF EXACT-HEAD GREEN**. Independent real hosted engines = **NOT RELEASED**. Phase04 = **IN_PROGRESS**. PR #34 stays DRAFT. No main merge.

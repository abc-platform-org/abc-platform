# ABC W1 — ENG05 independent worker accepts verified ENG04 review queue

**Engineering date:** 2026-10-31
**Disposition:** CI/local-only synthetic implementation candidate; no managed deployment or external signoff
**Stack:** ENG04 independent Worker #65 → authenticated same-artifact local TLS1.3/JWT review inbox #67 → this PR

## Change scope

Retain the existing dedicated `abc_eng05_worker` NOLOGIN role and distinct `abc_eng05_ci_login` physical CI login, which cannot assume the older `abc_pipeline_worker` or ENG04 identities. The physical test login is not a managed cloud service identity.

PostgreSQL migration **0025** transactionally re-compiles the existing bounded ENG05 `eng19_claim_synthetic` and `eng19_ack_synthetic` brokers, adding the `eng05_ci_verify_eng04_source` authority check and a new **FORCE-RLS** `eng05_ci_source_receipts` table. Previous 0001–0024 migrations are immutable. The new source guard requires:

- A prior authenticated ENG04→ENG05 Inbox/Queue receipt, with exact persisted Bytes and SHA-256;
- ACKed ENG04 job, engine/version/artifact and `BLOCKED_PENDING_AUTHORITY` report;
- Active independently scoped ENG04 source identity binding (share-locked against concurrent revocation);
- Matching tenant/branch/consumer/session/state_version, active purpose-specific consent and lease-fenced ENG05 worker login;
- Four ACKed real, synthetic ENG03 ledger entries whose ordered aggregate SHA-256 equals the ENG04 report manifest;
- Strict denial of malformed/partial claims of ENG03 provenance and cross-tenant consumer use.

Claim returns metadata-only `eng04_verified_lineage`. ACK verifies the source **again**, after session/consent concurrency locks, and atomically persists ENG05's `SOURCE_UNVERIFIED` result plus an immutable receipt recording ENG04 job ID, ENG04 source SHA, ENG03 manifest SHA and ENG05 output SHA. The outbound record remains **`BLOCKED_PENDING_AUTHORITY`**. No worker permission allows changing its status or dispatching to ENG06.

For the historical offline fixture, only the original `tenant-test/branch-test` payload lacking ENG03 lineage retains its prior synthetic behavior. This is not accepted for new tenant-bound jobs and cannot authorize media or professional source validation.

## Independent runtime and negative tests

The independently bounded `SyntheticEng05ReviewWorker` now validates the database-provided provenance claim, requires exact hash match, calls `SyntheticKnowledgeEngine(...,fixture=None)`, returns **zero grounded facts**, **zero retrieval sources**, and explicit `SOURCE_UNVERIFIED`; it does not synthesize treatment advice. Its separate OS-process entrypoint `python -m abc_foundation.eng05_review_worker` runs one Job only with a loopback PostgreSQL CI connection, `ABC_ENV=LOCAL_INTEGRATION_ONLY`, physically authenticated `abc_eng05_ci_login` and an explicit consumer ID. No public server or cloud service is started.

The integrated test fixture first performs four authentic synthetic ENG02→ENG14→ENG03 answers, independent ENG04 analysis/ACK, actual local TLS1.3/mTLS+asymmetric JWT delivery into ENG05's durable Inbox, then provisions the separate ENG05 physical subscriber by CI admin and runs the ENG05 worker against that *same* persisted queue. Assertions include:

- Exactly one ACK/result and independently persisted SHA-bound provenance receipt.
- Parallel Claim single lease, stale token rejection, re-leasing and one logical result.
- Source ENG04 identity revocation before Claim or after Claim, consent withdrawal after Claim, wrong engine role denial.
- Bad professional content or nonempty sources and facts denied even at SQL ACK.
- Three bounded failures reach DLQ and produce no ENG06 outbox.
- Historical staged-migration checksum/rerun/drift check and new 25th migration/RLS test.

## Remaining gates

The shared historical `SyntheticAnalysisPipeline` still exists for frozen v1/v2 compatibility. This work does not certify a professional salon knowledge base or a real decision engine. Independent ADR-ENG-003/004 ratification, seven managed workload attestations, external private PostgreSQL/network, owner-approved spending, signed professional sources, consent issuer and privacy evidence are still absent. All 190 engine G01–G10 acceptance slots remain OPEN. `main` unchanged, all work in a Draft PR. No paid AI API, new paid infrastructure or real client images.

Next logical scope after exact-head CI: validate ENG05 review results against independently curated, versioned, professionally signed SOP sources; continue only as review drafts until security and specialist ratification. ENG05→ENG06 operational release remains explicitly prohibited.

# ABC W1 — ENG-04 independent synthetic evidence worker and controlled ENG-05 handoff

**Date:** 2026-10-31  
**Status:** ENGINEERING CANDIDATE (CI/local only), no managed deployment, no production ingress, no customer release.  
**Source:** stacked after Draft PR #64, with the 19-engine canonical role registry unchanged.

## Purpose and precise boundaries

ENG-04 owns *Beauty / Visual Analysis*, ENG-05 owns *Professional Knowledge/Ontology*. The former legacy `SyntheticAnalysisPipeline` embeds ENG04/05/06 in one runtime; it is kept unchanged for frozen v1/v2 compatibility. This implementation adds a **separate and independently permissioned** ENG04 review Worker for synthetic, non-image consultation evidence; it does not claim that full computer-vision analysis or the historical combined runtime has been retired.

## Added implementation

- Append-only migration **0023** creates `eng04_ci_worker_bindings`, `eng04_ci_jobs` and `eng04_ci_results` with **ENABLE/FORCE RLS**, no worker direct table privileges and dedicated broker functions `eng04_ci_claim/ack/fail/result_for_review`. Inherits the dedicated ENG04 NOLOGIN role from 0022. A distinct, revocable physical ENG04 CI LOGIN is inherited from previous CI bootstrap.
- No public submission route. Work items can be inserted only by a disposable test administrator after real ENG03 evidence-ledger data exists. There is no auto-dispatch loop and no independent issuer of authorization claims.
- Claim requires exact worker physical login binding, tenant/consumer/session/version, valid scoped active consent for **AI_PROCESSING + INTERNAL_HANDOFF**, service `synthetic:hair-color`, four distinct valid ENG03 evidence attributes, already ACKed ENG03 source jobs, and matching ENG14 ALLOW decisions. It uses `FOR UPDATE SKIP LOCKED`, short leases and three-attempt DLQ.
- Each source record must include its ENG03 source job, answer, policy decision, evidence ID and SHA256. The Python Worker reconstructs a canonical digest of each record and the source-manifest hash, and refuses missing/duplicated/modified/unverified evidence.
- Independent deterministic `SyntheticBeautyAnalysis` outputs the canonical `eng04.synthetic-evidence.1` artifact carrying exact evidence IDs. ACK is atomic with result persistence, subject to a fresh consent/state check, lease-token fencing and unchanged source-manifest digest.
- The closed `governance/abc_eng04_beauty_analysis_report.v0.review.schema.json` schema now binds `source_engine=ENG-03`, `source_manifest_sha256`, and `professional_validation_verified=false` to the report. ACK rejects changed attributes and attempts to append customer-release claims.
- The persisted artifact is `BEAUTY_ANALYSIS_REPORT` with status **BLOCKED_PENDING_AUTHORITY**. A separately gated read-only export can construct a `abc.internal.capability.v3.review` message for ENG-05. It does not send a message automatically.
- The already independently tested local TLS 1.3 + audience-bound JWT receiver for ENG-04→ENG-05 remains the only authorized **synthetic review transport**; its authenticated inbox receipt is not an ENG05 execution grant. ENG05→ENG06 Outbox remains `BLOCKED_PENDING_AUTHORITY`.

## Negative controls and test plan

- Reject absent or incomplete ENG03 ledger; reject forged source digests, altered values, duplicated fields, missing evidence/ENG14 references.
- Reject nonmember service principals, cross-engine ENG05 direct DB access and stale/revoked ENG04 login bindings.
- Require FORCE RLS, bounded leases and a staged checksum lock for **23** migrations with drift detection.
- Verify local-only worker behavior and that no customer release or ENG04→05 automatic dispatch is accidentally enabled.
- Test existing local mTLS authenticated ENG04→05 handoff with synthetic BEAUTY_ANALYSIS_REPORT, consent and ENG14 gates under the existing transport suite.

**Test coverage boundary:** The new PostgreSQL integration tests create **four authentic, synthetic ENG02 answers via ENG14 policy and the ENG03 executor**, then consume the resulting four immutable ENG03 ledger records through the independent ENG04 Claim/ACK and form a held ENG05 review candidate. Separate tests verify revoked consent, physical identity isolation, incomplete source refusal and forged report rejection. The previously verified local TLS1.3/JWT ENG04→ENG05 review receipt remains a *separate* test harness. A single test that carries the **same durable ENG04 artifact** through authenticated mTLS and all the way to an ENG05 inbox ACK is **still required** before declaring integrated transport acceptance. No production release claim is permitted.

## Blocking requirements before operational cutover

- Independent ADR-ENG-003/004 security/SRE/professional ratification and exact-commit evidence.
- Private managed identity, isolated PostgreSQL, signed mTLS and rollback plan for actual runtime.
- Real signed ENG14 policy issuance and legitimate consent verifier; source professional validation, media privacy and specialist approvals.
- A separate engineering PR must replace the legacy combined pipeline with separately deployed ENG03/ENG04/ENG05/ENG06 receivers and fully prove producer→consumer provenance before any live activation.

**Nonchanges:** protected `main`, Notion, frozen historic migrations, v1/v2 APIs, customer media, paid AI APIs and production services.

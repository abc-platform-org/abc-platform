# ABC W1/W2 — Private staging and consent-first execution package

**Date:** 2026-10-31
**Status:** ENGINEERING CANDIDATE / SECURITY REVIEW REQUIRED / PRIVATE RUNTIME BLOCKED
**Branch:** `implementation/w1w2-precapture-policy-and-private-readiness-20261031`, stacked on W0 PR #57.
**Product:** Salon in-person shared-screen; no remote customer self-service.
**Authority:** Proposed ADR-ENG-003/004; external approvals and all 190 engine G01–G10 acceptance slots still OPEN.

## 1. Verified starting point and infrastructure discovery

PR #57 achieved successful Foundation CI #354 (453 tests + 10 W0 denial mutation tests) and Documentation Integrity #298. This proves local synthetic/static checks, not live multi-engine or service production readiness.

Connected Render workspace was inspected on 2026-10-31; its service listing returned no listed service, and its Postgres inventory returned no instance. This is an **observed connector view**, not proof no deployment exists under other providers or accounts. Do not declare the infrastructure provisioned, assign real endpoints, store credentials in Git, or auto-create a publicly reachable service.

## 2. Immediate W1 — private trust substrate

| Sequence | Infrastructure control | Accept only with external evidence |
|---|---|---|
| W1-A | Private VPC/service networking | Network map, inbound/outbound allowlists, no public engine DNS/listener, private-only service health checks |
| W1-B | Workload identities | Per-engine, per-environment identity (ENG01, ENG02, ENG03, ENG04, ENG05, ENG06, ENG14 first), managed PKI/OIDC, cert rotation and revocation tests |
| W1-C | Mutual auth | TLS 1.3 verified both ways; pinned audience, peer URI and certificate fingerprint; a forged token/missing cert fails |
| W1-D | PostgreSQL | Private managed cluster, role segregation, NOLOGIN permission groups, physical LOGIN identity, ENABLE/FORCE RLS, independent migrator, scoped app roles |
| W1-E | Runtime delivery | Signed build digests/SBOM, non-root containers, secrets vault, immutable logs, controlled rollout and rollback |
| W1-F | Reliability/operations | DB backup restore proof, worker failure injection, DLQ alarms, trace correlation, incident escalation, SLO baselines and on-call evidence |

A real `abc_pipeline_worker` NOLOGIN group may never be turned into a shared LOGIN for expedience. The existing CI's ephemeral identity is insufficient for managed private service trust. An application client may not grant itself an ENGINE or POLICY role, forge a policy proof, or read another tenant.

## 3. Immediate W2 — ENG02 capture/consent trust boundary

**Implemented as a deliberately non-operative safety preflight:**

- New `PostgresStore.authorize_capture_preflight` performs a scoped check against actual PostgreSQL session and consent tables: specialist identity, tenant, branch, client, current `state_version`, `CREATED` state, same ACTIVE consent record for **both** `CAPTURE` and `AI_PROCESSING`, verified evidence, valid retention, non-expired and non-revoked state.
- Exact `POST /v1/consultations/{session_id}/media` now invokes the preflight before parsing a body. Invalid identity/consent/version are rejected; a valid preflight still returns **501**. No picture bytes are read/retained; no model or storage runs; no customer-facing capability was enabled.
- HTTP and ephemeral real PostgreSQL tests check bad identity, missing version, absent/purpose-limited consent, consent revocation, stale session version and failure to enable capture.
- The preflight result deliberately states `capture_authorized=false`: it is a readiness check, **not a reusable upload grant**.

**Still required for a real media pipeline:** independent legitimate consent issuance and disclosure audit; purpose-specific scope and revocation, temporal atomicity against a concurrent revoke; consent verification and artifact write in one properly isolated transaction (or equivalent fencing), short-lived object URL authorization, encryption/object isolation, deletion and retention workers, data-subject erasure, file type/size/virus validation, and specialist/client confirmation. None of this is claimed implemented.

## 4. W2 — bounded ENG05 to ENG06 contract, still blocked

The existing ENG05 worker writes a transactional result and `BLOCKED_PENDING_AUTHORITY` ENG05→ENG06 outbox. **Do not change that status** until:

1. An ENG06-specific private workload identity and runtime process exists, with separately scoped DB LOGIN/role, authenticated listener, signed audience-bound transport, independent policy lookup and non-bypassable ENG14.
2. ENG06 consumer independently validates the ENG05 artifact SHA256, result schema/version, source evidence IDs, specialist knowledge provenance, tenant/branch/session CAS, consent and decision gate P2; no v2 semantic aliases.
3. Durable per-consumer inbox + replay/JTI + Claim/Lease/ACK, idempotent DLQ and rollback are tested under concurrency and forced process restart.
4. A revoked/expired consent or stale session forbids both ACK and any forwarded recommendation.
5. Domain benchmarks verify decisions on real authorized specialist cases; synthetic catalog output is not professional decision quality.
6. A separately reviewed and signed operational authorization changes the outbox release policy. A CI-only receipt cannot authorize this change.

**New bounded review-only evidence:** The existing authenticated 19-engine review receiver is exercised on an isolated local TLS 1.3 `ENG-05→ENG-06` link with a dedicated synthetic ENG05 SPIFFE identity, ENG06 audience-bound JWT, durable PostgreSQL inbox, idempotent repeat receipt, forged-edge denial and independent policy denial. This proves **review-receipt mechanics only** and does not consume the ENG05 outbox, dispatch a real decision job, or independently validate specialist knowledge.

**Proposed ENG06 domain-execution contract status:** `DESIGN_ONLY_UNWIRED`. Do not deploy or dispatch.

## 5. W0 ratification dependency, exact signoff

Issue #58 remains the approval authority tracker; PR #59 is an implementation evidence candidate, **not a signoff**.

- Architecture owner reviews 19 ownerships, six v2 bridges, workflow and source-of-truth compatibility.
- Independent security reviewer signs ADR-ENG-004 and verifies the pre-capture exception closure and private runtime identity evidence.
- Qualified salon professional validates Look selection, SOP provenance and human authority before ENG15/16/17.
- Platform/SRE signs deployment topology, identity lifecycle, observability, backup/restore and rollback.

Each signed review must cite the exact reviewed commit, actual verified signer, evidence, date and any conditions. No independent signoffs currently attached. Do not mark W0 ratified, W1 provisioned, W2 complete, or any of 19 engine G01–G10 ACCEPTED.

## 6. Ordered implementation next actions

1. Resolve any PR #59 CI failures, including PostgreSQL/RLS and ingress tests.
2. Independent review PR #57/59 and issue #58, including external identity/consent ownership and capture atomicity.
3. Provision explicitly approved **private staging only** using managed identities and signed migration receipts; validate real service mTLS and network isolation.
4. Build new ENG06 service-specific interface and receiver behind a separate release-disabled feature flag, then exercise ENG05→ENG06 with synthetic evidence in private CI/staging.
5. Verify policy/race/rollback and qualified-professional domain tests before anything goes beyond staging.
6. Only after security, quality and business release gates are independently approved, consider a controlled pilot. No automatic treatment or unaudited marketing even in the pilot.

## 7. Machine-verifiable evidence

- `governance/abc_w1w2_private_runtime_evidence.v0.review.json` — 12 OPEN external acceptance criteria, no fabricated provider IDs.
- `scripts/validate_abc_w1w2_private_candidate.py` — rejects false operational signoff and validates the pre-capture code gates with eight negative mutation scenarios.
- `runtime/phase04/tests/test_eng02_precapture_http.py` — HTTP denial and no media acceptance.
- `runtime/phase04/tests/test_pg_store.py` — purpose/version/revocation regression.
- `runtime/phase04/abc_foundation/pg_store.py` / `http_api.py` — candidate preflight and fail-closed endpoint.

**Nonchanges:** protected main, Notion, frozen v1/v2 engine contracts, real customer data, paid model APIs and existing blocked ENG06 outbox.

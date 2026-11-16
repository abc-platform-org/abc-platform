# ABC A2 — ADR-ENG-005 source security review and evidence disposition

**Date:** 2026-11-10  
**Engineering candidate code SHA:** `cfd57ecf29cd0b002270f4ac160fc0c6193a3c6b` (draft PR #89)  
**Evidence reconciliation branch:** `audit/a2-evidence-rebaseline-candidate-20261110`  
**Approval classification:** **ENGINEERING REVIEW / RECOMMEND APPROVAL OF DESIGN WITH CONDITIONS — NOT AN INDEPENDENTLY RATIFIED ADR**  
**Relevant reviews:** #58 Architecture, #84 independent Security, #85 SRE, #79 qualified Specialist, #87 identity drift, #81 A2; owner cost hold #63.

## A. Scope, method, and verified source

Connected GitHub private repository Git tree at the code SHA was not truncated: **661 Git tree entries, 616 blobs, 3,667,128 bytes**. Exact Git tree and 15 relevant source/test/document blob SHA entries are locked in `ABC_A2_SOURCE_BASELINE_CANDIDATE_20261110.json`.

Review examined the actual code at the SHA, especially:
- `private_api_mtls.py`, `service_mesh_identity.py`, `private_engine_transport.py`, `private_pg_atomic_admission.py`, `staging_api.py`, `private_engine_service_server.py`, `eng14_transition_policy.py`;
- `0034_a2_private_spiffe_atomic_ingress.sql`; `test_private_api_mtls.py`, `test_private_api_network_mtls.py`, `test_private_engine_mtls.py`, `test_eng14_transition_gate.py`, `test_staging_guards.py`;
- proposed ADR-ENG-003/004/005, 19-owner registry, W1 identity registry and the original 80-slot A2 reconciliation.

**Strict execution limitation:** a *complete* private Git clone was not available in the connected local Python container; no private GitHub archive/clone credential was exposed to that container and outbound `github.com` DNS failed. The container also lacks PostgreSQL server/psql/Docker and psycopg. Accordingly, **full native repository test discovery, database migrations and all remaining full-checkout tests were NOT RUN**, and this review must not claim otherwise. Historical isolated 7 native mTLS tests plus 15 isolated/custom probes from prior work are separately documented in PR #89; they are not full-suite acceptance.

## B. Source-level security properties confirmed (not production attestation)

| Area | Reviewed enforcement | Residual acceptance |
|---|---|---|
| Engine identities | `BoundEngineIdentity.verify`: certificate URI-SAN exact canonical `/staging/eng-XX`, bound signed `sub`, `engine_id`, `consumer_id` and cert SHA256 `cnf` | No external PKI operator / revocation / rotation attestation |
| Engine JWT | Pinned HTTPS issuer/JWKS, RS256, single exact `aud`, JWT UUID4 JTI, `exp-iat<=120`; untrusted `jku`/`jwk`/`x5u`/`x5c` headers rejected | Real issuer provisioning, key-rotation and external policy proof pending |
| Private API mTLS | Exact gateway-only `/gateway/<id>` allowlist in env parser, direct certificate verification and server constructor; deny engine SANs | Independent design ratification and actual provider ingress ACLs pending |
| Fail-closed availability | Unauthorized CA-trusted SAN results in socket close plus server-caught `OSError` rather than `serve_forever` termination | Real managed multi-instance tests not run |
| ENG14 | Only bounded synthetic S0 `CREATED -> PAUSED` with actor `SPECIALIST` possible in deterministic policy; SQL broker separately verifies identity/consent | Not an actual human OIDC, service SOP or qualified specialist signoff |
| PostgreSQL atomic admission | Source checks physical `session_user`, scoped JTI, consent/specialist/state and bounded execution in same transaction | This path is LOCAL_INTEGRATION_ONLY; physical external PG clientcert unverified |
| Six A1 adapters | Contract metadata still `UNMIGRATED` / no runtime dispatch | Professional approvals and migration rollback required |
| ENG06 | Review-only synthetic path, no customer release/ENG07 dispatch authorized | Separate professional and product release authority required |

## C. Material open security risks

### A2-SEC-P0-API-BOOT — staging API bootstrap / legacy SQL compatibility differs from the engine owner's hold

`staging_api.make_private_server` accepts `ABC_ENV=STAGING_PRIVATE` as a target mode and has an env-controlled `LEGACY_SYNTHETIC` database path (`ABC_SYNTHETIC_LEGACY_DB_COMPAT=true`) that validates only `sslmode=require` for a shared `abc_app` login. It also accepts injected `store`/`verifier` objects, by design for testability. In contrast, `private_engine_service_server.configure_private_engine_service` **unconditionally denies actual STAGING_PRIVATE startup** under the owner cost/managed-identity hold. ADR-ENG-005 requires a managed physical PostgreSQL client certificate and no unapproved service startup.

**Risk:** a staging API deployment could use a weaker auth mode or an unreviewed bootstrap path if provisioned by an operator. Existing guard tests reject implicit fallback, but an explicit legacy env opt-in is not a managed identity proof. A functioning customer-facing hosted exploit was **not** observed or claimed; no staging resource exists in the reviewed evidence.

**Disposition:** **P0 OPEN — block ratification for operational use.** Before promotion, remove or hard-disable the legacy mode in STAGING_PRIVATE, require operator-held enablement only in a separately signed deployment change, enforce `MANAGED_MTLS` with physical PG identity, and add negative tests for env opt-in, injected dependencies and unauthorized staging startup. Do not create infrastructure during current cost hold.

### A2-SEC-P0-NATIVE-CI — code SHA differs from passing CI SHA

Six previously successful workflow runs executed source commit `d8c7698bc060b859f5f4db52d572a00db656a2cd`, **not** candidate `cfd57ec...`. The original `ABC_A2_G01_G10_EVIDENCE_RECONCILIATION_v1.json` records 55 historical test mappings tied to the **old** source SHA. Those historical mappings must NOT be treated as new-code test evidence, regardless of synthetic local results.

**Disposition:** **BLOCKING**; execute complete native suites and re-index evidence to actual job IDs or signed local test artifact hashes on the new source, after confirming no incremental spend. Original 80 gates and 14 risk records must stay OPEN until actual acceptance.

### A2-SEC-P0-INDEPENDENT-REVIEW — no attributable external reviewer

PRs #78/#88/#89 showed no GitHub reviewer submissions or assigned requested reviewers during this check. A code-generation assistant is not an independent architecture/security authority.

**Disposition:** **BLOCKING**; obtain identifiable qualified humans for Architecture and Security, then separate SRE and professional approvals. Each decision must include `reviewer_id`, explicit disposition, immutable reviewed head SHA, evidence digest, timestamp, and relevant qualification. No fabricated approvals.

### A2-SEC-P1-EXTERNAL-TRUST — not yet established

The candidate per-engine SPIFFE naming scheme, issuer authority, hostssl `clientcert=verify-full`, certificate rotation/revocation, network default-deny, backup restore and live SRE telemetry have **no operator-attributed provider proof**. A disposable TLS handshake does not establish managed mesh.

**Disposition:** HOLD under #63; do not provision paid resources.

## D. ADR-ENG-005 decision record (proposed, not ratified)

**Engineering recommendation:** **APPROVE THE DESIGN DIRECTION WITH CONDITIONS**, specifically:
1. Keep the seven canonical engine identities `spiffe://abc.internal/staging/eng-XX`; never treat caller-selected consumer IDs as SAN credentials.
2. Keep `exp-iat<=120` for JWT. PR #88 fixes the metadata drift 900→120.
3. Keep gateway admission and engine-to-engine mesh identities explicitly separated, as in PR #89. No implicit old→new alias.
4. Preserve ENG14 independent purpose consent, specialist authority, state CAS and atomic PostgreSQL replay; no bearer or mTLS handshake itself authorizes a professional action.
5. **Reject any operational approval until the P0 staging API bootstrap / legacy SQL path is addressed and full native tests plus independently signed reviews exist.**

**Ratification table:**

| Authority | Decision | Reviewed SHA | Signature |
|---|---|---|---|
| Engineering assistant source audit | `RECOMMEND_WITH_CONDITIONS` | `cfd57ec...` | Not a qualified independent signature |
| Architecture owner / independent Architecture reviewer | `NOT_RECEIVED` | — | — |
| Independent Security reviewer | `NOT_RECEIVED` | — | — |
| Independent SRE reviewer | `NOT_RECEIVED` | — | — |
| Qualified professional specialist | `NOT_RECEIVED` | — | — |
| Owner provider, spending cap, staging deployment authorization | `NOT_AUTHORIZED` | — | — |

**Release status:** `ADR-ENG-005=NOT_RATIFIED`; `A2=OPEN`; `ENG06_RELEASE=BLOCKED`; `ENG07_DISPATCH=BLOCKED`; `NO_NEW_SPEND`.

## E. Evidence rebaseline plan

The new candidate JSON is **separate** from the original 80-slot decision matrix. The new `scripts/validate_a2_rebaseline_candidate.py` checks 15 Git blob hashes against source files in a **real full checkout** and guards against 12 metadata falsifications. Metadata-only validation is deliberately incomplete. Passing this script **never means** full CI, independent ADR approval, or A2 closure.

Before integration:
1. Make a full private clone on an authorized machine and verify HEAD and locked source blobs.
2. Run 97 Phase04 Python test files plus project-wide relevant suites using pinned dependencies, disposable PostgreSQL16/CA, and no client data; preserve JUnit, artifact hashes, complete environment/command manifest, and any skipped-test reasons.
3. Reconcile each of the **80 gate slots** with new source-bound evidence, explicitly distinguishing 55 historic references and 25 without direct mapped evidence. Resolve 14 risks through independent signoff; do not auto-close.
4. Make final candidate source SHA consistent with actual reviewed code after any further security fixes; finalize exact-head Architecture and Security reviews; never use old CI run IDs as validation for new SHA.
5. Only after successful checks propose promotion of the candidate into the canonical A2 matrix by a **separate reviewed commit**. No automatic merge or deployment.

**This document is an engineering review artifact; it is not an independent approval or a readiness certificate.**

---

## F. 2026-11-10 post-review P0 staging bootstrap correction (stacked child proposal)

**Code candidate SHA:** `3cdb34df68da9a6c5c0be8c79a96627f71faaa99` on `audit/a2-staging-api-hard-hold-20261110` (child of Draft PR #90).

**Previous Section C finding A2-SEC-P0-API-BOOT is CODE-MITIGATED in this candidate, NOT operationally closed.** `runtime/phase04/abc_foundation/staging_api.py` no longer constructs any listener or connects to a database under current `STAGING_PRIVATE` launch: after checking intended synthetic/private-scope config it unconditionally raises `staging_owner_cost_and_external_identity_hold`. The previously explicit `LEGACY_SYNTHETIC` and `ABC_SYNTHETIC_LEGACY_DB_COMPAT` path is now rejected with `legacy_shared_database_login_forbidden_in_staging`. Injected Store/Verifier objects, fabricated approval env flags and plausible externally managed TLS paths cannot authorize startup.

**Executed evidence:** local isolated Python3 `unittest` ran **7/7** new real repository test functions from `test_a2_staging_api_owner_hold.py`, with exact source and test file bytes verified against Git blobs `a40102bff728004d61d0d5908331362014c5e6f7` and `bf4c6b0c797c5e5e7dfdcaff4b77d1d6481701fe`. Runtime lacked `psycopg`, so a minimal `psycopg.conninfo` parser/connect stub was injected; no true PostgreSQL integration, full repository checkout, GitHub Actions or external CA was executed. The amended 14 pre-existing staging guard test methods have **not** been rerun as a suite. No paid CI was initiated.

**Residual P0 acceptance:** full dependency-faithful checkout tests and PostgreSQL16/identity regression, independent Architecture/Security review of the **final** code SHA, externally managed provider identity/hostssl cert evidence and explicit owner cost permission are required **before a separately authorized code change may lift the hard hold**.

**ADR-ENG-005:** remains `NOT_RATIFIED`; engineering guidance remains `RECOMMEND_DESIGN_WITH_CONDITIONS`, never an independent reviewer signature. Canonical A2 G01–G10 risk/gate ledger and historical successful CI SHA have **not** been promoted.

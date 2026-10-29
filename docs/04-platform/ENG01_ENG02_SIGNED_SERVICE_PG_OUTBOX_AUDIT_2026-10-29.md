# ABC Security Gate — ENG01 Workload Identity & ENG02 Atomic Answer/Outbox

**Decision date:** 2026-10-29. **Engineering candidate:** PR #32, stacked on PR #31 → PR #29 → Phase04 PR #23. `main` and Phase02 frozen v1 contracts unchanged. **No independent security acceptance, no cloud deploy, no release.**

## Actual dependency and execution boundaries

1. **Human identity:** Access-token verifier pinned to an HTTPS OIDC issuer, audience `abc-api`, RS256/JWKS. Yields only issuer+subject, not self-asserted roles or tenant.
2. **Engine identity:** Independent RS256 workload token verifier, pinned issuer/JWKS, audience `abc-eng01-internal`, exact `svc:abc-eng02`, `ENG-02`, `token_use=service`, UUID `jti`, max 120-second token lifetime. It intentionally ignores token-claimed branch, tenant and permissions.
3. **Dual proof:** `ENG01InternalIngress` independently verifies the two Bearer tokens and passes the two authenticated principals to the writer. A loopback-only `eng01_internal_http.py` server demonstrates actual dual-token HTTP ingress with strict route, JSON limit, duplicate-key refusal and no credential logging; this is **not an approved inter-service production transport**.
4. **Authorization:** Admin-managed `abc.engine_workload_grants` binds exact issuer, subject, engine, action, tenant and branch; active human `SPECIALIST` membership and assigned session are checked separately. Disabling either grant or human membership denies further write or replay.
5. **Database compartment:** Dedicated `abc_orchestrator` PostgreSQL role with non-superuser/no-BYPASSRLS. It has narrow membership/session reads, column-restricted aggregate version updates, outbox INSERT and ENG02 answer/receipt INSERT. App role `abc_app` and worker role `abc_worker` cannot select ENG02 rows or admin workload grants. Migrations 0001–0008 tested in disposable PG16; role needs a **third separate** migration-provisioned secret.
6. **Atomicity:** For synthetic service `synthetic:hair-color` only, one transaction locks the session, checks actual scope and specialist, checks exact active workload grant, checks next question/order/safety and session version, writes ENG02 answer, increments aggregate version and last_event_id, writes Phase02 `ANSWER_RECORDED` canonical envelope, and writes full-fingerprint receipt. Same command+identical service-token-jti replays the saved result; changed metadata/other keys fail. PostgreSQL unique/FK errors roll back the entire transaction.
7. **Outbox limitations:** The canonical event is stored transactionally, but only `SESSION_CREATED` has the narrow existing independent subscriber. The `ANSWER_RECORDED` subscriber/worker and its scoped permissions are **not built**. "Persisted event" does not mean downstream delivery or exactly-once external side effects.

## Security invariants and negative test matrix

| Attack / failure | Current candidate defense | Release requirement still missing |
| --- | --- | --- |
| Forged service JWT, wrong RS256 key, algorithm downgrade, issuer/audience swap | Signature, algorithm, JWKS host and engine identity pinning | Real workload IdP, key rollover/disable, transport TLS/mTLS |
| JWT claims an unauthorized tenant or salon staff role | Claims ignored; server-side grants + human membership checked | Independent external IAM/ABAC assessment |
| ENG02 tries to access another tenant, branch, specialist or service | Admin grant, row-locked session ownership, scope and DB RLS | E2E cross-instance and compromised-credential penetration tests |
| Duplicate command and parallel writers | Session row lock, version CAS, unique answer+event constraints and full-payload receipt | Load/chaos tests and SLA measurement in cloud |
| Token/grant revoked after initial write | Revoked DB permission and inactive membership checked **before receipt replay** | Managed token revocation and end-to-end audit |
| Outbox insertion conflicts or fails | One DB transaction rolls back session version, answer and receipt | Backup/restore and explicit downstream retries/DLQ |
| Model invents medical/chemical recommendation | Only explicitly synthetic value registry; no visual analysis or released service pack | Domain expert review, ENG14 policy and independent model evaluation |
| Authenticated DB role gets compromised | Separate constrained role + RLS, minimal grants | **Open:** DB custom-GUC scope set by trusted app is not cryptographic session proof; compromised DB credential remains a high-severity threat. Isolate network and workload identity, consider SECURITY DEFINER broker with fully verified context before production |
| Malicious internal network caller / header replay | Two signed bearers, short-lived service token and strict JSON | **Open:** loopback test server is not TLS/mTLS private cloud endpoint; no managed secret or replay-nonce store at ingress |

## Explicit outcome categories

- **CODE IMPLEMENTED:** token verifier + dual-auth ingress; dedicated SQL role/grant registry; ENG02 answer/outbox/receipt transaction; local network handler; negative test suites.
- **INTEGRATION CI EVIDENCE:** must cite exact-HEAD GitHub Actions run. Any failure prevents declaring this gate passed.
- **LOCAL-SYNTHETIC ONLY:** all service packs, answers, identity fixtures and test credentials are synthetic. No customer input or generated image is authorized.
- **NOT IMPLEMENTED:** production workload IdP + mTLS, independent ENG02 deployment, external token/secret rotation, full ENG14, real consultation profile, canonical ANSWER_RECORDED subscriber, service API rollout, load/pen tests and release approvals.
- **COST:** 0 new API purchases, 0 Render deployment or cloud DB billing as part of this change.

## Release / handoff gate

**ENG01_AUTH_CANDIDATE = CODE_AND_CI_ONLY; ENG02_PG_OUTBOX_CANDIDATE = CODE_AND_CI_ONLY; ENG01/02 = NOT_RELEASED; P04 = IN_PROGRESS.**

Required next: manager-approved IAM provider and budget only at demo-readiness, external IdP managed workload registrations, per-engine workload credentials, private mTLS reverse proxy, independent DB credential review, explicit admin grant lifecycle, real consent and policy execution, event delivery worker with narrow subscription, cross-tenant penetration testing, backup restore, observability, expert review. No staging deployment or main merge until required gates are signed.

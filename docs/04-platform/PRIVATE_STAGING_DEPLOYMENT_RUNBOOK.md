# ABC Phase 04 — Private Staging Deployment Runbook (Release BLOCKED)

**Decision:** This repo contains deployable PRIVATE-STAGING configuration. It is **not** proof of deployed resources. Rollout must stop if the Render workspace does not have approved paid capacity, linked private GitHub repo, external IdP, database administrative access and staging security approval. NO production or real-client data.

## Verified workspace / Git evidence (2026-10-29)

- Target app: \`saleheebrahimi2029-hub/abc-platform\` private repository; staging branch \`foundation/phase-04-runtime-20261029\`, draft PR #23; do not merge or enable automatic deploy.
- Render workspace listed: \`My Workspace\` (single workspace). At inspection time **zero services and zero PostgreSQL instances** were listed.
- Connected Render actions permit inspecting, creating databases, and creating **public web** services; they do not provide private-service or background-worker creation. **Never substitute a public web service for private API.** Run Blueprint import from Render dashboard under approved admin control.
- Staging target: Render Frankfurt, **one private service (pserv), one background worker, one managed PostgreSQL 16**. Private database inbound IP allowlist must be **empty**. Blueprint is \`infra/render/staging.render.yaml\` (custom path, not repo root).
- A paid service/database may create recurring charges. **No paid resource is to be provisioned until owner approves actual plan/cost** and security ownership. Render's free database is not acceptable for this professional staging gate (retention/reliability limitations).

## Release sequence — execution must be in this order

1. **Preflight approvals:** select verified billing/plan, configure Render↔private GitHub authorization, choose Frankfurt and staging-only resource names; confirm privacy/data location with responsible reviewer.
2. **Import Blueprint, NOT a Web Service:** Render Dashboard → New → Blueprint → connect the private repo → point to \`infra/render/staging.render.yaml\`. Verify resource types \`pserv\` and \`worker\` before clicking apply. Keep \`autoDeployTrigger: 'off'\`. Stop if Render changes types or requests public exposure. Review expected recurring costs.
3. **Provision PostgreSQL only if approved:** Render-managed Postgres 16, \`abc_staging\`, owner \`abc_staging_migrator\`. Verify \`ipAllowList: []\`; never expose port 5432 publicly. Ensure private internal DB hostname and TLS are available from services in Frankfurt. Never paste DB URLs or private signing keys into GitHub issues, docs, PR comments or this chat.
4. **Restricted roles via approved one-time migration job:** From a controlled **private-network execution context** with migration-only credential, run \`python -m abc_foundation.staging_migrate\` using:
   - \`ABC_ENV=STAGING_MIGRATION_PRIVATE\`
   - \`ABC_MIGRATION_APPROVAL=APPROVED_STAGING_ONLY\`
   - \`ABC_STAGING_MIGRATOR_DSN\`: **private** managed DSN for user \`abc_staging_migrator\`, database \`abc_staging\`, \`sslmode=require\`
   - \`ABC_STAGING_APP_PASSWORD\`, \`ABC_STAGING_WORKER_PASSWORD\`: distinct randomly generated 32+ character secrets
   - Never add migrator credential to API or Worker. The migration runner requires permission to CREATE ROLE and CREATE SCHEMA. If the provider's primary user lacks those rights, stop and provision through approved managed DB admin process; do not relax app grants.
   - Script applies exactly migrations \`0001..0006\` with checksum verification, advisory lock and atomic transaction+receipt; hash drift fails.
5. **Provision a *synthetic-only* tenant and specialist membership via restricted, audited admin procedure** using external OIDC subject/issuer. Provision one active \`abc.worker_subscriptions\` for \`SESSION_CREATED\`, binding the exact tenant and consumer ID. Avoid real customers or photos.
6. **Configure runtime secrets** in the Render dashboard, not a committed YAML:
   - Private API: \`ABC_PG_DSN\` (dedicated \`abc_app\`, \`sslmode=require\`), \`ABC_OIDC_ISSUER\`, \`ABC_OIDC_AUDIENCE\`, \`ABC_OIDC_JWKS_URI\`.
   - Worker: \`ABC_WORKER_DSN\` (different \`abc_worker\`, \`sslmode=require\`), \`ABC_CONSUMER_ID\` (pre-provisioned tenant subscription).
   - Staging identity issuer and JWKS host must be HTTPS and share the host due to present verifier policy. Real provider registrations, MFA, session revocation and SOC controls require independent review.
   - All services must have \`ABC_ENV=STAGING_PRIVATE\` and \`ABC_STAGING_PURPOSE=SYNTHETIC_NO_CLIENT_DATA\`. Blueprints enforce declared network mode, **not actual network isolation**; inspect provider resource settings.
7. **Manual deploy only after migration and secrets:** inspect build image non-root user (UID 10001), pinned direct libraries and CI SHA, then run approved manual deployment for private API and Worker. Staging API should only be visible via internal Render network, **no public onrender.com subdomain**. Worker has **no listener**. Do not set \`ABC_ENV\` to any production value.
8. **Post-deploy verification:** internal \`GET /healthz\` should report \`OIDC_PG_LOOPBACK\` (implementation label, currently not a full authenticated DB readiness check); verify a no-token request gives 401, unrelated specialist 403/404, same-tenant specialist can create/get one **synthetic** session, concurrent replay returns one session, revoked membership denies subsequent access. Verify the worker registers only its own tenant's \`SESSION_CREATED\`, projects once across restart, and cannot select \`abc.sessions\` or \`abc.consent_evidence\`.
9. **Observability/security acceptance:** enable Render logs/metrics and alerts (HTTP failures, worker DLQ, DB connection errors, disk/storage), run database backup and restore in separate isolated target, verify secret rotation and CREATEROLE segregation; log only synthetic data and never JWTs/credentials. Document CI commit, deploy IDs, RLS negative tests, IdP issuer and reviewer signoff; real client data strictly prohibited.
10. **Staging acceptance / rollback:** If any guard fails, suspend the private API and Worker, revoke their credentials, **do not create public web services**. Revert to previous tested image only if DB migration is backward compatible; irreversible migrations require restore from verified isolated backup plus change approval. Never automatically drop data, and never claim rollback success without real evidence.

## Critical blocked actions

There is no automatic self-serve route from the connected Render actions to create \`pserv\` or \`worker\`. The Blueprint import is a necessary external admin action. This must **not** be faked by creating a public \`web\` service. There is also no verified managed IdP registration or data-protection signoff. So **LIVE_STAGING = NOT_PROVISIONED** until provider-side evidence proves otherwise.

The migration runner is deliberately not called by API/Worker startup. The worker uses the separate \`abc_worker\` role, and the application DB role does not have general access to outbox/worker tables.

## Readiness gate

| Requirement | Current |
| --- | --- |
| GitHub private branch/PR and CI code | Tested in PR #23 |
| Private Blueprint + container runtime files | Authored and CI validated |
| Render paid capacity & private resources | **NOT PROVISIONED** |
| Managed database + verified backup/PITR | **NOT PROVISIONED** |
| Provider OIDC issuer registration and key rotation | **NOT CONFIGURED** |
| Restricted DB migrations + tenant/worker provisioning | **NOT EXECUTED IN RENDER** |
| Synthetic traffic, negative security acceptance, deploy logs | **NOT RUN IN RENDER** |
| Independent security/privacy/UX approvals | **BLOCKED** |

**Gating rule:** \`P04=IN_PROGRESS\`, \`P04_STAGING_DEPLOYMENT=BLOCKED_EXTERNAL_PROVISIONING\`, \`LIVE_CUSTOMER_ACCESS=FORBIDDEN\`. Do not merge draft PR #23 as complete Phase 04.

## Pending ENG01/ENG02 workload-security staging preconditions (PR #32; NOT DEPLOYED)

- Provision a **separate internal-only orchestrator service** using least-privilege role `abc_orchestrator`; do not embed its secret in `abc_app` or the worker. Existing Blueprint is an earlier-phase configuration, not a deployment approval for this new service.
- Configure **two independent signing authorities**: human OIDC (`abc-api`) and service-workload issuer (`abc-eng01-internal`, RS256, pinned same-host JWKS). Provision external workload identity, rotation and revocation; **the source currently tests generated RSA keys, not a managed provider**.
- Admin-provision `abc.engine_workload_grants` with exact `(issuer, service_subject, engine_id, tenant_id, branch_id, permission, active)` after security review. Never allow runtime services to self-register grants or elevate permissions.
- Run new negative tests for missing/forged workload token, wrong audience/service, revoked specialist/grant, cross-tenant/cross-branch, concurrent replay and RLS. Run separate restore and external network isolation evidence. The implemented HTTP transport binds only `127.0.0.1` with `ABC_ENV=LOCAL_INTEGRATION_ONLY` and is **not** a production network gateway or a replacement for TLS/mTLS.
- The synthetic answer path emits an `ANSWER_RECORDED` canonical event in the same DB transaction as the answer, session aggregate version and receipt; **the existing worker subscription still consumes only `SESSION_CREATED`**. Delivery of `ANSWER_RECORDED` to a distinct, admin-authorized subscriber is a separate future gate.
- Maintain `P04=IN_PROGRESS`, real-customer access prohibited, cloud spend deferred and Phase02 frozen contracts unchanged.

## PR #33: answer worker and ENG14 synthetic policy candidate

Migration plan for PR #33 ran 0001 through 0011; PR #35 extends it to 0013. Four distinct staging DB-role passwords are required: app, worker, orchestrator, and answer-worker. A dedicated `abc_answer_worker` private service is NOT present in the older Render Blueprint and has not been deployed. Admin-only provision an exact tenant and `ANSWER_RECORDED` subscription for that consumer; no runtime self-provisioning. The new ENG14 SQL broker protects synthetic answer writes only, not all ENG01 states or real services. Shared consumer-ID DB settings are not a substitute for per-workload DB identity binding. All real provider IAM, private TLS/mTLS, secret rotation, negative pentesting, expert policy approval, backup/restore and cost authorization remain blocked. No client data, new cloud services, paid API or main merge is authorized by PR #33.

## PR #34: ENG03 independent executor and synthetic analysis worker (NOT DEPLOYED)

- New migration `0012_eng03_executor_pipeline.sql` and six distinct managed DB secrets are mandatory if any future private staging is approved. These code-only candidate services **are not configured in the previous Render Blueprint** and have not been provisioned.
- Admin-provision each exact consumer+tenant and both `abc_eng03_worker` and `abc_pipeline_worker` bindings as separate reviewed workload permissions. Never allow a runtime worker to create or modify its binding. A shared role may only access explicitly enabled consumers, but **real multitenant production requires per-workload DB identity and secret isolation**, not just code-provided consumer IDs.
- The ENG03 input broker is SQL guarded by a valid lease token, ENG14 synthetic-answer proof, immutable original answer ID, tenant and event. The evidence-source trigger rejects fabricated observations. The analysis output gate rejects incomplete or unsafe professional approval.
- Startup module `abc_foundation.staging_engine_workers` is private, no HTTP listener, refuses production/public and non-TLS database DSNs, and requires an active admin binding. Do not deploy until independent IdP/mTLS, data protection, real customer consent, human expert review, backup/restore and capped budget authorization are signed.
- The synthetic ENG04/05/06 worker does not perform actual beauty image analysis or approve a real-world service. Phase04 remains IN_PROGRESS.

## PR #35 — mandatory per-consumer worker SQL authentication (NOT DEPLOYED)

Migration plan now includes **0001–0013**. Database group roles `abc_eng03_worker` and `abc_pipeline_worker` are **NOLOGIN**. The older group-role DSNs are intentionally unusable after migration 0013; do not work around this by re-enabling LOGIN. Provision a dedicated PostgreSQL `LOGIN NOINHERIT` for each approved `(tenant_id,consumer_id,engine role)` with only its engine permission group available via `SET ROLE`. Its password must be generated and held exclusively in a managed secret store. Admin must insert exact active `abc.worker_login_bindings` after `abc.eng03_worker_bindings` is provisioned. The runtime must be configured with `ABC_ENGINE_WORKLOAD_LOGIN`, the matching DB username in `ABC_ENGINE_DSN` and the exact `ABC_ENGINE_CONSUMER_ID`/tenant; no group password may be supplied to the runtime. A revoked login or consumer binding must fail closed before a claim or receipt.

This is **CI-only code**. It has not deployed an external credential broker, TLS/mTLS private service, identity rotation, a real salon knowledge pack, verified consent, or a managed Postgres production tenant. Do not use with customer data and do not merge until independent real staging security review and budget authorization. See `docs/04-platform/ENG03_CONSUMER_BOUND_DB_IDENTITY_AUDIT_2026-10-29.md`.

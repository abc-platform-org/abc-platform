# ABC Phase 04 — Private staging deployment and operational gate

**Status:** \`STAGING_INFRASTRUCTURE_CODE_PREPARED\`. Not a deployed or approved staging environment.  
**Target provider:** Render Blueprint candidate (selected for private service, isolated background worker, managed PostgreSQL). A real Render account, managed identity provider, verified secrets, resource IDs and live URLs have **not** been connected in this repository.  
**Location:** Frankfurt, Germany — provisional EU staging region; this alone does not establish GDPR compliance or data-residency sufficiency.  
**Source:** \`infra/render/staging.render.yaml\`; deployment branch \`foundation/phase-04-runtime-20261029\`; PR #23 Draft.

## 1. Network and identity boundary

\`\`\`text
                    Trusted internal reviewer / test adapter ONLY
                                  |
                Render private network (no public web route)
                                  |
              abc-p04-private-api       external OIDC/JWKS
                    |                          |
           verifies real JWT locally <--------+
                    |
           checks active DB membership + RLS
                    |
    abc_app (only) --- TLS-required internal PostgreSQL
                                  |
                 atomic SESSION_CREATED outbox
                                  |
    abc_worker (only) -- tenant-bound delivery and ACK
                                  |
       abc-p04-session-index-worker (no inbound listener)
\`\`\`

The API Blueprint is \`type: pserv\` (private service), the worker is \`type: worker\`; **no** \`type: web\` resource. The database is a managed Render PostgreSQL 16 instance with \`ipAllowList: []\` (no public database connections), Frankfurt region. Render private services have no public URL. Automatic deployment is **off**; an authorized operator must explicitly approve each rollout. Review provider Blueprint semantics before provisioning. This is not a generic public-facing app.

## 2. Secrets and privilege matrix

| Identity | May read/write | Must never have |
|---|---|---|
| \`abc_staging_migrator\` | Authorized one-off migrations & tenant/role provisioning | Permanent runtime API/Worker environment |
| \`abc_app\` | Scoped sessions, membership self-view, idempotency, append canonical outbox | Superuser, BYPASSRLS, consent activation, raw event reads, worker ack |
| \`abc_worker\` | Tenant-scoped outbox read, subscription read, delivery and non-PII projection writes | Client records, consent, session table, user management, public listener |

No credentials or tokens are committed to Git, GitHub Actions, documentation or Blueprint. Render Blueprint declares only **\`sync: false\` placeholders**. App + worker must receive **different random 32+ character credentials** as restricted managed environment variables. Real OIDC issuer, audience, JWKS URI must be from a vetted provider; token roles/branches are not authorization, and no client-initiated account provisioning is implemented.

\`ABC_PG_DSN\` must use \`user=abc_app\` and \`sslmode=require\`, with the managed database's internal host; \`ABC_WORKER_DSN\` must use \`abc_worker\`, likewise internal and TLS. Do not use Render's auto-generated default/admin \`fromDatabase.connectionString\` for either runtime process — that credential would violate the app/worker least-privilege boundary. The private API and worker fail startup on missing secret, wrong role, missing TLS or absent forced RLS. Database checks confirm the actual SQL login role is non-privileged; not just the URL username.

**Security qualification:** Render's managed internal PostgreSQL TLS may use self-signed certificates. \`sslmode=require\` encrypts but does not provide trusted peer identity verification by itself. Infrastructure owner must review certificate, DNS and threat model; \`sslmode=verify-full\` is preferred when supported by the provider's CA chain. No unaudited claim of end-to-end authenticated TLS.

## 3. Ordered provisioning runbook (not automatically executed)

1. Connect the Render workspace that owns this private ABC repository. Verify selected region **Frankfurt**, billable managed database plan, explicit private service type, and workspace membership/role restrictions. Resolve who is responsible for charges; do not authorize creation on an unrelated workspace.
2. Create a **nonproduction-only** staging identity-provider application/client; approve exact HTTPS Issuer, JWKS and Access Token Audience. Enforce organization policy for MFA/PKCE, user disable/revocation, auditing, and key rotation. Use only synthetic test identities, never live clients.
3. Review \`infra/render/staging.render.yaml\` and the reported costs/DB backup tier. Provision the managed PostgreSQL resource with public inbound disabled. **Do not** start the API or worker before migrations, roles and secret assignment.
4. From a trusted migration execution context able to reach the managed private PostgreSQL endpoint, set variables **out of band**: \`ABC_ENV=STAGING_MIGRATION_PRIVATE\`, \`ABC_MIGRATION_APPROVAL=APPROVED_STAGING_ONLY\`, \`ABC_STAGING_MIGRATOR_DSN\` (named database \`abc_staging\`, migrator user \`abc_staging_migrator\`, \`sslmode=require\`), \`ABC_STAGING_APP_PASSWORD\` and \`ABC_STAGING_WORKER_PASSWORD\` (strong, independently generated). Invoke \`python -m abc_foundation.staging_migrate\` from the \`runtime/phase04\` package. It validates environment, sets least-privilege roles, checks 0001–0006 migration SHA256 and records applied migrations. **Do not paste actual secrets into ChatGPT.**
5. Check provider DB role-management privileges; if the managed migrator cannot create separate login roles, **stop**, obtain an approved provider-side role provisioning method and rerun the tests. Never substitute the default powerful DB account for either runtime role.
6. Provision the \`abc.worker_subscriptions\` row only by authorized admin, binding the synthetic \`ABC_CONSUMER_ID\` to one specific staging tenant and \`SESSION_CREATED\`. Provision synthetic active specialist membership matching the test OIDC identity and branch. Document change-request / audit approval; the worker cannot self-provision subscriptions.
7. Set the Render API's \`ABC_PG_DSN\` and OIDC variables, and the Worker's \`ABC_WORKER_DSN\` and \`ABC_CONSUMER_ID\`. Verify private-only service type, no public URL, separate runtime credentials and \`autoDeployTrigger: off\`. No admin DSN may appear in either service's environment.
8. Deploy the exact audited Git SHA only after documentation integrity, full PostgreSQL integration CI, container build, and private Blueprint policy checks pass. Inspect boot and DB readiness; only synthetic data permitted. Execute active/expired/revoked JWT tests, wrong tenant/branch denial, idempotency replay, pause/resume, registered outbox consumer, lost-ACK recovery and cross-tenant leak regression.
9. Configure logs and metrics: service restarts and availability; DB RLS errors, disk and connection usage; per-consumer pending lease age, retries, DLQ and lag; expired tokens and denied requests; alert owners and runbooks. **No personal data, authorization headers or DB URLs in logs.**
10. Store the deployment's provider resource IDs, exact commit, schema-migration checksums, operational owner and acceptance signatures in a separate deployment evidence record. Mark formal staging gate only after **actual** provisioning and smoke tests are independently witnessed.

## 4. Rollback, recovery and destructive-change controls

- Automatic staging deployment is disabled. Roll back application and worker to the **previous tested SHA/image**, not an arbitrary mutable tag; monitor event retries after rollback. Repeat processing is idempotent by consumer + event ID.
- A database migration cannot safely be rolled back solely by reverting application code. All current migrations are additive but subsequent changes require compatibility review and tested forward-fix/restore. Record a managed Postgres snapshot and verified restore procedure **before** privileged migration; check backup entitlement/retention tier with the provider.
- On suspected token exposure: rotate IdP client/keys as provider supports, revoke active memberships, rotate affected DB credential, stop worker processing and investigate logs.
- On consent/privacy incident: disable relevant processing, revoke permitted scopes and document remediation; image endpoints are still disabled. No deletion service exists.
- Stop deployment if a service gains public ingress, database external IP allowlist is not empty, production data is present, default DB superuser is used by runtime, or staging fails to verify pinned IdP.

## 5. Evidence boundary and remaining gates

**Prepared in code**: Render private Blueprint, nonroot Docker image, private API/worker process launch, startup RLS/DB privilege/TLS guards, safe migration runner, CI policy validator, legacy 88+ integration tests and container build/fail-start checks. Code alone is **not** proof of live hosting.

**Not provisioned or verified**: Render workspace, actual service IDs/private hostnames, managed DB instance, production secret manager, real IdP app and credentials, real user sign-in, authenticated live TLS tunnel, backups/restore, email/push, object storage and privacy attestations, metrics/dashboards/alerts, external penetration test, human acceptance.

**Gate:** \`P04=IN_PROGRESS\`; \`STAGING_LIVE=NOT_PROVISIONED\`; \`P03-UX-EXIT=BLOCKED\`; \`G06/G08/G09=NOT_RUN\`. The 19 engine domains remain not implemented as production services.

Reference: [Render private services](https://render.com/docs/private-services), [Blueprint specification](https://render.com/docs/blueprint-spec), [Postgres internal TLS and IP rules](https://render.com/docs/postgresql-creating-connecting).

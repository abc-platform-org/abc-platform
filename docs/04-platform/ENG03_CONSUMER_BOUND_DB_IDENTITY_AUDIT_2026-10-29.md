# ABC P04 — ENG03 and ENG04–06 Consumer-Bound Database Identity Gate
Date: 2026-10-29. Scope: synthetic-only offline Postgres integration. Branch `security/eng03-consumer-bound-db-login-20261029` stacked draft PR #35 on #34 → #33 → #32 → #31 → #29 → P04 #23. Frozen Phase02 contracts and protected main remain unchanged.

## Threat and explicit decision

**Previously:** one logged-in `abc_eng03_worker` credential could choose a different admin-enabled `consumer_id`, because all consumers shared the same PostgreSQL session principal and RLS consulted a broad role-level binding. A consumer ID or custom session GUC is not authentication.

**Now implemented:** Migration `0013_per_consumer_db_workload_identity.sql` demotes `abc_eng03_worker` and `abc_pipeline_worker` to **NOLOGIN** permission groups and adds `abc.worker_login_bindings` with **FORCE RLS**. Each actual worker authenticates with a distinct PostgreSQL **LOGIN NOINHERIT** principal, created and assigned only by an administrator. Membership grants only **SET ROLE** to the matching engine group, never to another group. The system tests an exact active tuple `session_user + engine group + consumer_id + tenant_id` and the existing admin-controlled worker binding. `session_user` is assigned by PostgreSQL connection authentication and cannot be forged using `SET ROLE`, a caller-controlled consumer ID or `set_config` custom claims. An extra RESTRICTIVE RLS policy on the bindings table applies that exact authenticated tuple to all existing ENG03 and pipeline job/evidence access policies.

The original SECURITY DEFINER source broker and both output-provenance triggers are replaced **without changing migration 0012**; they require a live authorized workload login matched to the exact consumer/tenant/job, not merely a generic group. They retain live lease fencing, original answer and ENG14 source policies. A valid login for consumer A cannot claim, ACK or fetch another consumer B's work, even if both consumers are active under the same tenant. Revoking the login binding or its worker binding denies the next operation with an explicit authorization error.

## Files and actual execution

- `runtime/phase04/migrations/0013_per_consumer_db_workload_identity.sql`: groups NOLOGIN, immutable migration, FORCE-RLS authenticated login binding, restrictive policy, broker/trigger caller checks.
- `runtime/phase04/abc_foundation/eng03_executor.py`: connect with scoped login; SET ROLE only to ENG03 group; verify active DB-approved exact consumer binding before any claim/complete/fail.
- `runtime/phase04/abc_foundation/eng04_06_pipeline.py`: separate scoped login and pipeline group; verify exact consumer binding before claims/results/ACK.
- `runtime/phase04/abc_foundation/staging_engine_workers.py`: fail-closed for old group credentials, requires engine-prefixed, explicit `ABC_ENGINE_WORKLOAD_LOGIN` and matching TLS-mode private DSN. Current strict login prefixes `abc_e3_<randomhex>` and `abc_p6_<randomhex>` are a synthetic deployment convention and not a substitute for actual PostgreSQL authorization.
- `runtime/phase04/tests/test_eng03_durable_pipeline.py`: admin issues real unique PostgreSQL logins per consumer with NOINHERIT/SET TRUE, double-consumer proof, signed source provenance, revocation, group NOLOGIN, cross-engine denial, direct access refusal, prior Claim/Lease/ACK crash/DLQ, and real downstream ENG04–06 job.
- `runtime/phase04/tests/test_staging_guards.py`: explicit private-only role/login mismatch fail-closed tests.

## Security assumptions and operator contract

**Provisioning must be admin-only** and have an external approval record. For every intended consumer, create two distinct database LOGIN identities, one assigned exclusively to `abc_eng03_worker`, the other to `abc_pipeline_worker`; use `NOINHERIT NOSUPERUSER NOCREATEROLE NOCREATEDB NOBYPASSRLS`, random separately rotated credentials in a secret manager. Admin must explicitly insert `abc.eng03_worker_bindings` and `abc.worker_login_bindings` for the exact tenant, consumer and engine. Workload code cannot INSERT/UPDATE either registry. For revocation set `worker_login_bindings.active=false` and disable PostgreSQL LOGIN / rotate its password; remove any active leases via reviewed recovery procedure. For real deployment also require TLS/mTLS, managed secret rotation and actual workload-to-database identity attestation. None of those external steps has been performed by this PR.

The existing staging migrator still accepts group-password variables for historical compatible role creation; migration 0013 changes those groups to NOLOGIN, so those passwords **must not** be used to run either worker. Role provisioning is currently exercised by the disposable test admin; a production-grade reviewed scoped-identity onboarding/rotation workflow is an open work item.

## Evidence and limitations

The last validated **pre-document** CI was [run #40939774954](https://github.com/saleheebrahimi2029-hub/abc-platform/actions/runs/40939774954): 230/230 tests successful; ephemeral PostgreSQL 16 and strict staging migration checksum run. Additional staging negative tests were subsequently added; cite a new **exact-head green** CI run as the final acceptance evidence. Code-level tests against a PostgreSQL superuser-owned CI migration do **not** substitute for executing SECURITY DEFINER source brokers against non-superuser managed staging roles and active network-enforced workload identities. That separate security signoff remains open.

Other blockers unchanged: full ENG14 S0–S3 over ENG01 canonical transitions; real consent, client data privacy, reviewed salon knowledge, real visual analysis, independent ENG04/05/06 network services, real IdP + mTLS, policy/secret lifecycle, penetration testing, staging disaster restore, monitoring, production capacity, release approval. **No real customer data, cloud provisioning, paid API consumption or merge to main.**

**Decision:** Candidate source identity boundary is `PG_SCOPED_IDENTITY_CI_TESTED` only; ENG03 and ENG04–06 remain `SYNTHETIC_ONLY / NOT_RELEASED`. P04=`IN_PROGRESS`.

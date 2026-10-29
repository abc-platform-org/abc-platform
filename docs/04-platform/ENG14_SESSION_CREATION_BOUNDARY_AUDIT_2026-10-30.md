# ABC — ENG14 Session Creation Boundary / PostgreSQL Gate (Draft)

**Date:** 2026-10-30  
**Scope:** stacked draft based on PR #36, with no change to `main` or frozen `contracts/v1`.

## Finding and impact

Migration 0014 revoked the direct app-level `UPDATE(state,checkpoint)` route and forced both legacy and typed ENG01 checkpoint handlers through `eng14_apply_pause`. It did **not** constrain `INSERT` on `abc.sessions`: with valid/spoofed local session GUCs, a database client holding the `abc_app` credential could attempt to initialize a session directly in `PAUSED`, seed a nonzero `state_version` or a forged `checkpoint` without passing through the state transition audit. The app role also retained unnecessary direct UPDATE permissions on `state_version`, `updated_at` and `last_event_id`.

## Patch

Append-only migration `0015_eng14_session_creation_gate.sql`:

1. A `BEFORE INSERT` trigger on `abc.sessions` enforces for `session_user=abc_app`: `state=CREATED`, `state_version=0`, `checkpoint IS NULL`, matching issuer/subject/tenant/branch GUC scope, and active specialist membership. It runs as **SECURITY INVOKER**, avoiding an unexpected definer privilege elevation and keeping membership lookup within the app role's SELECT/RLS rights.
2. Revokes `abc_app` direct `UPDATE(state_version,last_event_id)` grants. PostgreSQL requires at least one UPDATE column privilege for the existing `SELECT ... FOR UPDATE` row locks, so the minimal `UPDATE(updated_at)` grant remains, but a `BEFORE UPDATE OF updated_at` trigger rejects metadata-only writes by `abc_app`. Both ENG01 pause routes already use the 0014 database-owned transition broker; the separately scoped `abc_orchestrator` ENG02 answer path retains its legitimate version update grant.
3. Updates immutable migration enumeration and checksum-based CI staging verification to 15 migrations; includes negative integration tests for forged INSERT state/version/checkpoint and unauthorized UPDATE of version/metadata.
4. Existing migrations remain unchanged. Privileged database operators remain a separate high-trust administrative boundary; the trigger is targeted at the application role.

## Evidence and release posture

First new CI run #40964560642 failed: removing every UPDATE privilege also prevented `SELECT ... FOR UPDATE` in the legitimate checkpoint paths (`psycopg.errors.InsufficientPrivilege`); 16 regression tests failed. The follow-up fix restores only the `updated_at` column privilege while independently SQL-denying metadata-only updates, and the negative test now expects the database gate denial for that column. Re-run exact-head CI before claiming acceptance.

Tests must be executed against disposable PostgreSQL 16 via GitHub Actions on the exact new head. Until green CI, this is **unverified proposed hardening**, not accepted or deployed. Even with green CI, this alone does not provide DB cryptographic principal attestation, create-event/outbox provenance for direct SQL writes, real customer consent, managed PKI/identity, hosted mTLS service deployment, or professional S1–S3 policy signoff.

**Disposition:** `P04=IN_PROGRESS`, `RELEASE=BLOCKED`, `main=UNCHANGED`, `PR=DRAFT`.

# ABC A2 P0 — staging API owner hard-hold / evidence record

**Date:** 2026-11-10
**Source candidate:** `3cdb34df68da9a6c5c0be8c79a96627f71faaa99`
**Branch:** `audit/a2-staging-api-hard-hold-20261110` (stacked on Draft PR #90, not merged)
**Review classification:** SOURCE CODE PATCH + ISOLATED NEGATIVE TESTS; **NOT full CI, managed staging or independent signoff**
**Owner restriction:** no cloud provisioning, paid Actions compute or actual salon/customer data

## Remediation of new A2-SEC-P0-API-BOOT finding

Prior `staging_api.make_private_server` could construct an HTTP mTLS listener under `STAGING_PRIVATE` using `MANAGED_MTLS` or an explicitly opted-in `LEGACY_SYNTHETIC` SQL login with `sslmode=require`, despite the project-wide owner cost/provider hold. In current candidate:

- `make_private_server` checks the existing synthetic scope, private network and valid port, and then **always** raises `staging_owner_cost_and_external_identity_hold` before any server bind or database/OIDC connection.
- `ABC_DB_AUTH_MODE=LEGACY_SYNTHETIC` or presence of `ABC_SYNTHETIC_LEGACY_DB_COMPAT` is separately rejected with `legacy_shared_database_login_forbidden_in_staging`.
- No additional env variable, mock `store` or `verifier`, fake Security/SRE approval or apparently correct mTLS certificate files can override the hold.
- Historical `validate_staging_dsn` and database schema inspection helpers remain *design/test helpers*, not staging service authorization. A new independently reviewed release implementation is required to restore any managed-staging API path once real operator/security/provider approval exists.
- The code does not change canonical engine JWT, SPIFFE, ENG14 policy, physical PG ledger, adapter contracts or customer release gates.

## Exact source evidence

| File | Verified Git blob SHA-1 at source commit |
|---|---|
| `runtime/phase04/abc_foundation/staging_api.py` | `a40102bff728004d61d0d5908331362014c5e6f7` |
| `runtime/phase04/tests/test_a2_staging_api_owner_hold.py` | `bf4c6b0c797c5e5e7dfdcaff4b77d1d6481701fe` |
| `runtime/phase04/tests/test_staging_guards.py` | `d1a232f0727dd7512754965e7cdc272a515c9894` |

Git Blob SHA values for the first two files were independently recomputed using `git hash-object` on the isolated local source copy and matched exactly.

### Local execution — actual targeted tests

Command: `PYTHONPATH=. python run_local_with_stub.py`
Result: `Ran 7 tests in 0.003s` / `OK`. All seven **native GitHub test methods** in `test_a2_staging_api_owner_hold.py` passed, including:
- Correct-looking managed cert/config and forged approval still denied
- Legacy synthetic DB opt-in denied, including explicit flag and mixed mode
- Injected test stores/verifiers cannot authorize server startup
- No `socket.socket` bind or `psycopg.connect` call before mandatory denial
- `main()` cannot start a listener
- Historical weak DSN parser does not grant staging rights
- Public network, customer purpose and malformed ports refused

**Critical limitation:** the sandbox has no installed `psycopg` or PostgreSQL16. A temporary offline shim replaced **only** `psycopg.conninfo.conninfo_to_dict` (using URI parsing) and offered a stub `psycopg.connect` for negative call interception. This is **ISOLATED FUNCTIONAL EVIDENCE**, not a real SQL test, complete dependency stack, codebase checkout, database mTLS or runner integration. The changed existing `test_staging_guards.py` methods have not been executed in the complete project suite.

## A2 scope and disposition

- New source code SHA `3cdb34df...` is **different** from older 6 successful runs at `d8c7698...`; no historical job is reused as current CI PASS.
- `governance/ABC_A2_SOURCE_BASELINE_CANDIDATE_20261110.json` now locks **17 relevant source blob IDs** to this new code SHA. The new `scripts/validate_a2_rebaseline_candidate.py` adds source-bound fail-closed checks and two extra negative metadata mutations (**14 guard cases in design**; original Python validator has not run on full checkout).
- The *canonical* 80-slot A2 ledger, **14 open risks**, ADR-ENG-005 independent ratification and release status remain unchanged. This proposed hard hold mitigates one code path but does **not** close A2.
- Signatures: independent Architecture **none**, independent Security **none**, SRE **none**, qualified professional **none**. A user/owner design direction does not substitute for these reviewers.
- ENG-06 customer operations, ENG-07 dispatch, customer media capture and actual managed staging remain **BLOCKED**.

## Before merge / staging release

1. On a complete authorized checkout, execute the native new test plus all amended existing staging and canonical mTLS/ENG14 suites with pinned dependencies. Run PostgreSQL16 integration and record actual JUnit outputs, exact source SHA, skipped suites and artifact SHA256.
2. Have a qualified independent Architecture and Security reviewer sign an explicit ADR-ENG-005 disposition bound to the final code SHA. Review introduction of any future gateway delegate or physical database identities.
3. Under cost hold, do not provision resources. Real private deployment, external CA and `hostssl clientcert=verify-full` require separately approved provider/budget/operator evidence and SRE acceptance.
4. Only after all source-bound evidence and signoffs, propose updating canonical A2 gate statuses; never automatically promote the candidate ledger.

**Current:** `P0_STAGING_API_CODE_PATH=HARD_HELD_LOCAL_7_OF_7_PASS`; `A2_NATIVE_CI=NOT_RUN`; `ADR_005=NOT_RATIFIED`; `A2=OPEN`; `ENG06_RELEASE=BLOCKED`.

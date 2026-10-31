"""Disposable CI-only end-to-end managed staging migrator contract.

This deliberately uses a separate abc_staging database, never a production URL.
The application's real staging validation is separately tested fail-closed;
only the network-location check is injected for the ephemeral loopback database.
"""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from unittest.mock import patch

import psycopg
from psycopg import sql

from abc_foundation import staging_migrate

ADMIN=os.environ.get("ABC_TEST_PG_ADMIN_DSN")
assert os.environ.get("ABC_ENV")=="LOCAL_INTEGRATION_ONLY" and ADMIN, "test-only database required"

app_pass="disposable-test-app-"+("a"*40)
worker_pass="disposable-test-worker-"+("b"*40)
orchestrator_pass="disposable-test-orchestrator-"+("d"*40)
answer_worker_pass="disposable-test-answer-worker-"+("e"*40)
eng03_pass="disposable-test-eng03-"+("f"*40)
pipeline_pass="disposable-test-pipeline-"+("g"*40)
migration_pass="disposable-test-migrator-"+("c"*40)

with psycopg.connect(ADMIN,autocommit=True) as con:
    con.execute(sql.SQL("""CREATE ROLE abc_staging_migrator LOGIN CREATEROLE
                 NOSUPERUSER NOCREATEDB NOBYPASSRLS PASSWORD {}""").format(sql.Literal(migration_pass)))
    con.execute("GRANT abc_app,abc_worker,abc_orchestrator,abc_answer_worker,abc_eng03_worker,abc_pipeline_worker TO abc_staging_migrator WITH ADMIN OPTION")
    con.execute("CREATE DATABASE abc_staging OWNER abc_staging_migrator")

local=ADMIN.replace("postgres:abc-integration-only-password",
                    "abc_staging_migrator:"+migration_pass).replace(
                    "/abc_phase04_ci","/abc_staging")
# Direct CI PG server has no managed TLS or private Render DNS. Treat only
# local integration connection as a test substitute; real staging preflight
# still rejects localhost, wrong DB/role and missing SSL.
env={"ABC_ENV":"STAGING_MIGRATION_PRIVATE",
     "ABC_MIGRATION_APPROVAL":"APPROVED_STAGING_ONLY",
     "ABC_STAGING_APP_PASSWORD":app_pass,
     "ABC_STAGING_WORKER_PASSWORD":worker_pass,
     "ABC_STAGING_ORCHESTRATOR_PASSWORD":orchestrator_pass,
     "ABC_STAGING_ANSWER_WORKER_PASSWORD":answer_worker_pass,
     "ABC_STAGING_ENG03_PASSWORD":eng03_pass,
     "ABC_STAGING_PIPELINE_PASSWORD":pipeline_pass}
with patch.object(staging_migrate,"validate_migrator_config",return_value=local):
    staging_migrate.apply_migrations(env)
    staging_migrate.apply_migrations(env)
with psycopg.connect(local) as con:
    migration_rows=con.execute("SELECT filename,sha256 FROM public.abc_schema_migrations ORDER BY filename").fetchall()
    assert len(migration_rows)==27
    assert [name for name,digest in migration_rows]==list(staging_migrate.FILENAMES)
    for name,digest in migration_rows:
        assert digest==dict(staging_migrate.planned_migrations())[name]
    for table in ("sessions","consent_evidence","outbox","worker_subscriptions","event_delivery","engine_workload_grants","eng02_answers","eng02_command_receipts","answer_index_projection","eng14_policy_audit","eng03_input_jobs","eng03_worker_bindings","worker_login_bindings","eng14_state_guard_audit","eng01_create_audit","eng14_tenant_workload_mode","eng14_v2_replay_ledger","eng19_review_inbox","eng19_synthetic_jobs","eng19_synthetic_results","eng19_synthetic_outbox","eng06_ci_worker_bindings","eng06_ci_jobs","eng06_ci_results","eng05_worker_bindings","eng04_ci_worker_bindings","eng04_ci_jobs","eng04_ci_results","eng05_ci_source_receipts","eng05_professional_source_candidates","eng05_professional_review_attestations","eng05_professional_conflict_dossiers","eng05_official_reference_discovery","eng05_external_issuer_review_packets","eng03_evidence_ledger","eng04_06_jobs","eng04_06_results"):
        row=con.execute("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid=to_regclass(%s)",
                        ("abc."+table,)).fetchone()
        assert row==(True,True),table
    con.execute("UPDATE public.abc_schema_migrations SET sha256='tampered' WHERE filename=%s",
                ("0006_session_index_projection.sql",))
try:
    with patch.object(staging_migrate,"validate_migrator_config",return_value=local):
        staging_migrate.apply_migrations(env)
except ValueError as err:
    assert "migration_checksum_drift" in str(err),str(err)
else:
    raise AssertionError("tampered checksum did not stop migration")
print("PASS: real staging migrator SQL+checksum journal atomicity, rerun, RLS and drift protection")

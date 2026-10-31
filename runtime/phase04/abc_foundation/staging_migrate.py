"""Controlled staging migration for a managed PostgreSQL database.

Run only from a private, explicitly approved operator context. Not run by the
web API or background worker. Never commit secrets or a full DB connection URL.
"""
import hashlib
import os
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"
FILENAMES = (
    "0001_postgres_core.sql",
    "0002_checkpoint_audit.sql",
    "0003_event_delivery.sql",
    "0004_tenant_subscriptions.sql",
    "0005_consent_lifecycle.sql",
    "0006_session_index_projection.sql",
    "0007_eng01_command_receipts.sql",
    "0008_engine_workload_eng02_answer_outbox.sql",
    "0009_answer_consumer_eng14_policy_gate.sql",
    "0010_eng03_durable_handoff_queue.sql",
    "0011_eng14_privileged_policy_broker.sql",
    "0012_eng03_executor_pipeline.sql",
    "0013_per_consumer_db_workload_identity.sql",
    "0014_eng14_state_guard.sql",
    "0015_eng14_session_creation_gate.sql",
    "0016_eng01_atomic_session_broker.sql",
    "0017_shared_managed_workload_gate.sql",
    "0018_eng14_distributed_replay_ledger.sql",
    "0019_eng19_review_inbox.sql",
    "0020_eng05_synthetic_work_queue.sql",
    "0021_eng06_synthetic_review_worker.sql",
    "0022_eng04_eng05_permission_isolation.sql",
)


def planned_migrations():
    files = sorted(x.name for x in MIGRATIONS.glob("*.sql"))
    if files != sorted(FILENAMES):
        raise ValueError("unexpected_or_missing_schema_migration")
    return [(name, hashlib.sha256((MIGRATIONS / name).read_bytes()).hexdigest())
            for name in FILENAMES]


def validate_migrator_config(env):
    if env.get("ABC_ENV") != "STAGING_MIGRATION_PRIVATE":
        raise ValueError("staging_migration_only")
    if env.get("ABC_MIGRATION_APPROVAL") != "APPROVED_STAGING_ONLY":
        raise ValueError("explicit_staging_migration_approval_required")
    dsn=env.get("ABC_STAGING_MIGRATOR_DSN")
    if not dsn:
        raise ValueError("missing_migrator_dsn")
    c=conninfo_to_dict(dsn)
    if (c.get("user") != "abc_staging_migrator"
            or c.get("sslmode") != "require"
            or c.get("host") in (None, "", "localhost", "127.0.0.1", "::1")
            or c.get("dbname") != "abc_staging"):
        raise ValueError("unexpected_managed_staging_database")
    for key in ("ABC_STAGING_APP_PASSWORD","ABC_STAGING_WORKER_PASSWORD","ABC_STAGING_ORCHESTRATOR_PASSWORD","ABC_STAGING_ANSWER_WORKER_PASSWORD","ABC_STAGING_ENG03_PASSWORD","ABC_STAGING_PIPELINE_PASSWORD"):
        v=env.get(key)
        if not isinstance(v,str) or len(v) < 32 or len(v) > 512:
            raise ValueError("missing_secure_role_credential_"+key)
    values=[env[k] for k in ("ABC_STAGING_APP_PASSWORD","ABC_STAGING_WORKER_PASSWORD","ABC_STAGING_ORCHESTRATOR_PASSWORD","ABC_STAGING_ANSWER_WORKER_PASSWORD","ABC_STAGING_ENG03_PASSWORD","ABC_STAGING_PIPELINE_PASSWORD")]
    if len(set(values))!=6:
        raise ValueError("distinct_role_credentials_required")
    return dsn


def _role(con, name, password):
    present=con.execute("SELECT 1 FROM pg_roles WHERE rolname=%s",(name,)).fetchone()
    if not present:
        con.execute(sql.SQL("""CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB
                    NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}""").format(
                    sql.Identifier(name), sql.Literal(password)))
    else:
        con.execute(sql.SQL("ALTER ROLE {} WITH PASSWORD {}").format(
                    sql.Identifier(name), sql.Literal(password)))
    flags=con.execute("""SELECT rolsuper,rolbypassrls,rolcreaterole,rolcreatedb,rolreplication
                        FROM pg_roles WHERE rolname=%s""",(name,)).fetchone()
    if flags is None or any(flags):
        raise ValueError("unsafe_database_role_"+name)


def apply_migrations(env=None):
    env=os.environ if env is None else env
    dsn=validate_migrator_config(env)
    plan=planned_migrations()
    with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as con:
        current=con.execute("SELECT current_user").fetchone()[0]
        if current != "abc_staging_migrator":
            raise ValueError("database_identity_mismatch")
        # Serialize all independent migration invocations before role creation or schema writes.
        con.execute("SELECT pg_advisory_lock(hashtext('abc_staging_p04_migrations_v1'))")
        try:
            _role(con,"abc_app",env["ABC_STAGING_APP_PASSWORD"])
            _role(con,"abc_worker",env["ABC_STAGING_WORKER_PASSWORD"])
            _role(con,"abc_orchestrator",env["ABC_STAGING_ORCHESTRATOR_PASSWORD"])
            _role(con,"abc_answer_worker",env["ABC_STAGING_ANSWER_WORKER_PASSWORD"])
            _role(con,"abc_eng03_worker",env["ABC_STAGING_ENG03_PASSWORD"])
            _role(con,"abc_pipeline_worker",env["ABC_STAGING_PIPELINE_PASSWORD"])
            with con.transaction():
                con.execute("""
                    CREATE TABLE IF NOT EXISTS public.abc_schema_migrations(
                        filename text PRIMARY KEY, sha256 text NOT NULL,
                        applied_at timestamptz NOT NULL DEFAULT clock_timestamp()
                    )
                """)
                con.execute("""REVOKE ALL ON public.abc_schema_migrations
                             FROM PUBLIC, abc_app, abc_worker, abc_orchestrator, abc_answer_worker, abc_eng03_worker, abc_pipeline_worker""")
            for filename,digest in plan:
                source=(MIGRATIONS / filename).read_text().strip()
                if not source.startswith("--") or "BEGIN;" not in source or not source.endswith("COMMIT;"):
                    raise ValueError("nontransactional_migration_"+filename)
                # Strip the migration file's own outer transaction so the applied
                # SQL and matching checksum receipt commit (or roll back) together.
                start=source.find("BEGIN;")
                ddl=source[start+len("BEGIN;"):-len("COMMIT;")].strip()
                if not ddl:
                    raise ValueError("empty_migration_"+filename)
                with con.transaction():
                    row=con.execute("SELECT sha256 FROM public.abc_schema_migrations WHERE filename=%s FOR UPDATE",
                                    (filename,)).fetchone()
                    if row:
                        if row[0] != digest:
                            raise ValueError("migration_checksum_drift_"+filename)
                        continue
                    con.execute(ddl)
                    con.execute("INSERT INTO public.abc_schema_migrations(filename,sha256) VALUES(%s,%s)",
                                (filename,digest))
                print("Applied", filename, flush=True)
            print("ABC staging schema verified and least-privilege roles configured",flush=True)
        finally:
            con.execute("SELECT pg_advisory_unlock(hashtext('abc_staging_p04_migrations_v1'))")


if __name__=="__main__":
    apply_migrations()

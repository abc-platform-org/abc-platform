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
    for key in ("ABC_STAGING_APP_PASSWORD","ABC_STAGING_WORKER_PASSWORD"):
        v=env.get(key)
        if not isinstance(v,str) or len(v) < 32 or len(v) > 512:
            raise ValueError("missing_secure_role_credential_"+key)
    if env["ABC_STAGING_APP_PASSWORD"] == env["ABC_STAGING_WORKER_PASSWORD"]:
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
        _role(con,"abc_app",env["ABC_STAGING_APP_PASSWORD"])
        _role(con,"abc_worker",env["ABC_STAGING_WORKER_PASSWORD"])
        con.execute("""
            CREATE TABLE IF NOT EXISTS public.abc_schema_migrations(
                filename text PRIMARY KEY, sha256 text NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT clock_timestamp()
            )
        """)
        con.execute("""REVOKE ALL ON public.abc_schema_migrations
                     FROM PUBLIC, abc_app, abc_worker""")
        for filename,digest in plan:
            row=con.execute("SELECT sha256 FROM public.abc_schema_migrations WHERE filename=%s",
                            (filename,)).fetchone()
            if row:
                if row[0] != digest:
                    raise ValueError("migration_checksum_drift_"+filename)
                continue
            # Every migration file has explicit BEGIN/COMMIT.
            con.execute((MIGRATIONS / filename).read_text())
            con.execute("INSERT INTO public.abc_schema_migrations(filename,sha256) VALUES(%s,%s)",
                        (filename,digest))
            print("Applied", filename, flush=True)
        print("ABC staging schema verified and least-privilege roles configured",flush=True)


if __name__=="__main__":
    apply_migrations()

"""Run migration against CI-only Postgres. Never use this script with real data."""
import os
from pathlib import Path

import psycopg

dsn=os.environ.get("ABC_TEST_PG_ADMIN_DSN","")
if not dsn or os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
    raise SystemExit("CI/local integration database only")
with psycopg.connect(dsn,autocommit=True) as con:
    con.execute("""DO $$ BEGIN
        IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='abc_app') THEN
            CREATE ROLE abc_app LOGIN PASSWORD 'integration-only-abc-app';
        END IF;
        END $$""")
    con.execute("""DO $$ BEGIN
        IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='abc_worker') THEN
            CREATE ROLE abc_worker LOGIN PASSWORD 'integration-only-abc-worker';
        END IF;
        END $$""")
    con.execute("""DO $ BEGIN IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='abc_orchestrator') THEN CREATE ROLE abc_orchestrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD 'integration-only-abc-orchestrator'; END IF; END $""")
    for role in ('abc_app', 'abc_worker', 'abc_orchestrator'):
        r=con.execute("SELECT rolsuper,rolbypassrls,rolcreaterole,rolcreatedb FROM pg_roles WHERE rolname=%s",(role,)).fetchone()
        if any(r):
            raise SystemExit(role+" role is not least-privilege")
    for migration in sorted((Path(__file__).resolve().parents[1]/"migrations").glob("*.sql")):
        con.execute(migration.read_text())
        print("Applied", migration.name)
print("PASS: core PostgreSQL migration applied under admin, abc_app has no BYPASSRLS")

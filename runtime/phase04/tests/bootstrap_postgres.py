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
    con.execute("CREATE ROLE abc_orchestrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD 'integration-only-abc-orchestrator'")
    con.execute("CREATE ROLE abc_answer_worker LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD 'integration-only-abc-answer-worker'")
    con.execute("CREATE ROLE abc_eng03_worker LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD 'integration-only-eng03-worker'")
    con.execute("CREATE ROLE abc_pipeline_worker LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD 'integration-only-pipeline-worker'")
    for role in ('abc_app', 'abc_worker', 'abc_orchestrator', 'abc_answer_worker', 'abc_eng03_worker', 'abc_pipeline_worker'):
        r=con.execute("SELECT rolsuper,rolbypassrls,rolcreaterole,rolcreatedb FROM pg_roles WHERE rolname=%s",(role,)).fetchone()
        if any(r):
            raise SystemExit(role+" role is not least-privilege")
    for migration in sorted((Path(__file__).resolve().parents[1]/"migrations").glob("*.sql")):
        con.execute(migration.read_text())
        print("Applied", migration.name)
    # CI-only dedicated NOINHERIT physical LOGIN; the permission group itself
    # remains NOLOGIN as required by migration 0013. No hosted principal issued.
    con.execute("""CREATE ROLE abc_eng05_ci_login LOGIN NOINHERIT
        NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS
        PASSWORD 'integration-only-eng05-physical-login'""")
    # Isolation: ENG05 no longer receives the ENG04 legacy pipeline group.
    con.execute("GRANT abc_eng05_worker TO abc_eng05_ci_login")
    flags=con.execute("""SELECT rolcanlogin,rolsuper,rolbypassrls,rolinherit
       FROM pg_roles WHERE rolname='abc_eng05_ci_login'""").fetchone()
    assert flags==(True,False,False,False),flags
    group=con.execute("SELECT rolcanlogin FROM pg_roles WHERE rolname='abc_pipeline_worker'").fetchone()
    assert group==(False,),group
    assert con.execute("SELECT rolcanlogin FROM pg_roles WHERE rolname='abc_eng04_worker'").fetchone()==(False,)
    assert con.execute("SELECT rolcanlogin FROM pg_roles WHERE rolname='abc_eng05_worker'").fetchone()==(False,)
    assert con.execute("""SELECT pg_has_role('abc_eng05_ci_login',
                    'abc_pipeline_worker','MEMBER')""").fetchone()==(False,)
    assert con.execute("""SELECT pg_has_role('abc_eng05_ci_login',
                    'abc_eng05_worker','MEMBER')""").fetchone()==(True,)
    # A second physical identity is deliberately independent of ENG05.
    # No production issuer, service endpoint or managed credential is created.
    con.execute("""CREATE ROLE abc_eng06_ci_login LOGIN NOINHERIT
        NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS
        PASSWORD 'integration-only-eng06-review-login'""")
    con.execute("GRANT abc_eng06_review_worker TO abc_eng06_ci_login")
    assert con.execute("""SELECT rolcanlogin,rolsuper,rolbypassrls,rolinherit
      FROM pg_roles WHERE rolname='abc_eng06_ci_login'""").fetchone()==(True,False,False,False)
    assert con.execute("SELECT rolcanlogin FROM pg_roles WHERE rolname='abc_eng06_review_worker'").fetchone()==(False,)
print("PASS: core PostgreSQL migrations and isolated ENG05/ENG06 physical CI logins; permission groups NOLOGIN")

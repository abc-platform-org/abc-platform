"""Static hard-deny gate for the bounded ENG05 worker and held ENG06 outbox."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SQL=ROOT/"runtime/phase04/migrations/0020_eng05_synthetic_work_queue.sql"
PY=ROOT/"runtime/phase04/abc_foundation/eng05_review_worker.py"
ISOLATION=ROOT/"runtime/phase04/migrations/0022_eng04_eng05_permission_isolation.sql"

def validate():
    sql=SQL.read_text()
    py=PY.read_text()
    split=ISOLATION.read_text()
    # Fail fast on truncated/duplicated transactional SQL and a broken
    # fail-receipt regex. PostgreSQL CI remains the authoritative SQL parser.
    assert sql.rstrip().endswith("COMMIT;"),"migration_missing_final_commit"
    assert sql.count("\nCOMMIT;")==1,"migration_duplicate_commit_or_tail"
    assert sql.count("CREATE FUNCTION abc.eng19_")==4,"missing_or_duplicate_worker_function"
    assert "OR p_error IS NULL OR p_error !~ '^CI_[A-Z_]{3,60}$'" in sql, "broken_failure_code_regex"
    for statement in (
        "CREATE FUNCTION abc.eng19_submit_synthetic",
        "CREATE FUNCTION abc.eng19_claim_synthetic",
        "CREATE FUNCTION abc.eng19_ack_synthetic",
        "CREATE FUNCTION abc.eng19_fail_synthetic",
        "FOR UPDATE OF job SKIP LOCKED",
        "j.lease_token IS DISTINCT FROM p_lease",
        "j.lease_until<=clock_timestamp()",
        "ce.status='ACTIVE'",
        "ce.revoked_at IS NULL",
        "s.state_version=j.state_version",
        "FOR SHARE OF s,ce",
        "status='BLOCKED_PENDING_AUTHORITY'",
        "status='LEASED'",
        "status='ACKED'",
        "'DLQ'",
        "IF session_user='abc_pipeline_worker'",
        "w.login_name=session_user",
        "w.worker_role='abc_pipeline_worker'",
        "w.consumer_id=b.consumer_id AND w.tenant_id=b.tenant_id",
        "eng19_migrator_worker_login_read",
        "p_tenant IS DISTINCT FROM 'tenant-test'",
        "p_branch IS DISTINCT FROM 'branch-test'"
    ):
        assert statement in sql,statement
    assert "abc.eng19_synthetic_outbox" in sql
    assert "downstream_dispatched" in py
    assert py.count("SET LOCAL ROLE abc_eng05_worker")==3
    assert "SET LOCAL ROLE abc_pipeline_worker" not in py
    assert split.count("CREATE OR REPLACE FUNCTION abc.eng19_")==4
    assert split.rstrip().endswith("COMMIT;")
    assert split.count("\\nCOMMIT;")==1
    assert "CREATE ROLE abc_eng04_worker NOLOGIN NOINHERIT" in split
    assert "CREATE ROLE abc_eng05_worker NOLOGIN NOINHERIT" in split
    assert "CREATE TABLE abc.eng05_worker_bindings" in split
    assert "ALTER TABLE abc.eng05_worker_bindings FORCE ROW LEVEL SECURITY" in split
    assert "REVOKE ALL ON FUNCTION abc.eng19_claim_synthetic(text,integer)" in split
    assert "FROM PUBLIC,abc_pipeline_worker,abc_eng04_worker" in split
    assert "TO abc_eng05_worker" in split
    assert "GRANT SELECT ON abc.eng19_synthetic_jobs" not in split
    assert "GRANT INSERT ON abc.eng19_synthetic_jobs" not in split
    assert "UPDATE abc.eng19_synthetic_outbox SET" not in split
    for source in ("abc.eng03_worker_bindings","abc.worker_login_bindings"):
        assert source not in split
    assert "session_user<>'abc_pipeline_worker'" not in sql
    assert "BLOCKED_PENDING_AUTHORITY" in py
    assert '"LOCAL_INTEGRATION_ONLY"' in py
    assert "SyntheticKnowledgeEngine().resolve" in py
    # The only accepted result cannot claim verified specialist knowledge.
    assert "fixture=None" in py
    assert "release_approved" not in py or "'release_approved':True" not in py
    return {"independent_worker_db_identity":"abc_eng05_worker",
        "source_artifact_kind":"BEAUTY_ANALYSIS_REPORT",
        "result_version":"synthetic-ontology.1",
        "next_engine":"ENG-06","next_outbox":"BLOCKED_PENDING_AUTHORITY",
        "downstream_automatically_dispatched":False,
        "production_execution_approved":False}

if __name__=="__main__":
    print(json.dumps(validate(),sort_keys=True))

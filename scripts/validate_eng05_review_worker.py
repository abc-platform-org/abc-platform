"""Static hard-deny gate for the bounded ENG05 worker and held ENG06 outbox."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SQL=ROOT/"runtime/phase04/migrations/0020_eng05_synthetic_work_queue.sql"
PY=ROOT/"runtime/phase04/abc_foundation/eng05_review_worker.py"

def validate():
    sql=SQL.read_text()
    py=PY.read_text()
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
        "IF session_user<>'abc_pipeline_worker'",
        "p_tenant IS DISTINCT FROM 'tenant-test'",
        "p_branch IS DISTINCT FROM 'branch-test'"
    ):
        assert statement in sql,statement
    assert "abc.eng19_synthetic_outbox" in sql
    assert "downstream_dispatched" in py
    assert "BLOCKED_PENDING_AUTHORITY" in py
    assert '"LOCAL_INTEGRATION_ONLY"' in py
    assert "SyntheticKnowledgeEngine().resolve" in py
    # The only accepted result cannot claim verified specialist knowledge.
    assert "fixture=None" in py
    assert "release_approved" not in py or "'release_approved':True" not in py
    return {"independent_worker_db_identity":"abc_pipeline_worker",
        "source_artifact_kind":"BEAUTY_ANALYSIS_REPORT",
        "result_version":"synthetic-ontology.1",
        "next_engine":"ENG-06","next_outbox":"BLOCKED_PENDING_AUTHORITY",
        "downstream_automatically_dispatched":False,
        "production_execution_approved":False}

if __name__=="__main__":
    print(json.dumps(validate(),sort_keys=True))

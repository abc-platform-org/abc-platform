"""Fail-closed review of ENG04->ENG05 exact-bytes mTLS source bridge.

Only local test dispatch may call this new broker. CI cannot grant security
ratification, provisioning, media intake or real salon decision execution.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SQL=(ROOT/"runtime/phase04/migrations/0024_eng04_eng05_same_artifact_review.sql").read_text()
CONSUMER=(ROOT/"runtime/phase04/abc_foundation/eng19_review_consumer.py").read_text()
TEST=(ROOT/"runtime/phase04/tests/test_eng03_durable_pipeline.py").read_text()
PLAN=(ROOT/"runtime/phase04/abc_foundation/staging_migrate.py").read_text()

def check():
    assert SQL.rstrip().endswith("COMMIT;") and SQL.count("\nCOMMIT;")==1
    for required in (
        "CREATE FUNCTION abc.eng19_submit_verified_eng04(",
        "SECURITY DEFINER","SET search_path=pg_catalog,abc",
        "JOIN abc.eng04_ci_results r ON r.job_id=j.job_id",
        "r.output_sha256=p_artifact_sha AND r.output_bytes=p_source",
        "r.status='BLOCKED_PENDING_AUTHORITY'",
        "j.status='ACKED'",
        "JOIN abc.eng04_ci_worker_bindings b",
        "b.login_name='abc_eng04_ci_login'",
        "v_source_hash IS DISTINCT FROM v_result.source_manifest_sha256",
        "src.status='ACKED'",
        "abc.eng19_record_review_handoff(",
        "INSERT INTO abc.eng19_synthetic_jobs(",
        "ON CONFLICT(handoff_id) DO NOTHING",
        "v_existing.source_bytes IS DISTINCT FROM p_source",
        "TO abc_app",
    ):
        assert required in SQL,required
    for forbidden in (
        "GRANT EXECUTE ON FUNCTION abc.eng19_submit_verified_eng04(",
        "UPDATE abc.eng19_synthetic_outbox",
        "UPDATE abc.eng04_ci_results",
        "CREATE ROLE abc_eng05_worker LOGIN",
        "ALTER TABLE abc.eng19_synthetic_outbox",
    ):
        if forbidden.startswith("GRANT EXECUTE"):
            assert "TO abc_eng04_worker" not in SQL
        else:
            assert forbidden not in SQL
    assert "eng19_submit_verified_eng04" in CONSUMER
    assert "eng19_submit_synthetic" in CONSUMER
    assert "0024_eng04_eng05_same_artifact_review.sql" in PLAN
    for name in (
        "test_eng04_actual_persisted_bytes_to_eng05_tls13_jwt_and_durable_receipt",
        "test_eng04_saved_artifact_jwt_replay_wrong_identity_and_tamper_denied",
        "test_eng04_dest_denies_revoked_consent_or_independent_policy",
        "test_eng04_network_outage_retry_fresh_jwt_no_duplicate_receipt",
    ):
        assert "def "+name in TEST,name
    return {"scope":"LOCAL_INTEGRATION_ONLY","artifact":"BEAUTY_ANALYSIS_REPORT",
            "producer":"ENG-04","receiver":"ENG-05","verified_source":"ENG03+ENG04 ACKED",
            "auto_dispatch":False,"eng05_to_eng06_released":False,
            "release_approved":False}

if __name__=="__main__":
    print(json.dumps(check(),sort_keys=True))

"""Static fail-closed guard for ENG05's verified ENG04 queue consumer.

A green static gate is not a production identity or authority signature.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SQL=(ROOT/"runtime/phase04/migrations/0025_eng05_verified_provenance_consumer.sql").read_text()
WORKER=(ROOT/"runtime/phase04/abc_foundation/eng05_review_worker.py").read_text()
TESTS=(ROOT/"runtime/phase04/tests/test_eng03_durable_pipeline.py").read_text()
PLAN=(ROOT/"runtime/phase04/abc_foundation/staging_migrate.py").read_text()

def check():
    assert SQL.rstrip().endswith("COMMIT;") and SQL.count("\nCOMMIT;")==1
    assert "0025_eng05_verified_provenance_consumer.sql" in PLAN
    assert SQL.count("CREATE OR REPLACE FUNCTION abc.eng19_")==2
    for required in (
        "CREATE TABLE abc.eng05_ci_source_receipts(",
        "FORCE ROW LEVEL SECURITY",
        "CREATE FUNCTION abc.eng05_ci_verify_eng04_source(",
        "r.output_bytes=v_job.source_bytes",
        "r.output_sha256=v_job.source_sha256",
        "j.status='ACKED'",
        "r.status='BLOCKED_PENDING_AUTHORITY'",
        "binding.active",
        "LIMIT 1 FOR SHARE OF j,r,binding",
        "src.status='ACKED'",
        "v_manifest IS DISTINCT FROM v_result.source_manifest_sha256",
        "v_verified:=abc.eng05_ci_verify_eng04_source(j.handoff_id)",
        "'eng04_verified_lineage',v_verified",
        "v_verified:=abc.eng05_ci_verify_eng04_source(j.handoff_id);",
        "v_out->'grounded_facts' IS DISTINCT FROM '[]'::jsonb",
        "v_out->'retrieval_sources' IS DISTINCT FROM '[]'::jsonb",
        "v_out->'unknowns' IS DISTINCT FROM '[\"SOURCE_UNVERIFIED\"]'::jsonb",
        "INSERT INTO abc.eng05_ci_source_receipts(",
        "status='BLOCKED_PENDING_AUTHORITY'",
        "abc.eng19_synthetic_outbox",
        "GRANT EXECUTE ON FUNCTION abc.eng19_claim_synthetic(text,integer) TO abc_eng05_worker",
    ):
        assert required in SQL,required
    assert "GRANT SELECT ON abc.eng05_ci_source_receipts" not in SQL
    assert "GRANT INSERT ON abc.eng05_ci_source_receipts" not in SQL
    assert "UPDATE abc.eng19_synthetic_outbox SET status" not in SQL
    assert "SET LOCAL ROLE abc_eng05_worker" in WORKER
    assert "eng05_verified_eng04_lineage_missing" in WORKER
    assert "eng05_local_identity_isolation_required" in WORKER
    assert "ABC_ENG05_CI_CONSUMER" in WORKER
    assert "eng05_to_eng06_dispatched" in WORKER
    for name in (
      "test_verified_eng05_processes_real_eng04_source_in_separate_os_process",
      "test_eng05_verified_queue_parallel_claim_and_stale_ack_fencing",
      "test_eng05_verified_source_revoke_eng04_identity_blocks_claim_and_ack",
      "test_eng05_verified_source_consent_revoked_after_claim_denies_ack",
      "test_eng05_verified_queue_retries_then_dlq_and_no_eng06_outbox",
      "test_eng05_verified_queue_denies_forged_professional_output_and_cross_role",
    ):
      assert "def "+name in TESTS,name
    return {"scope":"LOCAL_INTEGRATION_ONLY","engine":"ENG-05",
      "input":"ENG04_ACKED_BEAUTY_ANALYSIS_REPORT",
      "evidence":"ENG03_SHA256_MANIFEST",
      "physical_role":"abc_eng05_worker",
      "review_receipt":"IMMUTABLE_BLOCKED_PENDING_AUTHORITY",
      "verified_professional_sources":0,"eng05_to_eng06_dispatched":False,
      "customer_release_approved":False}

if __name__=="__main__":
    print(json.dumps(check(),sort_keys=True))

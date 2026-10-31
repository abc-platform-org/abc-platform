"""Guard ENG04 independent synthetic analysis and review-only ENG05 edge."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SQL=(ROOT/"runtime/phase04/migrations/0023_eng04_independent_evidence_worker.sql").read_text()
WORKER=(ROOT/"runtime/phase04/abc_foundation/eng04_review_worker.py").read_text()
PLAN=(ROOT/"runtime/phase04/abc_foundation/staging_migrate.py").read_text()
GATES=json.loads((ROOT/"governance/abc_w1w2_private_runtime_evidence.v0.review.json").read_text())
SCHEMA=json.loads((ROOT/"governance/abc_eng04_beauty_analysis_report.v0.review.schema.json").read_text())
WORKFLOW=json.loads((ROOT/"governance/abc_workflow_19.v0.review.json").read_text())

def check():
    assert SQL.count("\nCOMMIT;")==1 and SQL.rstrip().endswith("COMMIT;")
    assert all(s in SQL for s in (
        "CREATE TABLE abc.eng04_ci_worker_bindings",
        "CREATE TABLE abc.eng04_ci_jobs","CREATE TABLE abc.eng04_ci_results",
        "FORCE ROW LEVEL SECURITY",
        "CREATE FUNCTION abc.eng04_ci_claim(",
        "CREATE FUNCTION abc.eng04_ci_ack(",
        "CREATE FUNCTION abc.eng04_ci_fail(",
        "CREATE FUNCTION abc.eng04_ci_result_for_review(",
        "session_user='abc_eng04_worker'",
        "FOR UPDATE OF q SKIP LOCKED",
        "j.lease_token IS DISTINCT FROM p_lease",
        "ce.purpose @> ARRAY['AI_PROCESSING','INTERNAL_HANDOFF']::text[]",
        "src.status='ACKED'",
        "pol.decision='ALLOW'",
        "count(DISTINCT e.evidence_json->>'attribute_key')",
        "v_count IS DISTINCT FROM 4",
        "v_hash IS DISTINCT FROM p_manifest",
        "FOR SHARE OF s,ce",
        "BLOCKED_PENDING_AUTHORITY",
        "BEAUTY_ANALYSIS_REPORT",
        "GRANT EXECUTE ON FUNCTION abc.eng04_ci_claim(text,integer) TO abc_eng04_worker",
    ))
    assert "TO abc_pipeline_worker" not in SQL
    assert "GRANT SELECT ON abc.eng03_evidence_ledger TO abc_eng04_worker" not in SQL
    assert "UPDATE abc.eng19_synthetic_outbox" not in SQL
    assert all(s in WORKER for s in (
        "class SyntheticEng04ReviewWorker",
        "SET LOCAL ROLE abc_eng04_worker",
        "hashlib.sha256(canonical_bytes(data)).hexdigest()",
        "eng04_synthetic_analysis_candidate(",
        "ABC_ENV",
        '"dispatch_authorized":False',
        '"downstream_dispatched":False',
    ))
    assert SCHEMA["additionalProperties"] is False
    assert SCHEMA["properties"]["service_scope"]["const"]=="SYNTHETIC_NON_MEDIA_ONLY"
    assert SCHEMA["properties"]["engine_version"]["const"]=="eng04.synthetic-evidence.1"
    assert SCHEMA["properties"]["source_engine"]["const"]=="ENG-03"
    assert SCHEMA["properties"]["professional_validation_verified"]["const"] is False
    assert SCHEMA["properties"]["evidence_ids"]["minItems"]==4
    assert "source_manifest_sha256" in SCHEMA["required"]
    assert "eng04_unverified_report_mutation" in WORKER
    assert "eng04_local_isolation_required" in WORKER
    assert 'if __name__=="__main__":' in WORKER
    assert "ABC_ENG04_CI_CONSUMER" in WORKER
    assert "127.0.0.1" in WORKER
    assert "send_local_review_handoff(" not in WORKER
    assert "0023_eng04_independent_evidence_worker.sql" in PLAN
    assert GATES["eng05_to_eng06_dispatch_enabled"] is False
    assert GATES["customer_release_approved"] is False
    assert any(e["from"]=="ENG-04" and e["to"]=="ENG-05"
               and e["artifact"]=="BEAUTY_ANALYSIS_REPORT"
               for e in WORKFLOW["handoffs"])
    return {"eng04_durable_tables":3,"eng04_broker_functions":4,
            "eng03_source_verified":True,"eng04_to_eng05_auto_dispatch":False,
            "eng05_to_eng06_dispatch":False,"customer_release":False}

if __name__=="__main__":
    print(json.dumps(check(),sort_keys=True))

"""Admission check for isolated ENG06 CI worker; not product release approval."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
SQL=(ROOT/"runtime/phase04/migrations/0021_eng06_synthetic_review_worker.sql").read_text()
PY=(ROOT/"runtime/phase04/abc_foundation/eng06_review_worker.py").read_text()
FLOW=json.loads((ROOT/"governance/abc_workflow_19.v0.review.json").read_text())
GATES=json.loads((ROOT/"governance/abc_w1w2_private_runtime_evidence.v0.review.json").read_text())

def check():
    assert SQL.rstrip().endswith("COMMIT;")
    assert SQL.count("\nCOMMIT;")==1
    assert "CREATE ROLE abc_eng06_review_worker NOLOGIN NOINHERIT" in SQL
    assert SQL.count("CREATE FUNCTION abc.eng06_ci_")==3
    assert "CREATE TABLE abc.eng06_ci_worker_bindings" in SQL
    assert all(x in SQL for x in (
        "ENABLE ROW LEVEL SECURITY","FORCE ROW LEVEL SECURITY",
        "session_user='abc_eng06_review_worker'",
        "b.login_name=session_user","b.consumer_id=j.consumer_id",
        "b.tenant_id=j.tenant_id AND b.active",
        "FOR UPDATE OF job SKIP LOCKED",
        "j.lease_token IS DISTINCT FROM p_lease",
        "FOR SHARE OF s,ce",
        "ce.purpose @> ARRAY['AI_PROCESSING','INTERNAL_HANDOFF']::text[]",
        "encode(sha256(r.output_bytes),'hex')=r.output_sha256",
        "o.status='BLOCKED_PENDING_AUTHORITY'",
        "BLOCKED_PROFESSIONAL_SOURCE",
        "v->>'customer_release_approved' IS DISTINCT FROM 'false'",
        "v->'decision'->'candidates' IS DISTINCT FROM '[]'::jsonb",
    ))
    assert "GRANT EXECUTE ON FUNCTION abc.eng06_ci_ack" in SQL
    assert "GRANT INSERT ON" not in SQL
    assert "UPDATE abc.eng19_synthetic_outbox" not in SQL
    assert "INSERT INTO abc.eng19_synthetic_outbox" not in SQL
    assert all(x in PY for x in (
        'ABC_ENV")!="LOCAL_INTEGRATION_ONLY"',
        "SET LOCAL ROLE abc_eng06_review_worker",
        "SyntheticDecisionEngine().decide(",
        "SOURCE_UNVERIFIED","BLOCKED_PROFESSIONAL_SOURCE",
        '"downstream_dispatched":False',
        '"customer_release_approved":False'
    ))
    assert "send_local_review_handoff(" not in PY
    assert "dispatch(" not in PY
    assert "JOIN abc.eng19_synthetic_outbox o" in SQL
    assert any(e["from"]=="ENG-05" and e["to"]=="ENG-06"
               and e["artifact"]=="PROFESSIONAL_KNOWLEDGE_BUNDLE"
               and e["status"]=="SPEC_ONLY_UNWIRED"
               for e in FLOW["handoffs"])
    assert GATES["eng05_to_eng06_dispatch_enabled"] is False
    assert GATES["new_v3_runtime_enabled"] is False
    assert GATES["customer_release_approved"] is False
    return {"eng06_ci_worker_functions":3,"durable_review_tables":3,
            "eng05_outbox_mutated":False,"live_v3_dispatch":False,
            "eng07_output":False,"production_approved":False}

if __name__=="__main__":
    print(json.dumps(check(),sort_keys=True))

"""Check exact 19-engine database review edge list matches canonical graph.

Static-only: checks source artifact owners and DB safety declarations.
Runtime permissions, consents and TLS are separately checked in real PG CI.
"""
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GRAPH=ROOT/"governance/abc_workflow_19.v0.review.json"
MIGRATION=ROOT/"runtime/phase04/migrations/0019_eng19_review_inbox.sql"
EDGE=re.compile(r"\('ENG-([0-9]{2})','ENG-([0-9]{2})','([A-Z0-9_]+)'\)")

def validate():
    graph=json.loads(GRAPH.read_text())
    sql=MIGRATION.read_text()
    actual=[("ENG-"+a,"ENG-"+b,artifact) for a,b,artifact in EDGE.findall(sql)]
    expected=[(e["from"],e["to"],e["artifact"]) for e in graph["handoffs"]]
    assert len(actual)==16 and actual==expected
    for fragment in (
        "ALTER TABLE abc.eng19_review_inbox FORCE ROW LEVEL SECURITY",
        "GRANT EXECUTE ON FUNCTION abc.eng19_record_review_handoff",
        "abc.eng14_workload_allowed(p_tenant)",
        "ce.status='ACTIVE'",
        "ce.revoked_at IS NULL",
        "ce.valid_until>clock_timestamp()",
        "ce.purpose @> ARRAY['AI_PROCESSING','INTERNAL_HANDOFF']",
        "FOR SHARE OF s,ce",
        "s.state_version=p_version",
        "ON CONFLICT (handoff_id) DO NOTHING"
    ):
        assert fragment in sql,fragment
    assert graph["environment"]=="SPEC_ONLY_NO_CUSTOMER_EXECUTION"
    assert graph["flow_complete"] is False
    return {"approved_static_edges":16,"review_only":True,
            "real_service_execution_authorized":False}

if __name__=="__main__":
    print(json.dumps(validate(),sort_keys=True))

"""Reproducible, conservative engine audit evidence inventory.

Evidence is inventory only: no gate is promoted without independent sign-off.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GOV=ROOT/"governance"
MOD=ROOT/"runtime/phase04/abc_foundation"
TEST=ROOT/"runtime/phase04/tests"
FOCUS={f"ENG-{i:02d}" for i in (1,2,3,4,5,6,14)}
LEGACY={
    "eng04_recommendation_v2.py":"ENG-04→ENG-06/07 (legacy draft)",
    "eng05_decision_v2.py":"ENG-05→ENG-06 (legacy draft)",
    "eng06_technical_plan_v2.py":"ENG-06→ENG-15 (legacy draft)",
    "eng04_visual_qa.py":"ENG-04→ENG-11 (embedded)",
    "eng19_review_consumer.py":"REVIEW_TRANSPORT (not canonical ENG-19)",
    "eng19_review_producer.py":"REVIEW_TRANSPORT (not canonical ENG-19)",
    "eng19_review_transport.py":"REVIEW_TRANSPORT (not canonical ENG-19)",
}
def read(name):
    return json.loads((GOV/name).read_text(encoding="utf-8"))

def build():
    registry=read("abc_engine_registry_19.v0.review.json")
    matrix=read("abc_engine_quality_19.v0.review.json")
    quality=read("engine_quality_policy.v1.json")
    gates=[g["id"] for g in quality["mandatory_gates"]]
    rows=[]
    for e in registry["engines"]:
        engine=e["engine_id"]
        key=engine.lower().replace("-","")
        modules=sorted(p.name for p in MOD.glob(key+"*.py"))
        tests=sorted(p.name for p in TEST.glob("test_"+key+"*.py"))
        gate_row=next(q for q in matrix["engines"] if q["engine_id"]==engine)
        assert list(gate_row["gate_status"])==gates
        assert all(v=="OPEN" for v in gate_row["gate_status"].values())
        assert not gate_row["completion_signed"]
        rows.append({
            "engine_id":engine,
            "canonical_owner":e["logical_owner_key"],
            "baseline_scope":e["observed_scope"],
            "canonical_implementation_module":e["implementation_module"],
            "discovered_prefix_modules":modules,
            "discovered_prefix_tests":tests,
            "audit_priority":"ACTIVE_FOUNDATION" if engine in FOCUS else "CANONICAL_CONTRACT_ONLY",
            "gate_status":gate_row["gate_status"],
            "independent_deployment_verified":False,
            "professional_validation_verified":False,
            "operational_completion_claim":False
        })
    collisions=[{"module":p,"legacy_mapping":label,"exists":(MOD/p).is_file()}
                for p,label in sorted(LEGACY.items())]
    assert all(q["exists"] for q in collisions)
    assert len(rows)==19
    assert len({q["engine_id"] for q in rows})==19
    assert sum(len(q["gate_status"]) for q in rows)==190
    return {
        "schema_version":"abc.engine-evidence-inventory.v1",
        "source":"repository tree + unsigned governance baseline",
        "limitations":"Filename-prefix discovery is not a semantic code audit; tests listed are not proof of independent deployment or domain acceptance.",
        "focus_engines":sorted(FOCUS),
        "canonical_protocol_executable":False,
        "release_authorized":False,
        "engine_count":19,
        "open_gate_count":190,
        "legacy_namespace_collisions":collisions,
        "engines":rows
    }

if __name__=="__main__":
    print(json.dumps(build(),ensure_ascii=False,sort_keys=True,indent=2))

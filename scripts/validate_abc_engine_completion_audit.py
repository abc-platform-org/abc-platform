"""Audit gate: fail closed on canonical engine ownership, workflow and namespace drift.

No claim of runtime completion or professional approval is made by this check.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GOV=ROOT/"governance"
SRC=ROOT/"runtime/phase04/abc_foundation"
VERSION="abc.internal.capability.v3.review"
LEGACY={
    "eng06_technical_plan_v2.py":("ENG-06","ENG-15","TECHNICAL_PLANNING_INTELLIGENCE"),
    "eng19_review_consumer.py":("ENG-19",None,"REVIEW_TRANSPORT_NOT_CANONICAL_AUTOMATION"),
    "eng19_review_producer.py":("ENG-19",None,"REVIEW_TRANSPORT_NOT_CANONICAL_AUTOMATION"),
    "eng19_review_transport.py":("ENG-19",None,"REVIEW_TRANSPORT_NOT_CANONICAL_AUTOMATION"),
}

def load(name):
    return json.loads((GOV/name).read_text(encoding="utf-8"))

def validate():
    registry=load("abc_engine_registry_19.v0.review.json")
    graph=load("abc_workflow_19.v0.review.json")
    adapters=load("abc_v2_to_19_adapters.v0.review.json")
    quality=load("abc_engine_quality_19.v0.review.json")
    assert registry["decision_status"]=="PROPOSED_FOR_ARCHITECTURE_OWNER_REVIEW"
    assert registry["future_protocol_executable"] is False
    assert registry["customer_release_approved"] is False
    engines={e["engine_id"]:e for e in registry["engines"]}
    assert set(engines)=={f"ENG-{i:02d}" for i in range(1,20)}
    assert engines["ENG-06"]["logical_owner_key"]=="DECISION_RECOMMENDATION"
    assert engines["ENG-15"]["logical_owner_key"]=="TECHNICAL_PLANNING"
    assert engines["ENG-19"]["logical_owner_key"]=="OPPORTUNITY_AUTOMATION"
    assert graph["contract_version"]==VERSION
    assert graph["flow_complete"] is False
    assert graph["private_network_e2e_complete"] is False
    assert all(s["execution_status"]=="CONTRACT_ONLY_NOT_LIVE" and
               s["runtime_authorized"] is False for s in graph["ordered_stages"])
    assert len(graph["ordered_stages"])==17
    assert all(g["verification_status"]=="UNPROVISIONED" and
               g["skip_allowed"] is False for g in graph["required_policy_gates"])
    assert len(graph["required_policy_gates"])==7
    assert len(adapters["adapters"])==6
    assert adapters["live_dispatch_enabled"] is False
    assert adapters["customer_release_approved"] is False
    assert all(a["migration_status"]=="UNMIGRATED" and
               a["runtime_enabled"] is False for a in adapters["adapters"])
    assert quality["completion_count"]==0 and quality["open_gate_count"]==190
    assert all(e["completion_signed"] is False for e in quality["engines"])
    assert all((SRC/name).is_file() for name in LEGACY)
    assert any(a["adapter_id"]=="A06_TO_15_PLAN_CANDIDATE" and
               a["source_engine"]=="ENG-06" and a["target_engine"]=="ENG-15"
               for a in adapters["adapters"])
    # ENG19 is a canonical automation owner, never a synonym for the review transport.
    assert engines["ENG-19"]["implementation_module"] is None
    assert engines["ENG-07"]["implementation_module"] is None
    return {"canonical_engines":19,"workflow_stages":17,
            "unprovisioned_policy_gates":7,"unmigrated_adapters":6,
            "legacy_namespace_collisions":len(LEGACY),
            "open_quality_gates":190,"canonical_eng07_implemented":False,
            "customer_release_approved":False}

if __name__=="__main__":
    print(json.dumps(validate(),sort_keys=True))

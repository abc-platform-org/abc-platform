"""Fail closed: no engine may claim completion on self-authored evidence."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
POLICY=ROOT/"governance/engine_quality_policy.v1.json"
REGISTRY=ROOT/"governance/engine_quality_registry.v1.json"
EXPECTED={f"ENG-{i:02d}" for i in range(1,7)}|{"ENG-14"}
GATE_IDS=(
    "G01_ARCHITECTURE","G02_DOMAIN_CAPABILITY","G03_CONTRACTS",
    "G04_INDEPENDENCE","G05_SECURITY_PRIVACY","G06_RELIABILITY",
    "G07_PERFORMANCE","G08_PROFESSIONAL_VALIDATION",
    "G09_OBSERVABILITY_OPERATIONS","G10_INDEPENDENT_SIGNOFF"
)
ACCEPTED_MATURITY={
    "FOUNDATION_CI_TESTED","SYNTHETIC_PROCESS_CI_TESTED",
    "POLICY_FOUNDATION_CI_TESTED"
}


def verify(policy,registry):
    assert policy["schema_version"]=="abc.engine-quality-gates.v1"
    assert policy["scope"]=="IN_SALON_SHARED_SCREEN"
    assert policy["release_separate_from_engine_complete"] is True
    assert tuple(g["id"] for g in policy["mandatory_gates"])==GATE_IDS
    assert len(set(GATE_IDS))==10
    assert set(policy["required_roles"])=={
        "ENGINE_AUDITOR","PROFESSIONAL","SECURITY"
    }
    assert all(len(g["acceptance"])>=3 and len(g["evidence"])>=3
               for g in policy["mandatory_gates"])
    assert registry["schema_version"]=="abc.engine-quality-registry.v1"
    assert registry["mandatory_gate_policy"]=="governance/engine_quality_policy.v1.json"
    assert registry["engine_count"]==7
    assert registry["stage"]=="PHASE04_FOUNDATION_AND_PRIVATE_SECURITY_IN_PROGRESS"
    engines=registry["engines"]
    assert len(engines)==7 and {e["id"] for e in engines}==EXPECTED
    for e in engines:
        assert e["target_service_scope"]==policy["scope"]
        assert e["observed_maturity"] in ACCEPTED_MATURITY
        assert e["current_state"]=="IN_PROGRESS"
        assert e["completion_claim"] is False
        assert e["real_customer_ready"] is False
        assert e["gate_evidence"]=={}
        assert len(e["critical_blockers"])>=3
        assert len(e["implemented_and_tested_scope"])>=3
        assert e["id"] in e["target_architecture_role"]
    assert "CUSTOMER_RELEASE_APPROVED" in registry["prohibited_aggregate_claims"]
    return {"engine_count":7,"mandatory_gates_per_engine":10,
            "open_engine_gate_slots":70,"complete":0,
            "status":"EVIDENCE_INCOMPLETE",
            "product_release_approved":False}


def main():
    result=verify(json.loads(POLICY.read_text()),
                  json.loads(REGISTRY.read_text()))
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()

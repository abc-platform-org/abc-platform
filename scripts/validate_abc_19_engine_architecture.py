"""Static architectural admission for 19 logical engines, not a deployed workflow.

Verifies one canonical owner per capability and prevents an in-place v2->19
semantic promotion or fabricated engine completion. All gates remain open.
"""
import json
from pathlib import Path
from jsonschema import Draft202012Validator,FormatChecker

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=ROOT/"governance/abc_engine_registry_19.v0.review.json"
WORKFLOW=ROOT/"governance/abc_workflow_19.v0.review.json"
HANDOFF_SCHEMA=ROOT/"contracts/review/engine19_handoff.v0.schema.json"
QUALITY=ROOT/"governance/engine_quality_policy.v1.json"
GATE_MATRIX=ROOT/"governance/abc_engine_quality_19.v0.review.json"
CORE_19=[f"ENG-{n:02d}" for n in range(1,20)]
FOUNDATION={f"ENG-{n:02d}" for n in (1,2,3,4,5,6,14)}
FLOW=[f"ENG-{n:02d}" for n in (2,3,4,5,6,7,8,9,10,11,12,13,15,16,17,18,19)]
EXTERNAL_GATE_ENGINES={
    "GATE_P0_CONSENT":"ENG-03",
    "GATE_P1_VISUAL":"ENG-08",
    "GATE_P2_DECISION":"ENG-06",
    "GATE_P3_SELECTED_LOOK_LOCK":"ENG-13",
    "GATE_P4_TECHNICAL_SOP":"ENG-15",
    "GATE_P5_OPERATIONAL_HANDOFF":"ENG-17",
    "GATE_P6_BUSINESS_AUTOMATION":"ENG-19"
}
VERSION="abc.internal.capability.v3.review"


def load():
    return (json.loads(REGISTRY.read_text()),json.loads(WORKFLOW.read_text()),
            json.loads(HANDOFF_SCHEMA.read_text()),
            json.loads(QUALITY.read_text()),json.loads(GATE_MATRIX.read_text()))


def validate(registry,graph,handoff,quality,gate_matrix):
    assert registry["schema_version"]=="abc.canonical-19-engine-registry.v0.review"
    assert registry["decision_status"]=="PROPOSED_FOR_ARCHITECTURE_OWNER_REVIEW"
    assert registry["architecture_authority"]=="ADR-ENG-003_PROPOSED"
    assert registry["product_scope"]=="IN_SALON_SHARED_SCREEN"
    assert registry["future_canonical_protocol"]==VERSION
    assert registry["future_protocol_executable"] is False
    assert registry["frozen_legacy_api"]=="abc.internal.engine.synthetic.v1"
    assert registry["frozen_v2_draft_api"]=="abc.internal.engine.v2.draft"
    assert registry["operational_engines_complete"]==0
    assert registry["customer_release_approved"] is False
    entries=registry["engines"]
    assert len(entries)==19
    assert [e["engine_id"] for e in entries]==CORE_19
    assert len({e["logical_owner_key"] for e in entries})==19
    assert len({e["canonical_output"] for e in entries})==19
    required_gates=[g["id"] for g in quality["mandatory_gates"]]
    assert len(required_gates)==10
    assert registry["mandatory_gates"]==required_gates
    assert gate_matrix["schema_version"]=="abc.engine19-gate-matrix.v0.review"
    assert gate_matrix["decision_status"]=="UNSIGNED_BASELINE_NO_COMPLETIONS"
    assert gate_matrix["scope"]=="IN_SALON_SHARED_SCREEN"
    assert gate_matrix["gate_policy"]=="governance/engine_quality_policy.v1.json"
    assert gate_matrix["required_gates"]==required_gates
    assert gate_matrix["completion_count"]==0
    assert gate_matrix["open_gate_count"]==190
    assert gate_matrix["independent_attestation_issuer_provisioned"] is False
    assert gate_matrix["customer_release_approved"] is False
    assert len(gate_matrix["engines"])==19
    assert [r["engine_id"] for r in gate_matrix["engines"]]==CORE_19
    total_open=0
    for r in gate_matrix["engines"]:
        assert list(r["gate_status"])==required_gates
        assert all(s=="OPEN" for s in r["gate_status"].values())
        assert r["evidence_refs"]=={}
        assert r["signed_reviews"]=={}
        assert r["completion_signed"] is False
        total_open+=len(r["gate_status"])
    assert total_open==190
    for e in entries:
        id=e["engine_id"]
        expected="IN_PROGRESS" if id in FOUNDATION else "NOT_INDEPENDENTLY_IMPLEMENTED"
        assert e["completion_status"]==expected
        assert e["observed_scope"] in (
            "BOUNDED_CI","NOT_INDEPENDENT",
            "EMBEDDED_SUBCAPABILITY_ONLY","PROTOTYPE_ONLY")
        assert e["port_status"]=="CANONICAL_TARGET_CONTRACT_CANDIDATE_NOT_DEPLOYED"
        assert e["ten_gate_evidence"]=={}
        assert e["independent_deployment_verified"] is False
        assert e["qualified_domain_validation"] is False
        assert e["customer_processing_authorized"] is False
        if e["implementation_module"] is not None:
            module=ROOT/"runtime/phase04/abc_foundation"/e["implementation_module"]
            assert module.is_file(),("missing_impl_evidence",id,module)

    # Keep the historical seven-engine quality registry as a true subset,
    # not a second competing authority for the target 19 logical owners.
    previous=json.loads((ROOT/"governance/engine_quality_registry.v1.json").read_text())
    assert previous["engine_count"]==7
    previous_ids={e["id"] for e in previous["engines"]}
    assert previous_ids==FOUNDATION
    assert all(e["current_state"]=="IN_PROGRESS" and
               e["completion_claim"] is False and
               e["real_customer_ready"] is False for e in previous["engines"])
    aliases=registry["legacy_compatibility"]
    assert len(aliases)==6
    assert aliases[0]["policy"]=="IMMUTABLE_NO_IMPLICIT_PROMOTION"
    expected_aliases={
        ("ENG-04","RECOMMENDATION_INTELLIGENCE"):["ENG-06","ENG-07"],
        ("ENG-05","DECISION_INTELLIGENCE"):["ENG-06"],
        ("ENG-06","TECHNICAL_PLANNING_INTELLIGENCE"):["ENG-15"],
        ("ENG-04","EMBEDDED_PIXEL_QA"):["ENG-11"],
        ("ENG-06","PROFESSIONAL_SOURCE_SIGNATURE_PRIMITIVE"):["ENG-16"]
    }
    seen=set()
    for adapter in aliases[1:]:
        pair=(adapter["source_engine"],adapter["source_role"])
        assert pair in expected_aliases and pair not in seen
        seen.add(pair)
        assert adapter["canonical_capability_owners"]==expected_aliases[pair]
        assert adapter["status"]=="UNMIGRATED"
        assert adapter["compatibility_strategy"] in (
            "EXPLICIT_REVIEWED_PORT_ADAPTER_ONLY",
            "EXPLICIT_REVIEWED_ENG11_ADAPTER_ONLY",
            "INDEPENDENT_SPECIALIST_AUTHORITY_REQUIRED")
    assert seen==set(expected_aliases)
    portroot=ROOT/"runtime/phase04/abc_foundation/engine_v2"
    for id,filename,role in (
        ("ENG-04","eng04.recommendation.v2.json","RECOMMENDATION_INTELLIGENCE"),
        ("ENG-05","eng05.decision.v2.json","DECISION_INTELLIGENCE"),
        ("ENG-06","eng06.technical-plan.v2.json","TECHNICAL_PLANNING_INTELLIGENCE")):
        port=json.loads((portroot/filename).read_text())
        assert port["engine_id"]==id and port["role"]==role
        assert port["status"]=="CONTRACT_DRAFT_NO_RUNTIME_RELEASE"

    assert graph["schema_version"]=="abc.workflow19.v0.review"
    assert graph["decision_status"]=="PROPOSED_FOR_ARCHITECTURE_OWNER_REVIEW"
    assert graph["contract_version"]==VERSION
    assert graph["environment"]=="SPEC_ONLY_NO_CUSTOMER_EXECUTION"
    assert graph["entry"]=="ENG-02" and graph["core_final"]=="ENG-17"
    assert graph["logical_orchestrator"]=="ENG-01"
    assert graph["independent_policy_owner"]=="ENG-14"
    assert graph["optional_downstream"]==["ENG-18","ENG-19"]
    assert graph["product_scope"]=="IN_SALON_SHARED_SCREEN"
    assert graph["flow_complete"] is False
    assert graph["professional_validation_complete"] is False
    assert graph["private_network_e2e_complete"] is False
    stages=graph["ordered_stages"]
    assert len(stages)==17
    assert [s["owner_engine"] for s in stages]==FLOW
    assert sorted(set(s["owner_engine"] for s in stages)|{"ENG-01","ENG-14"})==CORE_19
    artifacts={e["engine_id"]:e["canonical_output"] for e in entries}
    for idx,s in enumerate(stages):
        assert s["stage_id"]==f"S{idx+1:02d}"
        assert s["input_from"]==([] if idx==0 else [FLOW[idx-1]])
        assert s["output_artifact"]==artifacts[FLOW[idx]]
        assert s["version"]==VERSION
        assert s["runtime_authorized"] is False
        assert s["customer_media_allowed"] is False
        assert s["execution_status"]=="CONTRACT_ONLY_NOT_LIVE"
        assert s["mode"]==("CORE_IN_SALON_FLOW" if idx<15
                          else "OPTIONAL_ASYNC_BUSINESS_DOWNSTREAM")
    edges=graph["handoffs"]
    assert len(edges)==len(FLOW)-1
    assert len({(e["from"],e["to"]) for e in edges})==len(edges)
    for i,edge in enumerate(edges):
        assert edge["from"]==FLOW[i] and edge["to"]==FLOW[i+1]
        assert edge["artifact"]==artifacts[FLOW[i]]
        assert edge["contract_version"]==VERSION
        assert edge["status"]=="SPEC_ONLY_UNWIRED"
        assert edge["scope_keys"]==[
            "tenant_id","branch_id","session_id",
            "state_version","correlation_id"]
        assert edge["required_guards"]==[
            "VALIDATED_PROVENANCE","SIGNED_SERVICE_PRINCIPAL",
            "TENANT_SESSION_SCOPE","ENG14_POLICY_IF_APPLICABLE"]
    gates=graph["required_policy_gates"]
    assert len(gates)==len(EXTERNAL_GATE_ENGINES)
    assert {g["gate_id"] for g in gates}==set(EXTERNAL_GATE_ENGINES)
    for g in gates:
        assert g["before_engine"]==EXTERNAL_GATE_ENGINES[g["gate_id"]]
        assert g["authority_engine"] in ("ENG-01","ENG-14")
        assert g["verification_status"]=="UNPROVISIONED"
        assert g["skip_allowed"] is False
        assert len(g["requires"])>25
    for s in stages:
        assert s["requires_gates"]==[
            g["gate_id"] for g in gates if g["before_engine"]==s["owner_engine"]]
    for ex in graph["exception_routes"]:
        assert ex["status"]!="LIVE"
        assert ex["status"] in (
            "NOT_IMPLEMENTED_FOR_FULL_SCOPE",
            "PARTIAL_SYNTHETIC_CI_ONLY",
            "PROPOSED_NOT_EXECUTABLE")
    assert "NO_AUTOMATIC_TREATMENT_EXECUTION" in graph["global_controls"]
    assert "CONSENT_REVOKE_CANCELS_DOWNSTREAM" in graph["global_controls"]
    assert "NO_IMPLICIT_V1_V2_TO_V3_ROUTING" in graph["global_controls"]

    Draft202012Validator.check_schema(handoff)
    assert handoff["$id"]=="abc://contracts/engine19/handoff.v0.review"
    assert handoff["additionalProperties"] is False
    fields=handoff["properties"]
    assert fields["contract_version"]=={"const":VERSION}
    assert fields["execution_authorized"]=={"const":False}
    assert fields["customer_release_approved"]=={"const":False}
    assert fields["status"]=={"const":"CANDIDATE_FOR_EXTERNAL_AUTHORIZATION"}
    assert {"tenant_id","branch_id","session_id","state_version",
            "correlation_id","artifact_sha256","policy_proof_ref"}<=set(handoff["required"])
    return {"canonical_engines":19,"core_stages":15,"optional_stages":2,
        "proposed_handoffs":16,"external_gates":7,"legacy_port_adapters_unmigrated":5,
        "engine_complete":0,"open_engine_quality_gates":190,"runtime_dispatch_authorized":False,
        "customer_release_approved":False}


if __name__=="__main__":
    print(json.dumps(validate(*load()),sort_keys=True))

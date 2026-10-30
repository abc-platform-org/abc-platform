"""W0 candidate integrity gate. This is NOT an architecture approval."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "governance/abc_w0_ratification_manifest.v0.review.json"
PORTS = "governance/abc_w0_engine_interfaces.v0.review.json"
REGISTRY = "governance/abc_engine_registry_19.v0.review.json"
FLOW = "governance/abc_workflow_19.v0.review.json"
ADAPTERS = "governance/abc_v2_to_19_adapters.v0.review.json"
QUALITY = "governance/abc_engine_quality_19.v0.review.json"
HANDOFF = "contracts/review/engine19_handoff.v0.schema.json"

EXPECTED_FLOW = [
    "ENG-02","ENG-03","ENG-04","ENG-05","ENG-06","ENG-07",
    "ENG-08","ENG-09","ENG-10","ENG-11","ENG-12","ENG-13",
    "ENG-15","ENG-16","ENG-17","ENG-18","ENG-19",
]
EXPECTED_GATE_OWNERS = {
    "GATE_P0_CONSENT":("ENG-03","ENG-14"),
    "GATE_P1_VISUAL":("ENG-08","ENG-14"),
    "GATE_P2_DECISION":("ENG-06","ENG-14"),
    "GATE_P3_SELECTED_LOOK_LOCK":("ENG-13","ENG-01"),
    "GATE_P4_TECHNICAL_SOP":("ENG-15","ENG-14"),
    "GATE_P5_OPERATIONAL_HANDOFF":("ENG-17","ENG-14"),
    "GATE_P6_BUSINESS_AUTOMATION":("ENG-19","ENG-14"),
}
EXPECTED_ADAPTERS = {
    ("A04_TO_06_DECISION_INPUT","ENG-04","ENG-06"),
    ("A04_TO_07_LOOK_SPEC_INPUT","ENG-04","ENG-07"),
    ("A05_TO_06_DECISION_EVIDENCE","ENG-05","ENG-06"),
    ("A06_TO_15_PLAN_CANDIDATE","ENG-06","ENG-15"),
    ("A04_PIXEL_TO_11_QA_EVIDENCE","ENG-04","ENG-11"),
    ("A06_SOURCE_TO_16_REVIEW_EVIDENCE","ENG-06","ENG-16"),
}
SCOPE = ["tenant_id","branch_id","session_id","state_version","correlation_id"]
APPROVERS = {"ARCHITECTURE_OWNER","SECURITY_REVIEWER","PROFESSIONAL_LEAD","PLATFORM_SRE"}

def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def need(condition, reason):
    if not condition:
        raise ValueError("W0_REJECTED:" + reason)

def inspect(manifest, ports, registry, graph, adapters, quality, handoff):
    need(manifest["schema_version"] == "abc.w0-ratification-manifest.v0.review", "manifest_version")
    need(manifest["status"] == "PENDING_INDEPENDENT_REVIEWS", "ratification_status")
    for key in ("design_freeze_approved","live_routing_allowed","customer_release_approved"):
        need(manifest.get(key) is False, "unsafe_manifest_" + key)
    need(manifest["source_commit"] == "3c4f978288d412ddb44f010a4162a35ad3a9ba1a",
         "unreviewed_starting_commit")
    expected = {"engines":19,"stages":17,"edges":16,"gates":7,
                "adapters":6,"open_quality_gates":190}
    need(manifest["expected"] == expected, "count_contract_drift")
    need({p["role"] for p in manifest["approval_slots"]} == APPROVERS
         and len(manifest["approval_slots"]) == 4, "reviewer_role_drift")
    need(all(p["state"] == "PENDING" and p["review_ref"] is None
             for p in manifest["approval_slots"]), "fabricated_ratification")
    need(set(manifest["artifacts"]) == {
         REGISTRY,FLOW,ADAPTERS,PORTS,HANDOFF,QUALITY
    }, "manifest_artifact_inventory")
    for path in manifest["artifacts"]:
        need((ROOT / path).is_file(), "missing_" + path)
    need("LIVE_V3_ROUTING" in manifest["blocked_actions"] and
         "CUSTOMER_RELEASE" in manifest["blocked_actions"] and
         "AUTOMATED_TREATMENT" in manifest["blocked_actions"],
         "missing_prohibited_action")

    need(registry["decision_status"] == "PROPOSED_FOR_ARCHITECTURE_OWNER_REVIEW"
         and registry["future_protocol_executable"] is False
         and registry["customer_release_approved"] is False,
         "unsigned_canonical_registry")
    need(registry["frozen_legacy_api"] == "abc.internal.engine.synthetic.v1"
         and registry["frozen_v2_draft_api"] == "abc.internal.engine.v2.draft",
         "frozen_legacy_abi_changed")
    version = registry["future_canonical_protocol"]
    need(version == "abc.internal.capability.v3.review", "candidate_promoted")
    by_id = {e["engine_id"]:e for e in registry["engines"]}
    ids = [f"ENG-{i:02d}" for i in range(1,20)]
    need(list(by_id) == ids and len(registry["engines"]) == 19, "engine_id_collision")
    need(len({e["logical_owner_key"] for e in by_id.values()}) == 19
         and len({e["canonical_output"] for e in by_id.values()}) == 19,
         "duplicate_capability_owner")
    need(registry["operational_engines_complete"] == 0, "false_complete")

    need(ports["schema_version"] == "abc.w0-engine-interface-matrix.v0.review"
         and ports["status"] == "CANDIDATE_NOT_RATIFIED"
         and ports["execution_authorized"] is False
         and ports["customer_release_approved"] is False,
         "unsafe_interface_matrix")
    need([p["engine_id"] for p in ports["interfaces"]] == ids, "port_owner_drift")
    need(ports["source_of_truth"] == {
         "registry":REGISTRY,"workflow":FLOW,"adapters":ADAPTERS},
         "port_source_conflict")

    need(graph["decision_status"] == "PROPOSED_FOR_ARCHITECTURE_OWNER_REVIEW"
         and graph["environment"] == "SPEC_ONLY_NO_CUSTOMER_EXECUTION"
         and graph["contract_version"] == version
         and graph["logical_orchestrator"] == "ENG-01"
         and graph["independent_policy_owner"] == "ENG-14"
         and graph["product_scope"] == "IN_SALON_SHARED_SCREEN",
         "workflow_authority_drift")
    need(graph["flow_complete"] is False
         and graph["professional_validation_complete"] is False
         and graph["private_network_e2e_complete"] is False,
         "false_workflow_complete")
    stages = graph["ordered_stages"]
    edges = graph["handoffs"]
    need([s["owner_engine"] for s in stages] == EXPECTED_FLOW
         and len(stages) == 17 and len(edges) == 16, "workflow_stage_drift")
    need(graph["optional_downstream"] == ["ENG-18","ENG-19"]
         and graph["core_final"] == "ENG-17", "business_coupling")
    actual_gates = {g["gate_id"]:(g["before_engine"],g["authority_engine"])
                    for g in graph["required_policy_gates"]}
    need(actual_gates == EXPECTED_GATE_OWNERS
         and len(graph["required_policy_gates"]) == 7,
         "policy_gate_position_or_authority")
    need(all(g["skip_allowed"] is False and g["verification_status"] == "UNPROVISIONED"
             for g in graph["required_policy_gates"]), "forged_policy_gate")
    for n,stage in enumerate(stages):
        source = EXPECTED_FLOW[n-1] if n else None
        need(stage["input_from"] == ([source] if source else [])
             and stage["execution_status"] == "CONTRACT_ONLY_NOT_LIVE"
             and stage["runtime_authorized"] is False
             and stage["customer_media_allowed"] is False, "stage_unlocked")
        need(stage["requires_gates"] ==
             [g["gate_id"] for g in graph["required_policy_gates"]
              if g["before_engine"] == stage["owner_engine"]], "gate_not_applied")
    need(all(x["status"] != "LIVE" for x in graph["exception_routes"]),
         "exception_unauthorized")
    for i,edge in enumerate(edges):
        upstream,downstream = EXPECTED_FLOW[i:i+2]
        need((edge["from"],edge["to"],edge["artifact"]) ==
             (upstream,downstream,by_id[upstream]["canonical_output"]),
             "handoff_ownership_drift")
        need(edge["contract_version"] == version
             and edge["scope_keys"] == SCOPE
             and edge["status"] == "SPEC_ONLY_UNWIRED"
             and edge["required_guards"] == [
                 "VALIDATED_PROVENANCE","SIGNED_SERVICE_PRINCIPAL",
                 "TENANT_SESSION_SCOPE","ENG14_POLICY_IF_APPLICABLE"
             ], "untrusted_handoff")

    for p in ports["interfaces"]:
        engine = p["engine_id"]
        source = by_id[engine]
        inbound = [e for e in edges if e["to"] == engine]
        outbound = [e for e in edges if e["from"] == engine]
        cross = engine in ("ENG-01","ENG-14")
        need(p["capability_owner_key"] == source["logical_owner_key"]
             and p["name"] == source["name"]
             and p["output_artifact"] == source["canonical_output"],
             "port_source_mismatch_" + engine)
        need(p["port_kind"] == ("CONTROL_PLANE" if cross else "DATA_PLANE"),
             "port_plane_mismatch_" + engine)
        need(p["upstream_engines"] == [e["from"] for e in inbound]
             and p["downstream_engines"] == [e["to"] for e in outbound],
             "port_edge_drift_" + engine)
        if cross:
            need(p["input_artifacts"] == (
                ["AUTHORIZED_SESSION_COMMAND","ENGINE_EXECUTION_RECEIPT",
                 "POLICY_DECISION_REFERENCE"] if engine == "ENG-01" else
                ["POLICY_EVALUATION_REQUEST","ACTIVE_CONSENT_EVIDENCE",
                 "QUALIFICATION_ATTESTATION_REFERENCE"]),
                 "crosscutting_port_drift_" + engine)
            need(p["required_dependencies"] == (
                 ["ENG-14"] if engine == "ENG-01" else []),
                 "crosscutting_dep_drift_" + engine)
        else:
            deps = list(dict.fromkeys(["ENG-01","ENG-14"] +
                                      [x["from"] for x in inbound]))
            need(p["input_artifacts"] == [
                by_id[e["from"]]["canonical_output"] for e in inbound
            ] and p["required_dependencies"] == deps,
            "port_dependency_drift_" + engine)
        need(p["contract_version"] == version
             and p["legacy_compatibility"] == "EXPLICIT_ADAPTER_ONLY_NO_IN_PLACE_ALIAS"
             and p["execution_approved"] is False
             and p["customer_processing_approved"] is False
             and p["independent_service_identity_verified"] is False
             and p["quality_gate_status"] == "G01_G10_OPEN"
             and p["deployment_boundary"] ==
                 "ENGINE_OWNED_PRIVATE_WORKLOAD_REQUIRED_BEFORE_EXECUTION",
             "premature_port_release_" + engine)
    need(adapters["decision_status"] == "CODE_REVIEW_ONLY"
         and adapters["owner_signoff"] is False
         and adapters["live_dispatch_enabled"] is False,
         "adapter_approval_forged")
    need(adapters["source_protocol"] == registry["frozen_v2_draft_api"]
         and adapters["target_protocol"] == version, "adapter_version_drift")
    need({(a["adapter_id"],a["source_engine"],a["target_engine"])
          for a in adapters["adapters"]} == EXPECTED_ADAPTERS
         and len(adapters["adapters"]) == 6, "adapter_mapping_drift")
    need(all(a["migration_status"] == "UNMIGRATED"
             and a["runtime_enabled"] is False
             and a["customer_release_approved"] is False
             for a in adapters["adapters"]), "silent_semantic_migration")
    need(quality["completion_count"] == 0
         and quality["open_gate_count"] == 190
         and quality["independent_attestation_issuer_provisioned"] is False
         and quality["customer_release_approved"] is False
         and len(quality["engines"]) == 19, "false_engine_quality_acceptance")
    need(all(len(e["gate_status"]) == 10
             and all(s == "OPEN" for s in e["gate_status"].values())
             and not e["completion_signed"] and not e["signed_reviews"]
             and not e["evidence_refs"] for e in quality["engines"]),
         "engine_gate_fabrication")
    need(handoff["properties"]["contract_version"] == {"const":version}
         and handoff["properties"]["execution_authorized"] == {"const":False}
         and handoff["properties"]["customer_release_approved"] == {"const":False}
         and handoff["additionalProperties"] is False,
         "handoff_schema_unlocked")
    need(set(SCOPE) <= set(handoff["required"])
         and "artifact_sha256" in handoff["required"]
         and "policy_proof_ref" in handoff["required"], "missing_handoff_fence")
    return {"interface_owners":19,"contract_stages":17,"review_handoffs":16,
            "policy_gates":7,"unmigrated_adapters":6,
            "independent_reviews_passed":0,"quality_gates_open":190,
            "ratified":False,"runtime_authorized":False,"customer_release":False}

def load():
    return [read(p) for p in (MANIFEST,PORTS,REGISTRY,FLOW,ADAPTERS,QUALITY,HANDOFF)]

def self_test(values):
    mutations = [
        (0,lambda x:x.update({"design_freeze_approved":True})),
        (0,lambda x:x["approval_slots"][0].update({"state":"APPROVED"})),
        (1,lambda x:x["interfaces"][6].update({"execution_approved":True})),
        (1,lambda x:x["interfaces"][4].update({"upstream_engines":["ENG-02"]})),
        (2,lambda x:x["engines"][5].update({"canonical_output":"PROFESSIONAL_KNOWLEDGE_BUNDLE"})),
        (3,lambda x:x["handoffs"][3].update({"status":"LIVE"})),
        (3,lambda x:x["required_policy_gates"][2].update({"skip_allowed":True})),
        (4,lambda x:x["adapters"][0].update({"runtime_enabled":True})),
        (5,lambda x:x.update({"open_gate_count":189})),
        (6,lambda x:x["properties"]["execution_authorized"].update({"const":True})),
    ]
    for index,mutate in mutations:
        v=copy.deepcopy(values)
        mutate(v[index])
        try:
            inspect(*v)
        except ValueError as err:
            need(str(err).startswith("W0_REJECTED:"), "unexpected_mutation_exception")
        else:
            raise ValueError("W0_NEGATIVE_TEST_BYPASS:" + str(index))
    return len(mutations)

if __name__ == "__main__":
    values=load()
    result=inspect(*values)
    result["negative_mutation_tests"]=self_test(values)
    print(json.dumps(result,sort_keys=True))

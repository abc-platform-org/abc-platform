"""W1 fail-closed, source-locked private trust candidate verification.

Never treats static JSON, CI or assistant-authored data as a managed identity
attestation, an independent ADR signature or permission to create resources.
"""
import copy
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TRUST=ROOT/"governance/abc_w1_workload_trust_boundaries.v0.review.json"
INFRA=ROOT/"governance/phase04_infrastructure_selection.v1.json"
REGISTRY=ROOT/"governance/abc_engine_registry_19.v0.review.json"
RATIFICATION=ROOT/"governance/abc_w0_ratification_manifest.v0.review.json"

ENGINES=("ENG-01","ENG-02","ENG-03","ENG-04","ENG-05","ENG-06","ENG-14")
EDGES={
    ("ENG-01","ENG-02","SESSION_COMMAND"),
    ("ENG-01","ENG-03","ORCHESTRATED_SESSION_TRANSITION"),
    ("ENG-02","ENG-03","CONSENTED_EVIDENCE"),
    ("ENG-03","ENG-04","QUALITY_GATED_ANALYSIS_INPUT"),
    ("ENG-04","ENG-05","ANALYSIS_TO_KNOWLEDGE_REVIEW"),
    ("ENG-05","ENG-06","PROFESSIONAL_KNOWLEDGE_BUNDLE"),
    ("ENG-14","ENG-02","PURPOSE_AND_CAPTURE_POLICY"),
    ("ENG-14","ENG-03","EVIDENCE_PROCESSING_POLICY"),
    ("ENG-14","ENG-04","ANALYSIS_POLICY"),
    ("ENG-14","ENG-05","KNOWLEDGE_PROVENANCE_POLICY"),
    ("ENG-14","ENG-06","DECISION_P2_POLICY")
}
EVIDENCE=(
    "PROVIDER_NETWORK_TOPOLOGY","PRIVATE_POSTGRES_CONNECTIVITY",
    "MANAGED_IDENTITY_ISSUER_METADATA","CERT_REVOCATION_ROTATION_TEST",
    "TLS13_MUTUAL_AUTH_FAILURE_TEST","SEVEN_ENGINE_PRINCIPAL_ATTESTATIONS",
    "TENANT_SCOPE_NEGATIVE_TEST","ENG14_POLICY_NEGATIVE_TEST",
    "RESTORE_AND_ROLLBACK_REPORT","BILLING_CAP_AND_OWNER_AUTHORIZATION"
)
DENIED_FLAGS=(
    "private_network_attested","externally_managed_issuer_attested",
    "external_private_postgres_verified","technical_cost_approval_received",
    "independent_architecture_signoff","independent_security_signoff",
    "independent_sre_signoff","live_v3_routing_allowed",
    "engine_customer_media_allowed","eng05_outbox_release_allowed",
    "customer_release_approved"
)

def fail(test, reason):
    if not test:
        raise ValueError("W1_DENY:"+reason)

def inspect(trust,infra,registry,ratification):
    fail(trust["schema_version"]=="abc.w1-workload-trust-boundaries.v0.review",
         "schema")
    fail(trust["state"]=="CANDIDATE_NOT_PROVISIONED", "candidate_only")
    fail(trust["scope"]=="STAGING_SYNTHETIC_ONLY", "no_customer_environment")
    fail(all(trust.get(f) is False for f in DENIED_FLAGS), "false_attestation")
    fail(trust["canonical_registry"]==str(REGISTRY.relative_to(ROOT)),
         "canonical_registry_ref")
    fail(trust["ratification_manifest"]==str(RATIFICATION.relative_to(ROOT)),
         "ratification_ref")
    fail(trust["infrastructure_selection"]==str(INFRA.relative_to(ROOT)),
         "infrastructure_ref")
    fail(trust["source_adr"]==["ADR-ENG-003","ADR-ENG-004"], "adr_refs")
    fail(trust["action_on_missing_evidence"]=="DENY_AND_DO_NOT_DEPLOY",
         "operator_denial")
    fail(trust["quality_gate_policy"]=="ALL_G01_G10_OPEN", "false_quality_pass")

    fail(infra["deployment_authorized"] is False
         and infra["billing_authorized"] is False
         and infra["production_release_authorized"] is False, "provider_approval")
    fail(infra["database"]["render_managed_postgres_acceptable"] is False
         and infra["database"]["selection"]==
           "EXTERNALLY_CONTROLLED_PRIVATE_POSTGRES16_REQUIRED",
         "private_db_selection")
    fail(infra["database"]["provisioned"] is False
         and infra["identity"]["pki_provisioned"] is False
         and infra["identity"]["oidc_jwks_provisioned"] is False,
         "deployed_provider_misrepresented")
    fail(infra["owner_approval"]["monthly_spend_cap_usd"] is None
         and infra["owner_approval"]["approver"] is None
         and infra["owner_approval"]["independent_security_approval"] is False,
         "billing_unapproved")
    fail(registry["future_canonical_protocol"]==
         "abc.internal.capability.v3.review"
         and registry["future_protocol_executable"] is False
         and registry["operational_engines_complete"]==0,
         "v3_promotion")
    fail(ratification["status"]=="PENDING_INDEPENDENT_REVIEWS"
         and ratification["design_freeze_approved"] is False
         and ratification["live_routing_allowed"] is False
         and all(slot["state"]=="PENDING" and slot["review_ref"] is None
                 for slot in ratification["approval_slots"]), "unsigned_adr")
    requirements=trust["credential_requirements"]
    fail(requirements["target_tls_version"]=="TLSv1.3"
         and requirements["maximum_proposed_assertion_ttl_seconds"]<=900
         and requirements["maximum_proposed_assertion_ttl_seconds"]>0,
         "tls_or_token_ttl")
    for key in (
        "require_unique_principal_per_engine","forbid_group_role_login",
        "require_peer_certificate_binding","require_nonce_or_jti_replay_protection",
        "require_independent_policy_lookup","require_rotation_and_revocation_tests",
        "forbid_static_shared_host_secret"
    ):
        fail(requirements[key] is True, "credential_requirement_"+key)
    workloads=trust["workloads"]
    fail([w["engine_id"] for w in workloads]==list(ENGINES),"missing_engine")
    fail(len({w["proposed_spiffe_id"] for w in workloads})==7
         and len({w["runtime_boundary"] for w in workloads})==7,
         "duplicate_physical_identity")
    for w in workloads:
        engine=w["engine_id"]
        fail(w["proposed_spiffe_id"]==
             "spiffe://abc.internal/staging/"+engine.lower(),
             "identity_path_"+engine)
        fail(w["physical_db_login"]=="UNPROVISIONED_DISTINCT_PER_ENGINE"
             and w["certificate_issuer"]=="EXTERNAL_MANAGED_ISSUER_REQUIRED"
             and w["service_account_issuer"]=="EXTERNAL_MANAGED_ISSUER_REQUIRED"
             and w["credential_material_embedded"] is False
             and w["verified_attestation"] is False
             and w["workload_deployed"] is False
             and w["user_media_allowed"] is False,
             "false_identity_"+engine)
    routes=trust["candidate_routes"]
    fail(len(routes)==11
         and {(e["source"],e["target"],e["artifact"]) for e in routes}==EDGES,
         "trust_edge_drift")
    for e in routes:
        fail(e["audience"]=="abc-engine:"+e["target"]
             and e["protocol"]=="abc.internal.capability.v3.review"
             and e["mtls_required"] is True
             and e["independent_policy_proof_required"] is True
             and e["source_signature_required"] is True
             and e["approved_for_transport"] is False
             and e["externally_verified"] is False
             and e["allow_public_internet"] is False
             and e["authorization_mode"]==
                "EXPLICIT_DENY_PENDING_INDEPENDENT_APPROVAL",
             "invalid_trust_edge")
    slots=trust["operator_evidence_slots"]
    fail(len(slots)==10 and [s["key"] for s in slots]==list(EVIDENCE),
         "evidence_slots")
    fail(all(s["status"]=="MISSING" and s["resource_id"] is None
         and s["reviewer"] is None and s["immutable_evidence_ref"] is None
         and s["reviewed_commit"] is None for s in slots),
         "fabricated_evidence")
    return {"core_workloads":7,"transport_edges":11,"missing_external_evidence":10,
            "independent_approvals":0,"managed_identities_provisioned":0,
            "private_database_provisioned":False,
            "eng05_to_eng06_transport_authorized":False,
            "adr003_004_ratified":False,"live_routing_allowed":False}

def self_test(data):
    mutations=[
        (0,lambda x:x.update(live_v3_routing_allowed=True)),
        (0,lambda x:x.update(private_network_attested=True)),
        (0,lambda x:x.update(independent_security_signoff=True)),
        (0,lambda x:x["workloads"][0].update(workload_deployed=True)),
        (0,lambda x:x["workloads"][1].update(proposed_spiffe_id=x["workloads"][0]["proposed_spiffe_id"])),
        (0,lambda x:x["candidate_routes"][5].update(approved_for_transport=True)),
        (0,lambda x:x["candidate_routes"][5].update(audience="abc-engine:ENG-05")),
        (0,lambda x:x["candidate_routes"][5].update(mtls_required=False)),
        (0,lambda x:x["operator_evidence_slots"][0].update(status="ATTESTED")),
        (0,lambda x:x["credential_requirements"].update(require_independent_policy_lookup=False)),
        (1,lambda x:x["database"].update(render_managed_postgres_acceptable=True)),
        (1,lambda x:x.update(billing_authorized=True)),
        (2,lambda x:x.update(future_protocol_executable=True)),
        (3,lambda x:x.update(design_freeze_approved=True)),
    ]
    for i,(number,change) in enumerate(mutations):
        mutated=copy.deepcopy(data)
        change(mutated[number])
        try:
            inspect(*mutated)
        except ValueError as err:
            fail(str(err).startswith("W1_DENY:"),"invalid_negative_exception")
        else:
            raise AssertionError("W1_MUTATION_ACCEPTED:"+str(i))
    return len(mutations)

def main():
    data=[json.loads(p.read_text()) for p in
          (TRUST,INFRA,REGISTRY,RATIFICATION)]
    result=inspect(*data)
    result["negative_tests"]=self_test(data)
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":
    main()

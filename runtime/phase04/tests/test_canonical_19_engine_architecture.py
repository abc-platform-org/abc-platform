"""Mutation tests for 19-engine ownership, graph handoffs and release denial."""
import copy
import json
import os
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts.validate_abc_19_engine_architecture import load,validate
from abc_foundation.engine19_handoff_preflight import preflight_candidate_handoff
from abc_foundation.store import DomainError

class Canonical19ArchitectureTests(unittest.TestCase):
    def setUp(self):
        self.a=list(load())

    def test_all_19_registered_exactly_once_and_all_controlled(self):
        result=validate(*self.a)
        self.assertEqual(result["canonical_engines"],19)
        self.assertEqual(result["proposed_handoffs"],16)
        self.assertEqual(result["external_gates"],7)
        self.assertEqual(result["engine_complete"],0)
        self.assertEqual(result["legacy_port_adapters_unmigrated"],5)
        self.assertEqual(result["open_engine_quality_gates"],190)
        self.assertFalse(result["runtime_dispatch_authorized"])

    def test_loss_of_engine_owner_and_fake_completion_rejected(self):
        mutations=[
            lambda a:a[0]["engines"].pop(),
            lambda a:a[0]["engines"][7].update(
                logical_owner_key=a[0]["engines"][6]["logical_owner_key"]),
            lambda a:a[0]["engines"][10].update(completion_status="COMPLETE"),
            lambda a:a[0]["engines"][0].update(independent_deployment_verified=True),
            lambda a:a[0]["engines"][6].update(customer_processing_authorized=True),
            lambda a:a[0].update(customer_release_approved=True),
            lambda a:a[0]["legacy_compatibility"][1].update(status="MIGRATED"),
            lambda a:a[0]["legacy_compatibility"][1].update(
                canonical_capability_owners=["ENG-04"]),
        ]
        for mutate in mutations:
            with self.subTest(mutate=str(mutate)):
                a=copy.deepcopy(self.a)
                mutate(a)
                with self.assertRaises(AssertionError):
                    validate(*a)

    def test_all_190_quality_slots_block_false_completion(self):
        mutations=[
            lambda a:a[4].update(open_gate_count=189),
            lambda a:a[4]["engines"][5]["gate_status"].update(
                G08_PROFESSIONAL_VALIDATION="COMPLETE"),
            lambda a:a[4]["engines"][10].update(completion_signed=True),
            lambda a:a[4]["engines"][15]["signed_reviews"].update(
                G01_ARCHITECTURE="fake-approval"),
            lambda a:a[4]["engines"][2]["gate_status"].pop(
                "G02_DOMAIN_CAPABILITY"),
            lambda a:a[4].update(
                independent_attestation_issuer_provisioned=True),
        ]
        for mutate in mutations:
            with self.subTest(mutate=str(mutate)):
                a=copy.deepcopy(self.a)
                mutate(a)
                with self.assertRaises(AssertionError):
                    validate(*a)

    def test_reordered_or_unguarded_flow_rejected(self):
        mutations=[
            lambda a:a[1]["ordered_stages"][7].update(owner_engine="ENG-11"),
            lambda a:a[1]["handoffs"][0].update(to="ENG-17"),
            lambda a:a[1]["handoffs"][3].update(status="LIVE"),
            lambda a:a[1]["handoffs"][3].update(required_guards=[]),
            lambda a:a[1]["ordered_stages"][12].update(requires_gates=[]),
            lambda a:a[1]["required_policy_gates"][0].update(skip_allowed=True),
            lambda a:a[1]["required_policy_gates"][0].update(
                verification_status="APPROVED"),
            lambda a:a[1].update(flow_complete=True),
            lambda a:a[1].update(private_network_e2e_complete=True),
            lambda a:a[1]["ordered_stages"][-1].update(
                mode="CORE_IN_SALON_FLOW"),
            lambda a:a[2]["properties"]["execution_authorized"].update(
                const=True),
        ]
        for mutate in mutations:
            with self.subTest(mutate=str(mutate)):
                a=copy.deepcopy(self.a)
                mutate(a)
                with self.assertRaises(AssertionError):
                    validate(*a)


class Canonical19CandidateHandoffTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{"ABC_ENV":"LOCAL_INTEGRATION_ONLY"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.message={
            "handoff_id":str(uuid.uuid4()),"contract_version":"abc.internal.capability.v3.review",
            "from_engine":"ENG-02","to_engine":"ENG-03",
            "tenant_id":"tenant-test","branch_id":"branch-test",
            "session_id":str(uuid.uuid4()),"state_version":2,
            "correlation_id":str(uuid.uuid4()),
            "artifact_kind":"PURPOSE_BOUND_CONSULTATION_EVIDENCE",
            "artifact_sha256":"a"*64,
            "evidence_refs":["synthetic:evidence-0001"],
            "policy_proof_ref":"synthetic:external-consent-proof-needs-verification",
            "status":"CANDIDATE_FOR_EXTERNAL_AUTHORIZATION",
            "execution_authorized":False,"customer_release_approved":False
        }

    def test_valid_candidate_still_never_authorizes_dispatch(self):
        r=preflight_candidate_handoff(self.message)
        self.assertEqual(r["status"],"CONTRACT_PREFLIGHT_ONLY")
        self.assertEqual(r["required_policy_gates"],["GATE_P0_CONSENT"])
        self.assertFalse(r["runtime_dispatch_authorized"])
        self.assertFalse(r["professional_plan_authorized"])
        self.assertTrue(r["external_signature_verification_required"])

    def test_all_schema_and_provenance_mutations_rejected(self):
        mutations=[
            {"from_engine":"ENG-14"},
            {"to_engine":"ENG-17"},
            {"artifact_kind":"AUTHORIZED_OPERATIONAL_HANDOFF"},
            {"contract_version":"abc.internal.engine.v2.draft"},
            {"tenant_id":"bad tenant"},
            {"state_version":True},
            {"artifact_sha256":"not-a-digest"},
            {"status":"LIVE"},
            {"execution_authorized":True},
            {"customer_release_approved":True},
            {"policy_proof_ref":None},
            {"evidence_refs":[]},
            {"additional_field":"bypass"}
        ]
        for patch_values in mutations:
            with self.subTest(patch_values=patch_values):
                with self.assertRaises(DomainError):
                    preflight_candidate_handoff({**self.message,**patch_values})

    def test_bad_correlation_and_env_rejected(self):
        with self.assertRaises(DomainError):
            preflight_candidate_handoff({**self.message,"session_id":str(uuid.uuid4()).upper()})
        with patch.dict(os.environ,{"ABC_ENV":"STAGING_PRIVATE"}):
            with self.assertRaisesRegex(DomainError,"canonical19_runtime_not_approved"):
                preflight_candidate_handoff(self.message)

    def test_non_gated_next_step_cannot_manufacture_approval(self):
        message={**self.message,
            "from_engine":"ENG-03","to_engine":"ENG-04",
            "artifact_kind":"TRACEABLE_EVIDENCE_PACKAGE",
            "policy_proof_ref":None}
        r=preflight_candidate_handoff(message)
        self.assertEqual(r["required_policy_gates"],[])
        self.assertFalse(r["runtime_dispatch_authorized"])


if __name__=="__main__":
    unittest.main()

"""Real computations, strictly limited to synthetic and nonprocedural v2.

These tests do NOT validate a computer vision model or salon expertise.
"""
import copy
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from abc_foundation.engine_v2_runtime import execute
from abc_foundation.engine_v2_contracts import validate_port
from abc_foundation.store import DomainError
from test_engine_v2_contracts import request,L,E,H


class V2BoundedImplementationTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{"ABC_ENV":"LOCAL_INTEGRATION_ONLY"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_eng04_exact_controlled_spec_and_deterministic_provenance(self):
        req=request("ENG-04")
        result=execute(req,engine="ENG-04")
        self.assertEqual(result["result"]["status"],"DRAFT_FOR_SPECIALIST_REVIEW")
        look=result["result"]["candidate_looks"][0]
        self.assertEqual(look["evidence_ids"],[L])
        self.assertEqual(look["edit_regions"],["HAIR"])
        self.assertEqual(look["feasibility"],"NOT_VERIFIED")
        self.assertEqual(result["result"]["visual_qa_status"],"NOT_VERIFIED")
        self.assertFalse(result["release_approved"])
        same=copy.deepcopy(req)
        same["request_id"]="55555555-5555-4555-8555-555555555555"
        same["correlation_id"]="66666666-6666-4666-8666-666666666666"
        self.assertEqual(execute(same,engine="ENG-04")["result"]["candidate_looks"],
                         result["result"]["candidate_looks"])
        different=copy.deepcopy(req)
        different["tenant_id"]="other-tenant"
        self.assertNotEqual(execute(different,engine="ENG-04")["result"]["candidate_looks"][0]["look_id"],
                            look["look_id"])
        different=copy.deepcopy(req)
        different["payload"]["evidence"][0]["source_digest"]="b"*64
        self.assertNotEqual(execute(different,engine="ENG-04")["result"]["candidate_looks"][0]["spec_digest"],
                            look["spec_digest"])

    def test_eng04_unknown_invalid_intent_and_nonhair_scope_are_blocked(self):
        for change in ("unknown","unsupported","nonhair","extra-region"):
            req=request("ENG-04")
            if change=="unknown":
                req["payload"]["evidence"][0]["evidence_class"]="UNKNOWN"
            if change=="unsupported":
                req["payload"]["target_intent"]="I want a random unsupported model"
            if change=="nonhair":
                req["payload"]["service_kind"]="SKIN"
            if change=="extra-region":
                req["payload"]["edit_regions"]=["HAIR","SKIN"]
            with self.subTest(change=change):
                result=execute(req,engine="ENG-04")["result"]
                self.assertEqual(result["status"],"BLOCKED")
                self.assertEqual(result["candidate_looks"],[])
                self.assertGreater(len(result["uncertainty"]),2)

    def test_eng05_hard_stop_unknown_policy_and_unreviewed_source(self):
        for mutation in ("normal","no-unknown","policy-review","source-review"):
            req=request("ENG-05")
            if mutation=="no-unknown":
                req["payload"]["critical_unknowns"]=[]
            if mutation=="policy-review":
                req["payload"]["policy_gate"]["decision"]="REVIEW_REQUIRED"
            if mutation=="source-review":
                req["payload"]["knowledge_sources"][0]["review_status"]="SPECIALIST_REVIEWED"
            result=execute(req,engine="ENG-05")["result"]
            self.assertEqual(result["status"],"BLOCKED")
            self.assertEqual(result["eligible_looks"],[])
            self.assertFalse(result["execution_authorized"])
            self.assertEqual(result["excluded_looks"][0]["look_id"],L)

    def test_eng05_all_controlled_inputs_yield_review_queue_never_approval(self):
        req=request("ENG-05")
        req["payload"]["critical_unknowns"]=[]
        req["payload"]["policy_gate"]["decision"]="REVIEW_REQUIRED"
        req["payload"]["knowledge_sources"][0]["review_status"]="SPECIALIST_REVIEWED"
        result=execute(req,engine="ENG-05")["result"]
        self.assertEqual(result["status"],"SPECIALIST_REVIEW_REQUIRED")
        self.assertEqual(result["eligible_looks"][0]["evidence_ids"],[L])
        self.assertFalse(result["specialist_selection_authorized"])
        self.assertFalse(result["execution_authorized"])

    def test_eng06_never_drafts_without_external_verified_gate(self):
        req=request("ENG-06")
        response=execute(req,engine="ENG-06")["result"]
        self.assertEqual(response["status"],"AWAITING_SPECIALIST_INPUT")
        self.assertIsNone(response["draft_plan"])
        self.assertIn("CONSENT_VERIFICATION_REQUIRED",response["missing_requirements"])
        self.assertIn("APPROVED_SOP_MISSING",response["missing_requirements"])
        self.assertIn("EXTERNAL_EVIDENCE_GATE_UNAVAILABLE_OR_DENIED",
                      response["missing_requirements"])

    def test_eng06_nonoperational_draft_requires_verified_bound_gate(self):
        req=request("ENG-06")
        req["payload"]["consent_status"]="VERIFIED_BY_ENG14"
        req["payload"]["consent_proof_digest"]="c"*64
        req["payload"]["approved_sop_ref"]="synthetic:unreleased-sop"
        req["payload"]["professional_findings"][0]["review_status"]="SPECIALIST_RECORDED"
        self.assertIsNone(execute(req,engine="ENG-06")["result"]["draft_plan"])
        class ExplicitTestOnlyGate:
            def verify(self,**kwargs):
                return kwargs["tenant_id"]=="tenant-test" and (
                    kwargs["consent_proof_digest"]=="c"*64)
        out=execute(req,engine="ENG-06",evidence_gate=ExplicitTestOnlyGate())
        plan=out["result"]["draft_plan"]
        self.assertIsNotNone(plan)
        self.assertEqual(out["result"]["status"],"DRAFT_REQUIRES_SPECIALIST_REVIEW")
        self.assertEqual(plan["tools_materials"],[])
        self.assertEqual(plan["step_sequence"][-1],
                         "Request professional validation before any treatment.")
        self.assertTrue(plan["stop_conditions"])
        self.assertFalse(out["result"]["operational_handoff_authorized"])
        self.assertFalse(out["execution_authorized"])
        req["tenant_id"]="other-tenant"
        req["payload"]["selected_look_lock"]["tenant_id"]="other-tenant"
        req["payload"]["decision_ref"]["tenant_id"]="other-tenant"
        self.assertIsNone(execute(req,engine="ENG-06",
            evidence_gate=ExplicitTestOnlyGate())["result"]["draft_plan"])

    def test_gate_never_returns_authorization_in_external_environment(self):
        req=request("ENG-04")
        with patch.dict(os.environ,{"ABC_ENV":"STAGING_PRIVATE"}):
            with self.assertRaises(DomainError):
                execute(req,engine="ENG-04")


if __name__=="__main__":
    unittest.main()

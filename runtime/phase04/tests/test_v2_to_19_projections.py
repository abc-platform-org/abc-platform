import copy
import os
import unittest
from unittest.mock import patch
from abc_foundation.store import DomainError
from abc_foundation.v2_to_19_projection import project_v2_response
from test_engine_v2_contracts import request,response

class StrictAdapterTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{"ABC_ENV":"LOCAL_INTEGRATION_ONLY"})
        self.env.start()
        self.addCleanup(self.env.stop)
    def test_valid_four_mappings_retain_no_authorization(self):
        for engine,key,target in (
          ("ENG-04","A04_TO_06_DECISION_INPUT","ENG-06"),
          ("ENG-04","A04_TO_07_LOOK_SPEC_INPUT","ENG-07"),
          ("ENG-05","A05_TO_06_DECISION_EVIDENCE","ENG-06"),
          ("ENG-06","A06_TO_15_PLAN_CANDIDATE","ENG-15")):
            q=request(engine)
            r=response(q)
            x=project_v2_response(q,r,adapter_id=key)
            self.assertEqual(x["target_engine"],target)
            self.assertEqual(x,project_v2_response(q,r,adapter_id=key))
            self.assertFalse(x["customer_release_approved"])
            self.assertFalse(x["downstream_dispatch_authorized"])
            self.assertFalse(x["professional_validation_complete"])

    def test_reject_wrong_engine_and_legacy_protocol(self):
        q=request("ENG-04");r=response(q)
        with self.assertRaises(DomainError):
            project_v2_response(q,r,adapter_id="A05_TO_06_DECISION_EVIDENCE")
        q["contract_version"]="abc.internal.engine.synthetic.v1"
        with self.assertRaises(DomainError):
            project_v2_response(q,r,adapter_id="A04_TO_07_LOOK_SPEC_INPUT")

    def test_reject_modified_response_and_untrusted_approval(self):
        q=request("ENG-04")
        for modification in (
            lambda r:r.update(tenant_id="tenant-other"),
            lambda r:r.update(execution_authorized=True),
            lambda r:r["result"].update(status="BLOCKED"),
            lambda r:r["result"]["candidate_looks"][0].update(
                evidence_ids=["ffffffff-ffff-4fff-8fff-ffffffffffff"])
        ):
            r=response(q);modification(r)
            with self.subTest(modification=str(modification)):
                with self.assertRaises(DomainError):
                    project_v2_response(q,r,adapter_id="A04_TO_07_LOOK_SPEC_INPUT")

    def test_reject_stale_look_and_fake_decision_eligibility(self):
        q=request("ENG-06");r=response(q)
        q["payload"]["selected_look_lock"]["state_version"]=1
        with self.assertRaises(DomainError):
            project_v2_response(q,r,adapter_id="A06_TO_15_PLAN_CANDIDATE")
        q=request("ENG-05");r=response(q)
        r["result"]["eligible_looks"]=[{
            "look_id":q["payload"]["candidate_looks"][0]["look_id"],
            "reason":"no evidence","evidence_ids":[
                q["payload"]["candidate_looks"][0]["evidence_ids"][0]]}]
        with self.assertRaises(DomainError):
            project_v2_response(q,r,adapter_id="A05_TO_06_DECISION_EVIDENCE")

    def test_hosted_staging_and_production_denied(self):
        q=request("ENG-04");r=response(q)
        for mode in ("STAGING_PRIVATE","PRODUCTION"):
            with patch.dict(os.environ,{"ABC_ENV":mode}):
                with self.assertRaises(DomainError):
                    project_v2_response(q,r,adapter_id="A04_TO_06_DECISION_INPUT")

    def test_projection_digest_changes_with_source_and_registry_blocks_release(self):
        from abc_foundation.v2_to_19_projection import _digest
        from pathlib import Path
        import json
        from jsonschema import Draft202012Validator,FormatChecker
        q=request("ENG-04")
        original=response(q)
        x=project_v2_response(q,original,adapter_id="A04_TO_06_DECISION_INPUT")
        self.assertEqual(x["projection_sha256"],_digest(x["projection"]))
        r=copy.deepcopy(original)
        r["result"]["uncertainty"].append("ADDITIONAL_UNCERTAINTY")
        changed=project_v2_response(q,r,adapter_id="A04_TO_06_DECISION_INPUT")
        self.assertNotEqual(x["source_response_sha256"],
                            changed["source_response_sha256"])
        self.assertNotEqual(x["projection_sha256"],
                            changed["projection_sha256"])
        schema=json.loads((Path(__file__).resolve().parents[3]/
            "contracts/review/v2_to_19_adapter_projection.v0.schema.json").read_text())
        for modification in (
            {"downstream_dispatch_authorized":True},
            {"customer_release_approved":True},
            {"professional_validation_complete":True},
            {"target_engine":"ENG-15"},
            {"status":"LIVE"}
        ):
            candidate={**x,**modification}
            self.assertFalse(Draft202012Validator(schema,
                format_checker=FormatChecker()).is_valid(candidate))

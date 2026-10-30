"""Offline source-linked v2->canonical projections, NOT a live 19-engine chain."""
import os
import unittest
from unittest.mock import patch

from abc_foundation.engine_v2_runtime import execute
from abc_foundation.v2_to_19_projection import project_v2_response,_digest
from test_engine_v2_contracts import request

class OfflineCompatibilityChainTests(unittest.TestCase):
    def test_real_bounded_v2_responses_project_without_claiming_specialist_authority(self):
        with patch.dict(os.environ,{"ABC_ENV":"LOCAL_INTEGRATION_ONLY"}):
            q4=request("ENG-04")
            r4=execute(q4,engine="ENG-04")
            self.assertEqual(r4["result"]["status"],"DRAFT_FOR_SPECIALIST_REVIEW")
            for adapter in ("A04_TO_06_DECISION_INPUT","A04_TO_07_LOOK_SPEC_INPUT"):
                x=project_v2_response(q4,r4,adapter_id=adapter)
                self.assertEqual(x["source_response_sha256"],_digest(r4))
                self.assertFalse(x["downstream_dispatch_authorized"])
            q5=request("ENG-05")
            q5["payload"]["recommendation_ref"]["digest"]=_digest(r4)
            q5["payload"]["candidate_looks"]=[
                {k:item[k] for k in ("look_id","spec_digest","evidence_ids")}
                for item in r4["result"]["candidate_looks"]]
            r5=execute(q5,engine="ENG-05")
            self.assertEqual(r5["result"]["status"],"BLOCKED")
            out=project_v2_response(q5,r5,adapter_id="A05_TO_06_DECISION_EVIDENCE")
            self.assertEqual(out["projection"]["eligible_look_ids"],[])
            self.assertFalse(out["projection"]["signed_policy_verified"])
            self.assertFalse(out["professional_validation_complete"])

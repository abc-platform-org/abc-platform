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

"""Isolated worker contract, OS process and no leaked ambient credential tests."""
import json
import os
import uuid
import unittest
from unittest.mock import patch
from abc_foundation.isolated_engine_service import dispatch,validate,VERSION
from abc_foundation.isolated_engine_runner import IsolatedEngineRunner
from abc_foundation.store import DomainError

SID=str(uuid.uuid4())
C="offline-synthetic-consumer"
FIXTURE={"kind":"SYNTHETIC_TEST_FIXTURE","source_id":"synthetic:offline-catalog",
         "source_version":"test-v1","validated_by":"TEST_FIXTURE_ONLY",
         "facts":{"synthetic:style-a":True,"synthetic:style-b":False}}

def request(engine,payload):
    return {"request_id":str(uuid.uuid4()),"engine_id":engine,
           "contract_version":VERSION,"consumer_id":C,"session_id":SID,
           "payload":payload}


class IndependentEngineProcessTests(unittest.TestCase):
    def test_eng05_separate_process_validates_synthetic_catalog(self):
        r=IsolatedEngineRunner().call("ENG-05",consumer_id=C,session_id=SID,
                 payload={"service_id":"synthetic:hair-color","fixture":FIXTURE})
        self.assertEqual(r["ontology_version"],"synthetic-ontology.1")
        self.assertEqual(r["retrieval_sources"][0]["validated_by"],"TEST_FIXTURE_ONLY")

    def test_eng05_no_source_is_not_falsely_certified(self):
        r=IsolatedEngineRunner().call("ENG-05",consumer_id=C,session_id=SID,
                 payload={"service_id":"synthetic:hair-color","fixture":None})
        self.assertEqual(r["retrieval_sources"],[])
        self.assertIn("SOURCE_UNVERIFIED",r["unknowns"])

    def test_invalid_schema_rejected_before_domain_engine(self):
        for tamper in (
            {"contract_version":"future.v2"},
            {"engine_id":"ENG-14"},
            {"session_id":"not-uuid"},
            {"consumer_id":""},
            {"payload":{"service_id":"synthetic:hair-color"}},
            {"unknown_authorization":True}
        ):
            with self.subTest(tamper=tamper),self.assertRaises(DomainError):
                dispatch({**request("ENG-05",{"service_id":"synthetic:hair-color",
                       "fixture":FIXTURE}),**tamper},"ENG-05")

    def test_engine_to_engine_payload_cross_session_denied(self):
        with self.assertRaises(DomainError):
            dispatch(request("ENG-06",{"analysis":{"session_id":str(uuid.uuid4())},
                        "knowledge":{}}),"ENG-06")

    def test_no_parent_database_secrets_passed_to_child(self):
        import abc_foundation.isolated_engine_runner as runner_module
        real=runner_module.subprocess.run
        def wrapper(*args,**kwargs):
            env=kwargs.get("env",{})
            self.assertEqual(set(env),{"PYTHONPATH","PYTHONNOUSERSITE",
                                        "ABC_ENGINE_SYNTHETIC_ONLY"})
            self.assertNotIn("ABC_TEST_PG_ADMIN_DSN",env)
            self.assertNotIn("ABC_ENGINE_DSN",env)
            return real(*args,**kwargs)
        with patch.dict(os.environ,{"ABC_ENGINE_DSN":"secret",
                      "ABC_TEST_PG_ADMIN_DSN":"never-export"},clear=False):
            with patch.object(runner_module.subprocess,"run",side_effect=wrapper):
                self.assertEqual(IsolatedEngineRunner().call("ENG-05",consumer_id=C,
                    session_id=SID,payload={"service_id":"synthetic:hair-color",
                    "fixture":None})["retrieval_sources"],[])

    def test_envelope_size_deadline_and_engine_allowlist(self):
        r=IsolatedEngineRunner(timeout_seconds=8)
        with self.assertRaises(DomainError):
            r.call("ENG-19",consumer_id=C,session_id=SID,payload={})
        with self.assertRaises(DomainError):
            r.call("ENG-04",consumer_id=C,session_id=SID,
                  payload={"evidence":["x"*(262145)]})
        for t in (0,16,True):
            with self.subTest(timeout=t),self.assertRaises(ValueError):
                IsolatedEngineRunner(timeout_seconds=t)

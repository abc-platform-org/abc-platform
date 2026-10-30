"""Three distinct v2 OS processes with real JSON schema/runtime execution.

This is process isolation under CI, not an externally deployed mTLS cluster.
"""
import json
import os
import subprocess
import sys
import unittest

from abc_foundation.engine_v2_contracts import validate_port
from test_engine_v2_contracts import request,L


class ThreeProcessV2BoundedE2E(unittest.TestCase):
    def worker(self,engine,payload,enabled=True):
        env=os.environ.copy()
        env["ABC_ENV"]="LOCAL_INTEGRATION_ONLY" if enabled else "UNAPPROVED"
        proc=subprocess.run([sys.executable,"-m",
            "abc_foundation.engine_v2_worker",engine],
            input=json.dumps(payload),capture_output=True,text=True,
            env=env,timeout=10,check=False)
        return proc,json.loads(proc.stdout)

    def test_three_independent_bounded_processes_full_chain(self):
        first=request("ENG-04")
        p4,r4=self.worker("ENG-04",first)
        self.assertEqual(p4.returncode,0,p4.stderr)
        self.assertTrue(validate_port(r4,engine="ENG-04",
                       response=True,request=first)["valid"])
        looks=r4["result"]["candidate_looks"]
        self.assertEqual(len(looks),1)
        look=looks[0]

        second=request("ENG-05")
        second["payload"]["candidate_looks"]=[{
           "look_id":look["look_id"],"spec_digest":look["spec_digest"],
           "evidence_ids":look["evidence_ids"]}]
        p5,r5=self.worker("ENG-05",second)
        self.assertEqual(p5.returncode,0,p5.stderr)
        self.assertTrue(validate_port(r5,engine="ENG-05",
                        response=True,request=second)["valid"])
        self.assertEqual(r5["result"]["status"],"BLOCKED")
        self.assertEqual(r5["result"]["excluded_looks"][0]["look_id"],look["look_id"])

        third=request("ENG-06")
        third["payload"]["selected_look_lock"]["look_id"]=look["look_id"]
        p6,r6=self.worker("ENG-06",third)
        self.assertEqual(p6.returncode,0,p6.stderr)
        self.assertTrue(validate_port(r6,engine="ENG-06",
                       response=True,request=third)["valid"])
        self.assertIsNone(r6["result"]["draft_plan"])
        self.assertEqual(r6["result"]["status"],"AWAITING_SPECIALIST_INPUT")
        for response in (r4,r5,r6):
            self.assertFalse(response["release_approved"])
            self.assertFalse(response["execution_authorized"])

    def test_worker_rejects_cross_version_oversized_and_unapproved_env(self):
        req=request("ENG-04")
        for mode in ("wrong_version","wrong_engine","unsafe_env","oversized"):
            data=dict(req)
            if mode=="wrong_version":
                data["contract_version"]="abc.internal.engine.synthetic.v1"
            if mode=="wrong_engine":
                data["engine_id"]="ENG-05"
            if mode=="oversized":
                data["payload"]={"untrusted": "x"*140000}
            proc,reply=self.worker("ENG-04",data,enabled=mode!="unsafe_env")
            with self.subTest(mode=mode):
                self.assertEqual(proc.returncode,3)
                self.assertEqual(reply["error"],"CONTROLLED_ENGINE_REQUEST_DENIED")
                self.assertFalse(reply["release_approved"])
                self.assertNotIn("payload",reply)
                self.assertNotIn("result",reply)

    def test_wrong_cli_engine_fails_before_reading_payload(self):
        env={**os.environ,"ABC_ENV":"LOCAL_INTEGRATION_ONLY"}
        proc=subprocess.run([sys.executable,"-m",
          "abc_foundation.engine_v2_worker","ENG-14"],
          input="{}",capture_output=True,text=True,env=env,timeout=5)
        self.assertEqual(proc.returncode,2)
        self.assertFalse(proc.stdout)


if __name__=="__main__":
    unittest.main()

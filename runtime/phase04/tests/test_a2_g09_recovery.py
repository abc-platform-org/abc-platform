"""A2 G09 local-only disaster probes for a synthetic five-engine IPC chain.

Real child OS crashes (os._exit(75)), SQLite WAL persistence, idempotency,
bound restart timing, timeout termination, no release and offline alert rules.
Hosted PG PITR, real pager, DNS/network fault and external SRE approval are
NOT covered. Existing G06 CI separately covers real disposable PG16 restart.
"""
import json
import multiprocessing as mp
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
import uuid

from abc_foundation.eng02_consultation import ConsultationEngine
from abc_foundation.oidc import Principal
from abc_foundation.store import DomainError

import test_eng02_eng06_five_process_chain as five
from a2_g07_five_process_benchmark import evaluate_alerts,policy

CRASH_EXIT=75


def _exit_ungracefully():
    os._exit(CRASH_EXIT)


def _commit_then_crash(cfg):
    eng=ConsultationEngine(cfg["sqlite_path"],five.ScopedSyntheticAuthority(cfg))
    principal=Principal(cfg["subject"],five.ISS)
    q=eng.next(principal,cfg["session_id"])["next_question"]
    eng.record(principal,cfg["session_id"],question_id=q["question_id"],
               value="NO",source="CLIENT",
               operation_key="a2-crash-commit-"+cfg["session_id"])
    # No ACK, no graceful cleanup. Only a truly committed WAL write survives.
    os._exit(CRASH_EXIT)


def _hang_forever():
    time.sleep(20)


class G09LocalFaultRecovery(unittest.TestCase):
    observed_rto=[]

    @classmethod
    def tearDownClass(cls):
        out=os.environ.get("ABC_A2_G09_REPORT")
        if out:
            target=Path(out)
            target.parent.mkdir(parents=True,exist_ok=True)
            limit=policy()["gate_g09"]["thresholds"]
            report={
               "gate":"G09_SYNTHETIC_RECOVERY_CI",
               "status":"CI_CANDIDATE_ONLY_NO_SRE_SIGNOFF",
               "observed_restarts":len(cls.observed_rto),
               "max_recovery_seconds":round(max(cls.observed_rto,default=0),6),
               "rto_ci_budget_seconds":limit["local_process_recovery_seconds_max"],
               "committed_synthetic_answer_rows_lost":0,
               "customer_release_approved":False,
               "real_hosted_pg_pitr_proven":False,
               "pager_delivery_proven":False,
               "externally_managed_recovery_proven":False,
               "a2_operational_closed":False,
               "exact_head":os.getenv("GITHUB_SHA","UNVERIFIED_LOCAL"),
               "run_id":os.getenv("GITHUB_RUN_ID","UNVERIFIED_LOCAL")
            }
            target.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")

    def setUp(self):
        if os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
            self.fail("local_integration_only_required")
        self.case=five.FiveIndependentProcessSyntheticChain(
                "test_01_full_five_process_chain_is_synthetic_only")
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.limits=policy()["gate_g09"]["thresholds"]

    def _die(self,target=_exit_ungracefully,args=()):
        proc=self.case.ctx.Process(target=target,args=args)
        proc.start()
        proc.join(timeout=5)
        try:
            self.assertEqual(proc.exitcode,CRASH_EXIT)
        finally:
            if proc.is_alive():
                proc.terminate()
                proc.join(timeout=2)
        return proc.pid

    def _recovery_stage(self,engine,**kwargs):
        start=time.perf_counter()
        response=self.case.stage(engine,**kwargs)
        duration=time.perf_counter()-start
        self.assertLessEqual(duration,self.limits["local_process_recovery_seconds_max"])
        self.assertEqual(response["engine_id"],engine)
        self.assertNotIn("error",response)
        self.assertIs(response["release_approved"],False)
        self.__class__.observed_rto.append(duration)
        return response

    def test_01_all_five_engines_restart_after_forced_process_crash(self):
        _,e3,e4,e5,e6=self.case.complete()
        arguments={
            "ENG-02":{"values":[]},
            "ENG-03":{},
            "ENG-04":{"payload":{"evidence":e3["result"]}},
            "ENG-05":{"payload":{"service_id":five.SYNTHETIC_SERVICE,
                                 "fixture":five.FIXTURE}},
            "ENG-06":{"payload":{"analysis":e4["result"]["result"],
                                 "knowledge":e5["result"]["result"]}},
        }
        for engine in ("ENG-02","ENG-03","ENG-04","ENG-05","ENG-06"):
            with self.subTest(engine=engine):
                child=self._die()
                self.assertNotEqual(child,os.getpid())
                reply=self._recovery_stage(engine,**arguments[engine])
                self.assertIs(reply["release_approved"],False)

    def test_02_hard_exit_after_committed_answer_before_ack_has_zero_rpo_and_replay(self):
        self._die(target=_commit_then_crash,args=(self.case.cfg,))
        path=self.case.cfg["sqlite_path"]
        with sqlite3.connect(path) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM eng02_answers").fetchone()[0],1)
            self.assertEqual(con.execute("SELECT count(*) FROM eng02_receipts").fetchone()[0],1)
        eng=ConsultationEngine(path,five.ScopedSyntheticAuthority(self.case.cfg))
        p=Principal(self.case.cfg["subject"],five.ISS)
        key="a2-crash-commit-"+self.case.cfg["session_id"]
        reply=eng.record(p,self.case.cfg["session_id"],
                         question_id="synthetic:prior-treatment",value="NO",
                         source="CLIENT",operation_key=key)
        self.assertEqual(reply["status"],"RECORDED_SYNTHETIC")
        with sqlite3.connect(path) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM eng02_answers").fetchone()[0],1)
            self.assertEqual(con.execute("SELECT count(*) FROM eng02_receipts").fetchone()[0],1)
        self._recovery_stage("ENG-03")

    def test_03_read_only_backup_restore_after_abrupt_writer_exit(self):
        self._die(target=_commit_then_crash,args=(self.case.cfg,))
        with tempfile.TemporaryDirectory() as target:
            recovered=str(Path(target)/"synthetic-restore.sqlite")
            with sqlite3.connect(self.case.cfg["sqlite_path"]) as src:
                with sqlite3.connect(recovered) as dst:
                    src.backup(dst)
            original=self.case.cfg["sqlite_path"]
            self.case.cfg["sqlite_path"]=recovered
            try:
                with sqlite3.connect(recovered) as con:
                    self.assertEqual(con.execute("PRAGMA integrity_check").fetchone()[0],"ok")
                    self.assertEqual(con.execute("SELECT count(*) FROM eng02_answers").fetchone()[0],1)
                    self.assertEqual(con.execute("SELECT count(*) FROM eng02_receipts").fetchone()[0],1)
                restored=self._recovery_stage("ENG-03")
                self.assertEqual(sum(e["evidence_class"]=="USER_REPORTED"
                                     for e in restored["result"]),1)
            finally:
                self.case.cfg["sqlite_path"]=original

    def test_04_hung_worker_is_killed_and_replaced_inside_cleanup_budget(self):
        proc=self.case.ctx.Process(target=_hang_forever)
        proc.start()
        begin=time.perf_counter()
        proc.join(timeout=.1)
        self.assertTrue(proc.is_alive(),"expected real hung process")
        proc.terminate()
        proc.join(timeout=2)
        if proc.is_alive():
            proc.kill()
            proc.join(timeout=2)
        self.assertFalse(proc.is_alive())
        self.assertLessEqual(time.perf_counter()-begin,
                             self.limits["timeout_cleanup_seconds_max"])
        self._recovery_stage("ENG-02",values=[])

    def test_05_recovered_chain_never_claims_unverified_professional_source(self):
        self._die()
        a,b,c,d,e=self.case.complete(fixture=None)
        self.assertIn("SOURCE_UNVERIFIED",d["result"]["result"]["unknowns"])
        self.assertEqual(e["result"]["result"]["candidates"],[])
        self.assertFalse(e["release_approved"])

    def test_06_offline_alert_rules_fire_on_errors_latency_rto_and_release(self):
        doc=policy()
        a=evaluate_alerts(error_count=1,p95_seconds=100,
                          restart_seconds=100,release_count=1,doc=doc)
        self.assertEqual({v["code"] for v in a},{
            "CHAIN_ERROR_RATE","P95_LATENCY","RESTART_BUDGET",
            "CONSENT_OR_RELEASE_VIOLATION"})
        self.assertEqual(sum(v["severity"]=="critical" for v in a),3)

    def test_07_offline_alert_rule_healthy_thresholds_generate_no_alarm(self):
        doc=policy()
        limit=doc["gate_g07"]["thresholds"]["end_to_end_seconds"]["p95_max"]
        rt=doc["gate_g09"]["thresholds"]["local_process_recovery_seconds_max"]
        self.assertEqual(evaluate_alerts(error_count=0,p95_seconds=limit,
                restart_seconds=rt,release_count=0,doc=doc),[])

    def test_08_media_and_unverified_safety_knowledge_stay_blocked_after_crash(self):
        self._die()
        bad=self.case.stage("ENG-02",values=[],media="UNAUTHORIZED-SYNTHETIC")
        self.assertEqual(bad.get("error"),"synthetic_non_media_only")
        self.assertFalse(Path(self.case.cfg["sqlite_path"]).exists())
        invalid=self.case.stage("ENG-05",payload={
            "service_id":five.SYNTHETIC_SERVICE,
            "fixture":{**five.FIXTURE,"validated_by":"FAKE_SRE"}})
        self.assertEqual(invalid.get("error"),"unverified_knowledge_source")

    def test_09_policy_never_marks_externally_managed_sre_review_complete(self):
        doc=policy()
        d=doc["operational_deferred"]
        self.assertFalse(d["operator_approval_issued"])
        self.assertFalse(d["staging_environment_deployed"])
        self.assertFalse(d["external_alert_route_acknowledged"])
        self.assertFalse(d["real_managed_database_pitr_restore_proven"])
        self.assertFalse(d["a2_operational_closed"])
        self.assertFalse(d["eng06_customer_release_approved"])


if __name__=="__main__":
    unittest.main()

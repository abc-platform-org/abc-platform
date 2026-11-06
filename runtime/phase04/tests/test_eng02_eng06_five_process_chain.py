"""Five REAL independent OS processes, ENG02→ENG03→ENG04→ENG05→ENG06.

Synthetic question/answer and non-media evidence ONLY. Every stage runs in
a separate spawned Python process and exchanges checked envelopes via IPC.
ENG14's current S0 question policy is evaluated on every ENG02 mutation.
No media, model API, remote service, production PKI or customer release.
The inter-process IPC is a LOCAL TEST, not independently managed mTLS.
"""
import multiprocessing as mp
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
import uuid

from abc_foundation.eng02_consultation import SYNTHETIC_SERVICE
from abc_foundation.isolated_engine_service import VERSION

ISS="https://ci-5engine-oidc.invalid"
CONSUMER="synthetic-chain-consumer"
FIXTURE={
 "kind":"SYNTHETIC_TEST_FIXTURE","source_id":"synthetic:offline-catalog",
 "source_version":"test-v1","validated_by":"TEST_FIXTURE_ONLY",
 "facts":{"synthetic:style-a":True,"synthetic:style-b":False}}


class ScopedSyntheticAuthority:
    """CI fixture: never accepted as production identity/consent authority."""
    def __init__(self,cfg):self.cfg=cfg
    def get(self,principal,session_id):
        if (principal.subject!=self.cfg["subject"]
            or principal.issuer!=ISS or session_id!=self.cfg["session_id"]):
            return None
        return {"session_id":session_id,"tenant_id":self.cfg["tenant"],
                "branch_id":self.cfg["branch"],
                "specialist_id":principal.subject,
                "state":"CREATED","state_version":0,
                "service_id":SYNTHETIC_SERVICE}


def _spawned_engine(stage,cfg,output):
    import os
    from abc_foundation.eng02_consultation import ConsultationEngine
    from abc_foundation.eng03_evidence import SyntheticEvidenceEngine
    from abc_foundation.eng14_policy import SyntheticQuestionPolicy
    from abc_foundation.isolated_engine_service import dispatch
    from abc_foundation.oidc import Principal
    from abc_foundation.store import DomainError
    try:
        if (os.environ.get("ABC_ENV") not in (None,"LOCAL_INTEGRATION_ONLY")
            or "media" in cfg or "image" in cfg or "customer_data" in cfg):
            raise DomainError(403,"synthetic_non_media_only")
        principal=Principal(cfg["subject"],ISS)
        if stage in ("ENG-02","ENG-03"):
            eng02=ConsultationEngine(cfg["sqlite_path"],
                  ScopedSyntheticAuthority(cfg))
        if stage=="ENG-02":
            entries=cfg["values"]
            if not isinstance(entries,list) or len(entries)>4:
                raise DomainError(400,"synthetic_answer_budget_invalid")
            policy=SyntheticQuestionPolicy()
            answers={}
            receipts=[]
            for i,value in enumerate(entries):
                state=eng02.next(principal,cfg["session_id"])
                question=state.get("next_question")
                if question is None:
                    raise DomainError(409,"eng14_no_more_questions")
                qid=question["question_id"]
                decision=policy.evaluate(command_id=str(uuid.uuid4()),
                   tenant_id=cfg["tenant"],session_id=cfg["session_id"],
                   service_id=SYNTHETIC_SERVICE,state="CREATED",
                   answers=answers,question_id=qid,expected_question=qid,
                   profile_version=question["profile_version"])
                policy.require_allow(decision)
                receipt=eng02.record(principal,cfg["session_id"],
                    question_id=qid,value=value,source="CLIENT",
                    operation_key="ci-nonmedia-"+str(i)+"-"+cfg["session_id"])
                answers[qid]=value
                receipts.append(receipt)
            result={"readiness":eng02.next(principal,cfg["session_id"])["readiness"],
                    "answer_ids":[x["answer_id"] for x in receipts],
                    "policy_evaluations":len(receipts),
                    "media_received":False}
        elif stage=="ENG-03":
            result=SyntheticEvidenceEngine(eng02).collect_non_media(
                principal,cfg["session_id"])
        elif stage in ("ENG-04","ENG-05","ENG-06"):
            msg={"request_id":str(uuid.uuid4()),"engine_id":stage,
                "contract_version":cfg.get("contract_version",VERSION),
                "consumer_id":cfg.get("consumer_id",CONSUMER),
                "session_id":cfg["session_id"],"payload":cfg["payload"]}
            result=dispatch(msg,stage)
            if result.get("release_approved") is not False:
                raise DomainError(403,"synthetic_release_forbidden")
        else:
            raise DomainError(403,"invalid_process_owner")
        output.put({"engine_id":stage,"pid":os.getpid(),
                    "result":result,"release_approved":False})
    except BaseException as exc:
        output.put({"engine_id":stage,"pid":os.getpid(),"error":
                    getattr(exc,"code",type(exc).__name__),
                    "release_approved":False})


class FiveIndependentProcessSyntheticChain(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="abc-a2-5-proc-")
        self.addCleanup(temp.cleanup)
        sid=str(uuid.uuid4())
        self.cfg={"session_id":sid,"tenant":"ci-tenant-"+sid[:8],
                  "branch":"ci-branch-"+sid[:8],
                  "subject":"ci-specialist-"+sid[:8],
                  "sqlite_path":str(Path(temp.name)/"eng02-answers.sqlite")}
        self.pids=[]
        self.invocations=[]
        self.ctx=mp.get_context("spawn")

    def stage(self,engine,**params):
        cfg={**self.cfg,**params}
        queue=self.ctx.Queue()
        p=self.ctx.Process(target=_spawned_engine,args=(engine,cfg,queue),
                           name="ABC-A2-"+engine)
        p.start()
        try:
            result=queue.get(timeout=14)
            p.join(timeout=3)
            if p.is_alive():
                p.terminate()
                p.join(timeout=3)
                self.fail(engine+" child did not shut down")
            self.assertEqual(p.exitcode,0,(engine,result))
            self.assertEqual(result["engine_id"],engine)
            self.assertFalse(result["release_approved"])
            self.assertNotEqual(result["pid"],os.getpid())
            self.pids.append(result["pid"])
            self.invocations.append(engine)
            return result
        finally:
            if p.is_alive():
                p.kill()
                p.join(timeout=3)
            queue.close()
            queue.join_thread()

    def complete(self,values=("NO","NO","SUBTLE","LOW"),fixture=FIXTURE):
        e2=self.stage("ENG-02",values=list(values))
        e3=self.stage("ENG-03")
        e4=self.stage("ENG-04",payload={"evidence":e3["result"]})
        e5=self.stage("ENG-05",payload={"service_id":SYNTHETIC_SERVICE,
                                        "fixture":fixture})
        e6=self.stage("ENG-06",payload={"analysis":e4["result"]["result"],
                                        "knowledge":e5["result"]["result"]})
        return e2,e3,e4,e5,e6

    def test_01_full_five_process_chain_is_synthetic_only(self):
        a,b,c,d,e=self.complete()
        self.assertEqual(self.invocations,
            ["ENG-02","ENG-03","ENG-04","ENG-05","ENG-06"])
        # PIDs can in principle be reused after sequential process exit;
        # process instance identity is proved by actual spawn plus exitcode.
        self.assertEqual(a["result"]["readiness"],"READY_FOR_RECOMMENDATION")
        self.assertEqual(a["result"]["policy_evaluations"],4)
        self.assertFalse(a["result"]["media_received"])
        self.assertEqual(len(b["result"]),4)
        self.assertTrue(all(x["evidence_class"]=="USER_REPORTED"
                            for x in b["result"]))
        analysis=c["result"]["result"]
        self.assertEqual(set(analysis["evidence_ids"]),
                         {x["evidence_id"] for x in b["result"]})
        decision=e["result"]["result"]
        self.assertEqual(decision["session_id"],self.cfg["session_id"])
        self.assertEqual(len(decision["candidates"]),1)
        self.assertEqual(decision["candidates"][0]["feasibility_label"],
                         "PROFESSIONAL_CHECK_REQUIRED")
        self.assertEqual(decision["candidates"][0]["candidate_id"],
                         "synthetic:style-a")
        self.assertFalse(e["result"]["release_approved"])

    def test_02_unknown_critical_answer_stops_question_and_candidate(self):
        a,b,c,d,e=self.complete(values=("UNKNOWN",))
        self.assertEqual(a["result"]["readiness"],"PROFESSIONAL_CHECK_REQUIRED")
        self.assertEqual(e["result"]["result"]["candidates"],[])

    def test_03_reported_sensitivity_stops_question_and_candidate(self):
        a,b,c,d,e=self.complete(values=("NO","YES"))
        self.assertEqual(a["result"]["readiness"],"PROFESSIONAL_CHECK_REQUIRED")
        self.assertEqual(e["result"]["result"]["candidates"],[])

    def test_04_no_professional_knowledge_yields_no_candidate(self):
        _,_,_,e5,e6=self.complete(fixture=None)
        self.assertIn("SOURCE_UNVERIFIED",e5["result"]["result"]["unknowns"])
        self.assertEqual(e6["result"]["result"]["candidates"],[])

    def test_05_wrong_session_evidence_rejected_before_eng05_or_eng06(self):
        self.stage("ENG-02",values=["NO","NO","SUBTLE","LOW"])
        ev=self.stage("ENG-03")["result"]
        ev[0]["session_id"]=str(uuid.uuid4())
        resp=self.stage("ENG-04",payload={"evidence":ev})
        self.assertIn("error",resp)
        self.assertEqual(self.invocations[-1],"ENG-04")

    def test_06_forged_professional_source_rejected_before_eng06(self):
        bad={**FIXTURE,"validated_by":"external_fake_expert"}
        response=self.stage("ENG-05",payload={
            "service_id":SYNTHETIC_SERVICE,"fixture":bad})
        self.assertEqual(response["error"],"unverified_knowledge_source")

    def test_07_cross_session_analysis_denied_by_eng06(self):
        self.stage("ENG-02",values=["NO","NO","SUBTLE","LOW"])
        ev=self.stage("ENG-03")["result"]
        e4=self.stage("ENG-04",payload={"evidence":ev})
        e5=self.stage("ENG-05",payload={
            "service_id":SYNTHETIC_SERVICE,"fixture":FIXTURE})
        wrong={**e4["result"]["result"],"session_id":str(uuid.uuid4())}
        e6=self.stage("ENG-06",payload={"analysis":wrong,
                                        "knowledge":e5["result"]["result"]})
        self.assertEqual(e6["error"],"cross_session_engine_input")

    def test_08_injected_media_is_denied_before_eng02_storage(self):
        result=self.stage("ENG-02",values=[],media="FAKE-MEDIA")
        self.assertEqual(result["error"],"synthetic_non_media_only")
        self.assertFalse(Path(self.cfg["sqlite_path"]).exists())

    def test_09_bad_contract_version_denied_by_independent_engine(self):
        result=self.stage("ENG-05",contract_version="unapproved-v3",
                  payload={"service_id":SYNTHETIC_SERVICE,"fixture":FIXTURE})
        self.assertIn(result["error"],("invalid_engine_service_contract",
                                     "engine_port_json_schema_rejected"))

    def test_10_wrong_consumer_is_denied_by_independent_schema(self):
        result=self.stage("ENG-05",consumer_id="",
                  payload={"service_id":SYNTHETIC_SERVICE,"fixture":FIXTURE})
        self.assertEqual(result["error"],"invalid_engine_service_contract")


if __name__=="__main__":unittest.main()

"""ENG02 synthetic-only golden scenarios and negative security tests."""
import json
from pathlib import Path
import tempfile
import uuid
import unittest
from concurrent.futures import ThreadPoolExecutor

from abc_foundation.eng02_consultation import ConsultationEngine,SYNTHETIC_SERVICE,FIXTURE_PATH
from abc_foundation.oidc import Principal
from abc_foundation.store import DomainError

ISS="https://identity.example.test/realms/abc"

class ScopeStore:
    def __init__(self):
        self.sid=str(uuid.uuid4())
        self.principal=Principal("specialist-a",ISS)
        self.tenant="tenant-a"
        self.branch="branch-a"
        self.state="CREATED"
        self.service=SYNTHETIC_SERVICE
    def get(self,p,sid):
        if p!=self.principal or sid!=self.sid:
            raise DomainError(404,"not_found")
        return {"session_id":self.sid,"tenant_id":self.tenant,"branch_id":self.branch,
                "specialist_id":self.principal.subject,"state":self.state,
                "service_id":self.service}


class ConsultationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=self.temp.name+"/eng02.sqlite"
        self.scope=ScopeStore()
        self.e=ConsultationEngine(self.path,self.scope)
        self.p=self.scope.principal
        self.sid=self.scope.sid

    def question(self):
        return self.e.next(self.p,self.sid)["next_question"]

    def record(self,value,source="CLIENT",key=None):
        q=self.question()
        return self.e.record(self.p,self.sid,question_id=q["question_id"],
                             value=value,source=source,operation_key=key or "answer-"+uuid.uuid4().hex)

    def test_critical_questions_first_and_profile_schema(self):
        self.assertEqual(self.question()["question_id"],"synthetic:prior-treatment")
        self.record("NO")
        self.assertEqual(self.question()["question_id"],"synthetic:sensitivity")
        self.record("NO")
        self.assertEqual(self.question()["question_id"],"synthetic:desired-goal")
        self.record("SUBTLE")
        self.assertEqual(self.question()["question_id"],"synthetic:maintenance")
        self.record("LOW")
        result=self.e.next(self.p,self.sid)
        self.assertEqual(result["readiness"],"READY_FOR_RECOMMENDATION")
        self.assertIsNone(result["next_question"])
        snapshot=self.e.profile_snapshot(self.p,self.sid)
        self.assertEqual(len(snapshot["answer_ids"]),4)
        self.assertEqual(snapshot["evidence_ids"],[])
        self.assertEqual(snapshot["service_id"],SYNTHETIC_SERVICE)

    def test_unknown_prior_treatment_requires_specialist(self):
        self.record("UNKNOWN")
        result=self.e.next(self.p,self.sid)
        self.assertEqual(result["readiness"],"PROFESSIONAL_CHECK_REQUIRED")
        self.assertIn("prior_treatment",result["critical_unknown_keys"])
        self.assertIsNone(result["next_question"])
        with self.assertRaises(DomainError):
            self.e.record(self.p,self.sid,question_id="synthetic:sensitivity",
                          value="NO",source="CLIENT",operation_key="answer-after-unknown")

    def test_sensitivity_flag_is_escalated_never_auto_diagnosed(self):
        self.record("YES" if False else "NO")
        self.record("YES")
        result=self.e.next(self.p,self.sid)
        self.assertEqual(result["readiness"],"PROFESSIONAL_CHECK_REQUIRED")
        self.assertIn("sensitivity_flag",result["critical_unknown_keys"])
        self.assertIsNone(result["next_question"])

    def test_idempotent_replay_returns_same_answer_record(self):
        q=self.question()
        args={"question_id":q["question_id"],"value":"NO","source":"CLIENT",
              "operation_key":"answer-same-id"}
        a=self.e.record(self.p,self.sid,**args)
        b=self.e.record(self.p,self.sid,**args)
        self.assertEqual(a,b)
        with self.assertRaises(DomainError) as ctx:
            self.e.record(self.p,self.sid,**{**args,"value":"YES"})
        self.assertEqual(ctx.exception.code,"idempotency_payload_conflict")

    def test_second_key_cannot_silently_rewrite_answer(self):
        self.record("NO",key="answer-first-one")
        with self.assertRaises(DomainError) as ctx:
            self.e.record(self.p,self.sid,question_id="synthetic:prior-treatment",
                          value="YES",source="CLIENT",operation_key="answer-second-one")
        self.assertEqual(ctx.exception.status,409)
        self.assertEqual(self.e.profile_snapshot(self.p,self.sid)["answer_ids"].__len__(),1)

    def test_wrong_question_order_denied(self):
        with self.assertRaises(DomainError) as ctx:
            self.e.record(self.p,self.sid,question_id="synthetic:maintenance",
                          value="LOW",source="CLIENT",operation_key="answer-out-of-order")
        self.assertEqual(ctx.exception.code,"question_sequence_or_safety_block")

    def test_invalid_value_and_source_denied(self):
        q=self.question()
        for value,source in (("diagnose-me","CLIENT"),("NO","SYSTEM"),(None,"CLIENT"),("no","CLIENT")):
            with self.subTest(value=value,source=source),self.assertRaises(DomainError):
                self.e.record(self.p,self.sid,question_id=q["question_id"],
                              value=value,source=source,operation_key="bad-value-01")

    def test_revoked_or_cross_tenant_identity_denied(self):
        with self.assertRaises(DomainError):
            self.e.next(Principal("another-specialist",ISS),self.sid)
        with self.assertRaises(DomainError):
            self.e.next(self.p,str(uuid.uuid4()))
        with self.assertRaises(DomainError):
            self.e.next(None,self.sid)

    def test_no_real_service_or_paused_session_allowed(self):
        self.scope.service="actual-hair-color"
        with self.assertRaises(DomainError):
            self.e.next(self.p,self.sid)
        self.scope.service=SYNTHETIC_SERVICE
        self.scope.state="PAUSED"
        with self.assertRaises(DomainError):
            self.e.next(self.p,self.sid)

    def test_restart_persists_order_and_same_receipt(self):
        q=self.question()
        a=self.e.record(self.p,self.sid,question_id=q["question_id"],value="NO",
                        source="SPECIALIST",operation_key="durable-record1")
        second=ConsultationEngine(self.path,self.scope)
        self.assertEqual(second.next(self.p,self.sid)["next_question"]["question_id"],"synthetic:sensitivity")
        b=second.record(self.p,self.sid,question_id=q["question_id"],value="NO",
                        source="SPECIALIST",operation_key="durable-record1")
        self.assertEqual(a,b)

    def test_concurrent_same_command_writes_one_receipt(self):
        q=self.question()
        def call(_):
            return self.e.record(self.p,self.sid,question_id=q["question_id"],value="NO",
                       source="CLIENT",operation_key="race-key-123")
        with ThreadPoolExecutor(max_workers=4) as exe:
            rows=list(exe.map(call,range(4)))
        self.assertTrue(all(x==rows[0] for x in rows))
        self.assertEqual(len(self.e.profile_snapshot(self.p,self.sid)["answer_ids"]),1)

    def test_no_real_client_question_profile_allowed(self):
        cfg=json.loads(FIXTURE_PATH.read_text())
        cfg["profiles"][0]["enabled_for_real_clients"]=True
        with self.assertRaises(ValueError):
            ConsultationEngine(self.path,self.scope,cfg)

    def test_duplicate_or_malformed_question_registry_rejected(self):
        cfg=json.loads(FIXTURE_PATH.read_text())
        cfg["profiles"][0]["questions"].append(dict(cfg["profiles"][0]["questions"][0]))
        with self.assertRaises(ValueError):
            ConsultationEngine(self.path,self.scope,cfg)
        cfg=json.loads(FIXTURE_PATH.read_text())
        cfg["profiles"][0]["questions"][0]["priority"]=True
        with self.assertRaises(ValueError):
            ConsultationEngine(self.path,self.scope,cfg)

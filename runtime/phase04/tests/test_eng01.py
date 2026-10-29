"""ENG01 runtime tests against contract snapshot, fake scoped adapter and real PG."""
import os
from types import SimpleNamespace
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor

from abc_foundation.eng01_orchestrator import WorkflowMachine,OrchestrationEngine
from abc_foundation.oidc import Principal
from abc_foundation.pg_store import PostgresStore
from abc_foundation.store import DomainError

ISS="https://identity.example.test/realms/abc"
POSTGRES_DSN=os.getenv("ABC_TEST_PG_DSN")
POSTGRES_ADMIN=os.getenv("ABC_TEST_PG_ADMIN_DSN")


class StubStore:
    def __init__(self,state="CREATED",version=0):
        self.sid=str(uuid.uuid4())
        self.tenant="tenant-a"
        self.branch="branch-a"
        self.subject="staff-a"
        self.state=state
        self.version=version
        self.receipts={}
        self.calls=0
    @staticmethod
    def _key(key):
        if not isinstance(key,str) or not 8<=len(key)<=128:
            raise DomainError(400,"invalid_idempotency_key")
    def get(self,p,sid):
        if (sid!=self.sid or p.subject!=self.subject or p.issuer!=ISS):
            raise DomainError(404,"not_found")
        return dict(session_id=self.sid,tenant_id=self.tenant,branch_id=self.branch,
                    specialist_id=self.subject,state=self.state,state_version=self.version)
    def checkpoint_command(self,p,sid,action,expected,key):
        self.calls+=1
        self.get(p,sid)
        intent=(action,expected)
        if key in self.receipts:
            old,result=self.receipts[key]
            if intent!=old:
                raise DomainError(409,"idempotency_payload_conflict")
            return result.copy()
        if self.state!="CREATED" or self.version!=expected or action!="pause":
            raise DomainError(409,"state_version_conflict")
        self.state="PAUSED"
        self.version+=1
        result=self.get(p,sid)
        self.receipts[key]=(intent,result)
        return result.copy()


class Eng01Contracts(unittest.TestCase):
    def setUp(self):
        self.store=StubStore()
        self.p=Principal("staff-a",ISS)
        self.orch=OrchestrationEngine(self.store)

    def test_canonic_machine_is_20_states_and_102_edges(self):
        m=self.orch.machine
        self.assertEqual(len(m.states),20)
        self.assertEqual(m.transition_count,102)
        self.assertEqual(m.initial,"CREATED")
        self.assertTrue({"CLOSED","CANCELLED"}<=m.terminal)

    def test_next_actions_are_explainable_and_never_autonomous(self):
        info=self.orch.inspect(self.p,self.store.sid)
        self.assertEqual(info["state"],"CREATED")
        self.assertEqual(info["state_version"],0)
        self.assertEqual(info["publication_status"],"INTERNAL_SYNTHETIC_ONLY")
        self.assertEqual({x["to_state"] for x in info["available_next_actions"]},
                         {"CONSENTED","CANCELLED","PAUSED","SAFETY_BLOCKED"})
        pause=next(x for x in info["available_next_actions"] if x["to_state"]=="PAUSED")
        self.assertEqual(pause["readiness"],"INTERNAL_PAUSE_IMPLEMENTED")
        self.assertEqual(pause["required_guards"],["authenticated_actor","persist_checkpoint"])
        self.assertEqual(next(x for x in info["available_next_actions"]
                             if x["to_state"]=="SAFETY_BLOCKED")["readiness"],
                         "ENGINE_DEPENDENCY_UNAVAILABLE")

    def test_guarded_business_transition_never_executes(self):
        for target in ("CONSENTED","INTENT_DEFINED","CANCELLED","HANDOFF","LOOK_SELECTED",
                       "CLOSED","SAFETY_BLOCKED"):
            with self.subTest(target=target),self.assertRaises(DomainError) as ctx:
                self.orch.perform_checkpoint(self.p,self.store.sid,target_state=target,
                    expected_state_version=0,idempotency_key="valid-idempotency-key")
            self.assertEqual(ctx.exception.status,501)
        self.assertEqual(self.store.calls,0)

    def test_pause_executes_once_and_can_replay_same_command(self):
        def call():
            return self.orch.perform_checkpoint(self.p,self.store.sid,target_state="PAUSED",
                    expected_state_version=0,idempotency_key="checkpoint-valid-01")
        a=call()
        b=call()
        self.assertEqual(a,b)
        self.assertEqual(self.store.version,1)
        self.assertEqual(a["state"],"PAUSED")
        self.assertEqual(a["status"],"DURABLE_CHECKPOINT_COMMITTED")
        self.assertEqual(self.store.calls,2)

    def test_duplicate_different_key_rejects_stale(self):
        self.orch.perform_checkpoint(self.p,self.store.sid,target_state="PAUSED",
                                     expected_state_version=0,idempotency_key="checkpoint-first")
        with self.assertRaises(DomainError) as ctx:
            self.orch.perform_checkpoint(self.p,self.store.sid,target_state="PAUSED",
                                     expected_state_version=0,idempotency_key="checkpoint-second")
        self.assertEqual(ctx.exception.status,409)

    def test_stale_expected_version_rejected(self):
        with self.assertRaises(DomainError) as ctx:
            self.orch.perform_checkpoint(self.p,self.store.sid,target_state="PAUSED",
                    expected_state_version=99,idempotency_key="checkpoint-stale")
        self.assertEqual(ctx.exception.status,409)
        self.assertEqual(self.store.calls,0)

    def test_noninteger_and_bool_version_rejected(self):
        for version in (-1,True,0.0,"0",None):
            with self.subTest(version=version),self.assertRaises(DomainError) as ctx:
                self.orch.perform_checkpoint(self.p,self.store.sid,target_state="PAUSED",
                     expected_state_version=version,idempotency_key="checkpoint-version")
            self.assertEqual(ctx.exception.status,400)

    def test_malformed_or_external_actor_denied(self):
        for principal in (None,{},SimpleNamespace(subject="staff-a",issuer="http://malicious"),
                          Principal("other-staff",ISS),Principal("staff-a","https://wrong.test")):
            with self.subTest(principal=principal),self.assertRaises(DomainError):
                self.orch.inspect(principal,self.store.sid)

    def test_unknown_or_bad_session_does_not_enumerate(self):
        for sid in ("not-uuid",str(uuid.uuid4()),None):
            with self.subTest(sid=sid),self.assertRaises(DomainError) as ctx:
                self.orch.inspect(self.p,sid)
            self.assertEqual(ctx.exception.status,404)

    def test_terminal_has_no_edges_and_illegal_transition_denied(self):
        self.store.state="CANCELLED"
        self.assertTrue(self.orch.inspect(self.p,self.store.sid)["terminal"])
        self.assertEqual(self.orch.inspect(self.p,self.store.sid)["available_next_actions"],[])
        with self.assertRaises(DomainError) as ctx:
            self.orch.machine.edge("CANCELLED","CREATED")
        self.assertEqual(ctx.exception.status,409)

    def test_resume_is_explicitly_disabled_until_atomic_policy_gate(self):
        self.store.state="PAUSED"
        self.store.version=1
        info=self.orch.inspect(self.p,self.store.sid)
        resume=next(x for x in info["available_next_actions"] if x["to_state"]=="CREATED")
        self.assertIn("consent_still_sufficient",resume["required_guards"])
        self.assertEqual(resume["readiness"],"REQUIRES_AUTHORIZED_GUARDS_AND_IMPLEMENTATION")
        with self.assertRaises(DomainError) as ctx:
            self.orch.perform_checkpoint(self.p,self.store.sid,target_state="CREATED",
                    expected_state_version=1,idempotency_key="checkpoint-resume")
        self.assertEqual(ctx.exception.status,501)

    def test_contract_rejects_duplicate_edge(self):
        import json
        from pathlib import Path
        path=Path(__file__).resolve().parents[1]/"abc_foundation/eng01_consultation_machine.json"
        payload=json.loads(path.read_text())
        payload["transitions"].append(dict(payload["transitions"][0]))
        with self.assertRaises(ValueError):
            WorkflowMachine(payload)

    def test_contract_rejects_unknown_guardless_or_terminal_edge(self):
        import json
        from pathlib import Path
        path=Path(__file__).resolve().parents[1]/"abc_foundation/eng01_consultation_machine.json"
        payload=json.loads(path.read_text())
        payload["transitions"][0]["guards"]=[]
        with self.assertRaises(ValueError):
            WorkflowMachine(payload)
        payload=json.loads(path.read_text())
        payload["transitions"][0]["from"]="CLOSED"
        with self.assertRaises(ValueError):
            WorkflowMachine(payload)

    def test_malicious_store_scope_mismatch_does_not_return_data(self):
        real=self.store.get
        def fake(p,sid):
            d=real(p,sid)
            d["specialist_id"]="attacker"
            return d
        self.store.get=fake
        with self.assertRaises(DomainError) as ctx:
            self.orch.inspect(self.p,self.store.sid)
        self.assertEqual(ctx.exception.status,403)

    def test_malicious_checkpoint_postcondition_is_detected(self):
        def malicious(p,sid,action,version,key):
            d=self.store.get(p,sid)
            return {**d,"state":"CONSENTED","state_version":1}
        self.store.checkpoint_command=malicious
        with self.assertRaises(DomainError) as ctx:
            self.orch.perform_checkpoint(self.p,self.store.sid,target_state="PAUSED",
                expected_state_version=0,idempotency_key="checkpoint-invalid-postcondition")
        self.assertEqual(ctx.exception.status,500)


@unittest.skipUnless(POSTGRES_DSN and POSTGRES_ADMIN,"requires CI disposable PostgreSQL")
class Eng01PostgresIntegration(unittest.TestCase):
    def setUp(self):
        import psycopg
        key=uuid.uuid4().hex[:14]
        self.tenant="eng01-tenant-"+key
        self.branch="eng01-branch-"+key
        self.subject="eng01-specialist-"+key
        self.p=Principal(self.subject,ISS)
        self.store=PostgresStore(POSTGRES_DSN)
        self.engine=OrchestrationEngine(self.store)
        with psycopg.connect(POSTGRES_ADMIN) as con:
            con.execute("INSERT INTO abc.tenants(tenant_id) VALUES(%s)",(self.tenant,))
            con.execute("INSERT INTO abc.branches(tenant_id,branch_id) VALUES(%s,%s)",
                        (self.tenant,self.branch))
            con.execute("""INSERT INTO abc.memberships
                  (issuer,subject,tenant_id,branch_id,role,active,verified_qualification)
                  VALUES(%s,%s,%s,%s,'SPECIALIST',true,false)""",
                        (ISS,self.subject,self.tenant,self.branch))
        s=self.store.create(self.p,{"branch_id":self.branch,
                          "scope":"IN_SALON_SHARED_SCREEN"},"eng01-create-"+key)
        self.sid=s["session_id"]

    def call(self,key="eng01-pause-0001"):
        return self.engine.perform_checkpoint(self.p,self.sid,target_state="PAUSED",
                       expected_state_version=0,idempotency_key=key)

    def test_pg_real_engine_pause_receipt_and_audit(self):
        import psycopg
        a=self.call()
        self.assertEqual(a,self.call())
        self.assertEqual(self.engine.inspect(self.p,self.sid)["state"],"PAUSED")
        with psycopg.connect(POSTGRES_ADMIN) as con:
            record=con.execute("SELECT from_state,to_state,from_version,to_version FROM abc.state_audit WHERE session_id=%s",
                               (self.sid,)).fetchall()
        self.assertEqual(record,[("CREATED","PAUSED",0,1)])

    def test_pg_concurrent_pause_attempts_one_version(self):
        import psycopg
        with ThreadPoolExecutor(max_workers=4) as executor:
            rows=list(executor.map(lambda _:self.call("eng01-concurrent-key"),range(4)))
        self.assertTrue(all(row==rows[0] for row in rows))
        with psycopg.connect(POSTGRES_ADMIN) as con:
            audit_count=con.execute("SELECT count(*) FROM abc.state_audit WHERE session_id=%s",
                                    (self.sid,)).fetchone()[0]
        self.assertEqual(audit_count,1)

    def test_pg_wrong_tenant_or_revoked_specialist_denied(self):
        import psycopg
        with self.assertRaises(DomainError):
            self.engine.inspect(Principal("attacker",ISS),self.sid)
        with psycopg.connect(POSTGRES_ADMIN) as con:
            con.execute("UPDATE abc.memberships SET active=false WHERE subject=%s",
                        (self.subject,))
        with self.assertRaises(DomainError):
            self.call()

    def test_pg_stale_retry_with_different_key_rejected(self):
        self.call("eng01-key-one")
        with self.assertRaises(DomainError) as ctx:
            self.call("eng01-key-two")
        self.assertEqual(ctx.exception.status,409)

"""ENG14 all canonical transition edges and independent DB state policy gate."""
import os
import uuid
import unittest
import psycopg
from abc_foundation.eng01_orchestrator import WorkflowMachine
from abc_foundation.eng14_transition_policy import ENG14TransitionPolicy
from abc_foundation.oidc import Principal
from abc_foundation.pg_store import PostgresStore
from abc_foundation.store import DomainError

ISS="https://identity.example.test/abc"
ADMIN=os.getenv("ABC_TEST_PG_ADMIN_DSN")
APP=os.getenv("ABC_TEST_PG_DSN")


class ENG14AllTransitions(unittest.TestCase):
    def test_all_102_edges_get_explicit_block_or_allow(self):
        policy=ENG14TransitionPolicy()
        graph=WorkflowMachine.load()
        approved=[]
        n=0
        for state in sorted(graph.states):
            for edge in graph.edges(state):
                n+=1
                decision=policy.evaluate(from_state=state,to_state=edge.to_state,
                     actor=edge.actor,expected_version=0)
                self.assertIn(decision["decision"],("ALLOW","BLOCK"))
                if decision["decision"]=="ALLOW":
                    approved.append((state,edge.to_state))
                    policy.require_allowed(decision)
                else:
                    with self.assertRaises(DomainError):
                        policy.require_allowed(decision)
        self.assertEqual(n,102)
        self.assertEqual(approved,[("CREATED","PAUSED")])

    def test_actor_forgery_never_authorizes_pause(self):
        p=ENG14TransitionPolicy()
        d=p.evaluate(from_state="CREATED",to_state="PAUSED",actor="ENG-14",expected_version=0)
        with self.assertRaises(DomainError):
            p.require_allowed(d)

    def test_unsupported_transition_cannot_be_claimed(self):
        with self.assertRaises(DomainError):
            ENG14TransitionPolicy().evaluate(from_state="CREATED",to_state="CLOSED",
                                               actor="SPECIALIST",expected_version=0)

    def test_bogus_policy_receipt_rejected(self):
        with self.assertRaises(DomainError):
            ENG14TransitionPolicy().require_allowed({
                 "decision":"ALLOW","policy_version":"eng14.state.synthetic.1",
                 "reason":"SYNTHETIC_S0_CHECKPOINT_ONLY",
                 "source_state":"PAUSED","target_state":"CREATED"})

@unittest.skipUnless(APP and ADMIN,"PostgreSQL16 integration only")
class ENG14DatabaseGate(unittest.TestCase):
    def setUp(self):
        suffix=uuid.uuid4().hex[:12]
        self.t="eng14-state-"+suffix
        self.b="eng14-branch-"+suffix
        self.s="eng14-specialist-"+suffix
        self.p=Principal(self.s,ISS)
        with psycopg.connect(ADMIN) as con:
            con.execute("INSERT INTO abc.tenants(tenant_id) VALUES(%s)",(self.t,))
            con.execute("INSERT INTO abc.branches(tenant_id,branch_id) VALUES(%s,%s)",(self.t,self.b))
            con.execute("""INSERT INTO abc.memberships(issuer,subject,tenant_id,branch_id,role,active)
                VALUES(%s,%s,%s,%s,'SPECIALIST',true)""",(ISS,self.s,self.t,self.b))
        self.store=PostgresStore(APP)
        self.sid=self.store.create(self.p,{"branch_id":self.b,
             "scope":"IN_SALON_SHARED_SCREEN","service_id":"synthetic:hair-color"},
             "guard-"+suffix)["session_id"]

    def test_untrusted_direct_state_update_rejected(self):
        # Direct state writes are now unconditionally forbidden at SQL GRANT
        # level, even before RLS and state trigger are reached.
        with psycopg.connect(APP) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("""UPDATE abc.sessions SET state='PAUSED',
                    state_version=1,checkpoint='CREATED'
                    WHERE session_id=%s""",(self.sid,))
        self.assertEqual(self.store.get(self.p,self.sid)["state"],"CREATED")

    def test_state_pause_approved_only_after_verified_membership_and_audited(self):
        r=self.store.checkpoint_command(self.p,self.sid,"pause",0,"valid-pause-once")
        self.assertEqual(r["state"],"PAUSED")
        with psycopg.connect(ADMIN) as con:
            a=con.execute("""SELECT source_state,target_state,from_version,to_version,
                   result,guard_version FROM abc.eng14_state_guard_audit
                   WHERE session_id=%s""",(self.sid,)).fetchone()
        self.assertEqual(a,("CREATED","PAUSED",0,1,
               "ALLOW_SYNTHETIC_PAUSE_S0","eng14.state.synthetic.1"))
        replay=self.store.checkpoint_command(self.p,self.sid,"pause",0,"valid-pause-once")
        self.assertEqual(replay["state_version"],1)
        with psycopg.connect(ADMIN) as con:
            self.assertEqual(con.execute("""SELECT count(*) FROM abc.eng14_state_guard_audit
                   WHERE session_id=%s""",(self.sid,)).fetchone()[0],1)

    def test_paused_resume_denied_even_with_forged_db_scope(self):
        self.store.checkpoint_command(self.p,self.sid,"pause",0,"valid-pause-once")
        with psycopg.connect(APP) as con:
            for k,v in (("abc.issuer",ISS),("abc.subject",self.s),
                        ("abc.tenant",self.t),("abc.branch",self.b)):
                con.execute("SELECT set_config(%s,%s,true)",(k,v))
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("""UPDATE abc.sessions SET state='CREATED',
                       checkpoint=NULL,state_version=state_version+1
                       WHERE session_id=%s""",(self.sid,))
        self.assertEqual(self.store.get(self.p,self.sid)["state"],"PAUSED")

    def test_forged_custom_guc_cannot_grant_direct_state_update(self):
        # Simulate stolen abc_app DB credentials with spoofed valid GUC values.
        # SQL privilege boundary must still block state UPDATE.
        with psycopg.connect(APP) as con:
            for key,val in (("abc.issuer",ISS),("abc.subject",self.s),
                            ("abc.tenant",self.t),("abc.branch",self.b)):
                con.execute("SELECT set_config(%s,%s,true)",(key,val))
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("""UPDATE abc.sessions SET state='PAUSED',
                    checkpoint='CREATED',state_version=1
                    WHERE session_id=%s""",(self.sid,))
        self.assertEqual(self.store.get(self.p,self.sid)["state"],"CREATED")

    def test_revoked_specialist_cannot_mutate(self):
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.memberships SET active=false
                        WHERE issuer=%s AND subject=%s AND tenant_id=%s""",
                        (ISS,self.s,self.t))
        with self.assertRaises(DomainError):
            self.store.checkpoint_command(self.p,self.sid,"pause",0,"no-longer-authorized")
        with psycopg.connect(ADMIN) as con:
            self.assertEqual(con.execute("""SELECT count(*) FROM abc.eng14_state_guard_audit
                 WHERE session_id=%s""",(self.sid,)).fetchone()[0],0)

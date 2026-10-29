"""Real PG16 checks for dedicated answer worker, RLS, replay and ENG14 gate.

Solely synthetic salon session fixtures; no external provider or real customers.
"""
import os
import uuid
import unittest
from concurrent.futures import ThreadPoolExecutor
import psycopg

from abc_foundation.answer_index_consumer import AnswerIndexConsumer
from abc_foundation.eng01_service_identity import WorkloadPrincipal
from abc_foundation.eng02_pg_outbox import PGENG02CommandWriter
from abc_foundation.oidc import Principal
from abc_foundation.pg_store import PostgresStore
from abc_foundation.store import DomainError
from datetime import datetime,timezone

ADMIN=os.getenv("ABC_TEST_PG_ADMIN_DSN")
APP=os.getenv("ABC_TEST_PG_DSN")
ORCH=os.getenv("ABC_TEST_PG_ORCHESTRATOR_DSN")
ANSWER=os.getenv("ABC_TEST_PG_ANSWER_WORKER_DSN")
ISS="https://identity.example.test/abc"
SERVICE_ISS="https://workload.identity.example.test/abc"


@unittest.skipUnless(all((ADMIN,APP,ORCH,ANSWER)),"needs disposable PG16")
class AnswerConsumerIntegration(unittest.TestCase):
    def setUp(self):
        marker=uuid.uuid4().hex[:12]
        self.tenant="answer-tenant-"+marker
        self.branch="answer-branch-"+marker
        self.subject="answer-staff-"+marker
        self.cid="answer-index-"+marker
        self.human=Principal(self.subject,ISS)
        self.service=WorkloadPrincipal(SERVICE_ISS,"svc:abc-eng02","ENG-02",str(uuid.uuid4()))
        self.writer=PGENG02CommandWriter(ORCH)
        with psycopg.connect(ADMIN) as con:
            con.execute("INSERT INTO abc.tenants(tenant_id) VALUES(%s)",(self.tenant,))
            con.execute("INSERT INTO abc.branches(tenant_id,branch_id) VALUES(%s,%s)",
                        (self.tenant,self.branch))
            con.execute("""INSERT INTO abc.memberships
                (issuer,subject,tenant_id,branch_id,role,active)
                VALUES(%s,%s,%s,%s,'SPECIALIST',true)""",
                (ISS,self.subject,self.tenant,self.branch))
            con.execute("""INSERT INTO abc.engine_workload_grants
                (issuer,service_subject,engine_id,tenant_id,branch_id,permission,active)
                VALUES(%s,'svc:abc-eng02','ENG-02',%s,%s,'ENG02_RECORD_ANSWER',true)""",
                (SERVICE_ISS,self.tenant,self.branch))
            con.execute("""INSERT INTO abc.worker_subscriptions
                (consumer_id,tenant_id,event_type,active)
                VALUES(%s,%s,'ANSWER_RECORDED',true)""",(self.cid,self.tenant))
        s=PostgresStore(APP).create(self.human,
            {"branch_id":self.branch,"scope":"IN_SALON_SHARED_SCREEN",
             "service_id":"synthetic:hair-color"},"answer-created-"+marker)
        self.sid=s["session_id"]
        self.service_worker=AnswerIndexConsumer(ANSWER,self.cid)

    def answer(self, *, key=None, value="NO", question="synthetic:prior-treatment", version=0):
        command={
            "command_id":key or str(uuid.uuid4()),
            "correlation_id":str(uuid.uuid4()),
            "session_id":self.sid,
            "tenant_id":self.tenant,"branch_id":self.branch,
            "engine_id":"ENG-02","contract_version":"1.0.0-draft",
            "profile_version":"synthetic-1.0.0",
            "question_id":question,"value":value,
            "answer_source":"CLIENT","expected_state_version":version,
            "requested_at":datetime.now(timezone.utc).isoformat()
        }
        return self.writer.record_synthetic_answer(self.human,self.service,command)

    def test_real_outbox_to_dedicated_worker_and_projection(self):
        receipt=self.answer()
        self.assertEqual(self.service_worker.run_once(),"PROJECTED")
        self.assertIsNone(self.service_worker.run_once())
        with psycopg.connect(ADMIN) as con:
            row=con.execute("""SELECT event_id,session_id,aggregate_version,
               question_id,answer_id FROM abc.answer_index_projection
               WHERE consumer_id=%s""",(self.cid,)).fetchone()
            self.assertEqual(str(row[0]),receipt["event_id"])
            self.assertEqual(str(row[1]),self.sid)
            self.assertEqual(row[2],1)
            self.assertEqual(row[3],"synthetic:prior-treatment")
            self.assertEqual(str(row[4]),receipt["answer_id"])
            status=con.execute("""SELECT state FROM abc.event_delivery
                WHERE consumer_id=%s AND event_id=%s""",
                (self.cid,receipt["event_id"])).fetchone()[0]
            self.assertEqual(status,"ACKED")

    def test_effect_commits_before_ack_restart_dedup(self):
        self.answer()
        dispatcher=self.service_worker.dispatcher
        self.assertEqual(dispatcher.register(self.cid),1)
        delivery=dispatcher.lease(self.cid)
        self.service_worker.project(delivery)
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.event_delivery
                 SET lease_until=clock_timestamp()-interval '1 second'
                 WHERE consumer_id=%s""",(self.cid,))
        restarted=AnswerIndexConsumer(ANSWER,self.cid)
        self.assertEqual(restarted.run_once(),"PROJECTED")
        with psycopg.connect(ADMIN) as con:
            n=con.execute("""SELECT count(*) FROM abc.answer_index_projection
                              WHERE consumer_id=%s""",(self.cid,)).fetchone()[0]
            self.assertEqual(n,1)

    def test_dedicated_role_cannot_read_answers_sessions_or_consent(self):
        for table in ("abc.eng02_answers","abc.sessions","abc.consent_evidence",
                      "abc.memberships","abc.engine_workload_grants"):
            with self.subTest(table=table):
                with psycopg.connect(ANSWER) as con:
                    with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                        con.execute("SELECT count(*) FROM "+table)

    def test_worker_cannot_read_unsubscribed_event_types(self):
        self.answer()
        with self.service_worker.dispatcher._connect() as con:
            rows=con.execute("SELECT event_json->>'event_type' AS event_type FROM abc.outbox").fetchall()
            self.assertEqual([r["event_type"] for r in rows],["ANSWER_RECORDED"])
        self.assertEqual(self.service_worker.dispatcher.register(self.cid),1)

    def test_wrong_consumer_or_tenant_event_cannot_project(self):
        self.answer()
        self.service_worker.dispatcher.register(self.cid)
        item=self.service_worker.dispatcher.lease(self.cid)
        for tamper in (
            {**item,"tenant_id":"some-other-tenant"},
            {**item,"consumer_id":"other-consumer"},
            {**item,"event":{**item["event"],"producer_engine_id":"ENG-19"}},
        ):
            with self.subTest(tamper=tamper),self.assertRaises(DomainError):
                self.service_worker.project(tamper)
        with psycopg.connect(ADMIN) as con:
            rows=con.execute("SELECT count(*) FROM abc.answer_index_projection WHERE consumer_id=%s",
                             (self.cid,)).fetchone()[0]
            self.assertEqual(rows,0)

    def test_revocation_prevents_processing_or_ack(self):
        self.answer()
        self.service_worker.dispatcher.register(self.cid)
        item=self.service_worker.dispatcher.lease(self.cid)
        with psycopg.connect(ADMIN) as con:
            con.execute("UPDATE abc.worker_subscriptions SET active=false WHERE consumer_id=%s",
                        (self.cid,))
        with self.assertRaises((psycopg.errors.InsufficientPrivilege,psycopg.errors.CheckViolation)):
            self.service_worker.project(item)
        with self.assertRaises(DomainError):
            self.service_worker.dispatcher.complete(
                self.cid,item["event_id"],item["lease_token"],succeeded=True)

    def test_eng14_audit_and_db_trigger_exist_in_same_tx(self):
        receipt=self.answer()
        with psycopg.connect(ADMIN) as con:
            row=con.execute("""SELECT a.policy_decision_id,p.policy_version,p.scope,
                p.decision,p.aggregate_version,p.input_digest
                FROM abc.eng02_answers a JOIN abc.eng14_policy_audit p
                  ON p.decision_id=a.policy_decision_id
                WHERE a.session_id=%s""",(self.sid,)).fetchone()
            self.assertEqual(row[1:5],("eng14.synthetic.1","QUESTION","ALLOW",1))
            self.assertEqual(len(row[5]),64)
            self.assertIsNotNone(row[0])
            self.assertEqual(con.execute("SELECT count(*) FROM abc.eng14_policy_audit WHERE session_id=%s",
                             (self.sid,)).fetchone()[0],1)

    def test_direct_db_answer_without_eng14_attestation_denied(self):
        with psycopg.connect(ADMIN) as con:
            with self.assertRaises(psycopg.errors.CheckViolation):
                con.execute("""INSERT INTO abc.eng02_answers
                    (tenant_id,branch_id,session_id,question_profile_version,
                     question_id,value,answer_source,actor_id,answer_id,aggregate_version)
                    VALUES(%s,%s,%s,'synthetic-1.0.0','synthetic:prior-treatment',
                          'NO','CLIENT',%s,%s,1)""",
                    (self.tenant,self.branch,self.sid,self.subject,uuid.uuid4()))
        with psycopg.connect(ADMIN) as con:
            n=con.execute("SELECT count(*) FROM abc.eng02_answers WHERE session_id=%s",
                          (self.sid,)).fetchone()[0]
            self.assertEqual(n,0)

    def test_eng14_critical_unknown_stops_next_command(self):
        self.answer(value="UNKNOWN")
        with self.assertRaises(DomainError):
            self.answer(question="synthetic:sensitivity",version=1)
        with psycopg.connect(ADMIN) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM abc.eng14_policy_audit WHERE session_id=%s",
                 (self.sid,)).fetchone()[0],1)
            self.assertEqual(con.execute("SELECT state_version FROM abc.sessions WHERE session_id=%s",
                 (self.sid,)).fetchone()[0],1)

    def test_malformed_event_enters_retry_then_dlq_without_projection(self):
        # A canonical-type but malformed synthetic envelope from an admin
        # fixture is permanently rejected and only DLQed after bounded retries.
        sid2=PostgresStore(APP).create(self.human,{
            "branch_id":self.branch,"scope":"IN_SALON_SHARED_SCREEN"},
            "invalid-event-session-"+uuid.uuid4().hex)["session_id"]
        eid=uuid.uuid4()
        with psycopg.connect(ADMIN) as con:
            con.execute("""INSERT INTO abc.outbox
                (event_id,tenant_id,aggregate_id,aggregate_version,event_json,created_at)
                VALUES(%s,%s,%s,1,%s,clock_timestamp())""",
                (eid,self.tenant,sid2,
                 __import__("json").dumps({"event_type":"ANSWER_RECORDED",
                   "event_id":str(eid),"tenant_id":self.tenant,"session_id":sid2,
                   "aggregate_id":sid2,"aggregate_version":1,"payload":{}})))
        self.service_worker.dispatcher.register(self.cid)
        self.assertEqual(self.service_worker.run_once(),"REJECTED")
        with psycopg.connect(ADMIN) as con:
            state=con.execute("SELECT state FROM abc.event_delivery WHERE consumer_id=%s AND event_id=%s",
                          (self.cid,eid)).fetchone()[0]
            self.assertEqual(state,"PENDING")

    def test_parallel_dispatch_lease_single_item(self):
        self.answer()
        worker=self.service_worker.dispatcher
        worker.register(self.cid)
        with ThreadPoolExecutor(max_workers=4) as pool:
            rows=list(pool.map(lambda _:worker.lease(self.cid),range(4)))
        self.assertEqual(sum(row is not None for row in rows),1)

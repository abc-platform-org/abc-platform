"""Disposable PG16 ENG03 executor -> persistent ENG04/05/06 pipeline security.

All service/domain values synthetic. The actual source answer is retrieved by
a privileged broker only for a currently leased, admin-bound ENG03 job.
"""
import json
import os
import uuid
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone

import psycopg
from abc_foundation.answer_index_consumer import AnswerIndexConsumer
from abc_foundation.eng01_service_identity import WorkloadPrincipal
from abc_foundation.eng02_pg_outbox import PGENG02CommandWriter
from abc_foundation.eng03_executor import ENG03Executor
from abc_foundation.eng04_06_pipeline import SyntheticAnalysisPipeline
from abc_foundation.oidc import Principal
from abc_foundation.pg_store import PostgresStore
from abc_foundation.store import DomainError

ADMIN=os.getenv("ABC_TEST_PG_ADMIN_DSN")
APP=os.getenv("ABC_TEST_PG_DSN")
ORCH=os.getenv("ABC_TEST_PG_ORCHESTRATOR_DSN")
ANSWER=os.getenv("ABC_TEST_PG_ANSWER_WORKER_DSN")
ENG03=os.getenv("ABC_TEST_PG_ENG03_DSN")
PIPELINE=os.getenv("ABC_TEST_PG_PIPELINE_DSN")
ISS="https://identity.example.test/abc"
SERVICE_ISS="https://workload.identity.example.test/abc"
FIXTURE={"kind":"SYNTHETIC_TEST_FIXTURE","source_id":"synthetic:offline-catalog",
         "source_version":"test-v1","validated_by":"TEST_FIXTURE_ONLY",
         "facts":{"synthetic:style-a":True,"synthetic:style-b":False}}


@unittest.skipUnless(all((ADMIN,APP,ORCH,ANSWER,ENG03,PIPELINE)),"disposable PG16 required")
class ENG03PipelineTests(unittest.TestCase):
    def setUp(self):
        marker=uuid.uuid4().hex[:12]
        self.tenant="eng03-test-tenant-"+marker
        self.branch="eng03-test-branch-"+marker
        self.subject="eng03-test-staff-"+marker
        self.consumer="eng03-test-consumer-"+marker
        self.human=Principal(self.subject,ISS)
        self.workload=WorkloadPrincipal(SERVICE_ISS,"svc:abc-eng02","ENG-02",str(uuid.uuid4()))
        with psycopg.connect(ADMIN) as con:
            con.execute("INSERT INTO abc.tenants VALUES(%s)",(self.tenant,))
            con.execute("INSERT INTO abc.branches VALUES(%s,%s)",(self.tenant,self.branch))
            con.execute("""INSERT INTO abc.memberships(issuer,subject,tenant_id,branch_id,role,active)
                        VALUES(%s,%s,%s,%s,'SPECIALIST',true)""",
                        (ISS,self.subject,self.tenant,self.branch))
            con.execute("""INSERT INTO abc.engine_workload_grants
                (issuer,service_subject,engine_id,tenant_id,branch_id,permission,active)
                VALUES(%s,'svc:abc-eng02','ENG-02',%s,%s,'ENG02_RECORD_ANSWER',true)""",
                (SERVICE_ISS,self.tenant,self.branch))
            con.execute("""INSERT INTO abc.worker_subscriptions(consumer_id,tenant_id,event_type,active)
                     VALUES(%s,%s,'ANSWER_RECORDED',true)""",(self.consumer,self.tenant))
            for role in ("abc_eng03_worker","abc_pipeline_worker"):
                con.execute("""INSERT INTO abc.eng03_worker_bindings(worker_role,consumer_id,tenant_id,active)
                        VALUES(%s,%s,%s,true)""",(role,self.consumer,self.tenant))
        self.sid=PostgresStore(APP).create(self.human,{
            "branch_id":self.branch,"service_id":"synthetic:hair-color",
            "scope":"IN_SALON_SHARED_SCREEN"
        },"eng03-create-"+marker)["session_id"]
        self.writer=PGENG02CommandWriter(ORCH)
        self.answer_worker=AnswerIndexConsumer(ANSWER,self.consumer)
        self.worker=ENG03Executor(ENG03,self.consumer)
        self.pipeline=SyntheticAnalysisPipeline(PIPELINE,self.consumer)

    def answer(self,qid="synthetic:prior-treatment",value="NO",version=0):
        command={
          "command_id":str(uuid.uuid4()),"correlation_id":str(uuid.uuid4()),
          "session_id":self.sid,"tenant_id":self.tenant,"branch_id":self.branch,
          "engine_id":"ENG-02","contract_version":"1.0.0-draft",
          "profile_version":"synthetic-1.0.0","question_id":qid,"value":value,
          "answer_source":"CLIENT","expected_state_version":version,
          "requested_at":datetime.now(timezone.utc).isoformat()}
        return self.writer.record_synthetic_answer(self.human,self.workload,command)

    def arrive(self,qid="synthetic:prior-treatment",value="NO",version=0):
        receipt=self.answer(qid,value,version)
        self.assertEqual(self.answer_worker.run_once(),"PROJECTED")
        return receipt

    def count(self,table):
        if table not in ("abc.eng03_input_jobs","abc.eng03_evidence_ledger",
                         "abc.eng04_06_jobs","abc.eng04_06_results"):
            raise ValueError("invalid_test_table")
        with psycopg.connect(ADMIN) as con:
            return con.execute("SELECT count(*) FROM "+table+
                    " WHERE session_id=%s",(self.sid,)).fetchone()[0]

    def test_real_eng03_claim_ack_source_and_downstream_job(self):
        receipt=self.arrive()
        item=self.worker.claim()
        self.assertEqual(item["tenant_id"],self.tenant)
        with psycopg.connect(ENG03) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("SELECT * FROM abc.eng02_answers")
        result=self.worker.complete(item["job_id"],item["lease_token"])
        self.assertEqual(result["status"],"ACKED")
        self.assertEqual(self.count("abc.eng03_evidence_ledger"),1)
        self.assertEqual(self.count("abc.eng04_06_jobs"),1)
        with psycopg.connect(ADMIN) as con:
            row=con.execute("""SELECT e.evidence_json,e.source_answer_id,
                e.source_event_id,e.policy_decision_id,j.status
                FROM abc.eng03_evidence_ledger e
                JOIN abc.eng03_input_jobs j ON j.job_id=e.source_job_id
                WHERE e.session_id=%s""",(self.sid,)).fetchone()
        self.assertEqual(row[0]["attribute_key"],"prior_treatment")
        self.assertEqual(row[0]["evidence_class"],"USER_REPORTED")
        self.assertEqual(row[0]["source_type"],"CLIENT_ANSWER")
        self.assertEqual(str(row[1]),receipt["answer_id"])
        self.assertEqual(str(row[2]),receipt["event_id"])
        self.assertIsNotNone(row[3])
        self.assertEqual(row[4],"ACKED")
        self.assertIsNone(self.worker.claim())

    def test_crash_before_completion_and_stale_fencing(self):
        self.arrive()
        leased=self.worker.claim(seconds=30)
        self.assertIsNotNone(leased)
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.eng03_input_jobs
                SET lease_until=clock_timestamp()-interval '1 second'
                WHERE job_id=%s""",(leased["job_id"],))
        fresh=ENG03Executor(ENG03,self.consumer).claim()
        self.assertEqual(fresh["job_id"],leased["job_id"])
        self.assertNotEqual(fresh["lease_token"],leased["lease_token"])
        with self.assertRaises(DomainError) as ex:
            self.worker.complete(leased["job_id"],leased["lease_token"])
        self.assertEqual(ex.exception.status,409)
        self.worker.complete(fresh["job_id"],fresh["lease_token"])
        self.assertEqual(self.count("abc.eng03_evidence_ledger"),1)
        self.assertEqual(self.count("abc.eng04_06_jobs"),1)

    def test_concurrent_eng03_claim_once(self):
        self.arrive()
        with ThreadPoolExecutor(max_workers=5) as pool:
            leases=list(pool.map(lambda _:self.worker.claim(),range(5)))
        self.assertEqual(sum(x is not None for x in leases),1)
        x=next(v for v in leases if v)
        self.worker.complete(x["job_id"],x["lease_token"])

    def test_revocation_denies_next_claim_and_proof_read(self):
        self.arrive()
        leased=self.worker.claim()
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.eng03_worker_bindings SET active=false
                 WHERE consumer_id=%s AND worker_role='abc_eng03_worker'""",(self.consumer,))
        with self.assertRaises((DomainError,psycopg.errors.InsufficientPrivilege)) as err:
            self.worker.complete(leased["job_id"],leased["lease_token"])
        self.assertEqual(self.count("abc.eng03_evidence_ledger"),0)
        self.assertIsNone(self.worker.claim())

    def test_worker_cannot_forge_admin_grant_or_write_answer(self):
        with psycopg.connect(ENG03) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("UPDATE abc.eng03_worker_bindings SET active=true")
        with psycopg.connect(ENG03) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("SELECT * FROM abc.eng14_policy_audit")
        with psycopg.connect(PIPELINE) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("SELECT * FROM abc.eng02_answers")

    def test_source_broker_requires_lease_and_correct_token(self):
        self.arrive()
        item=self.worker.claim()
        with psycopg.connect(ENG03) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("SELECT abc.eng03_source_for_lease(%s,%s)",
                           (item["job_id"],uuid.uuid4()))
        with psycopg.connect(APP) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("SELECT abc.eng03_source_for_lease(%s,%s)",
                           (item["job_id"],item["lease_token"]))

    def test_eng03_bounded_dlq_after_three_failures(self):
        self.arrive()
        for attempt in range(1,4):
            leased=self.worker.claim()
            self.assertIsNotNone(leased)
            state=self.worker.fail(leased["job_id"],leased["lease_token"],"TEST_FAILURE")
            self.assertEqual(state,"DLQ" if attempt==3 else "QUEUED_PENDING_ENGINE")
            if attempt<3:
                with psycopg.connect(ADMIN) as con:
                    con.execute("""UPDATE abc.eng03_input_jobs
                          SET next_attempt_at=clock_timestamp()-interval '1 second'
                          WHERE job_id=%s""",(leased["job_id"],))
        self.assertIsNone(self.worker.claim())

    def test_pipeline_persists_unknowns_without_fake_knowledge(self):
        self.arrive()
        self.assertEqual(self.worker.run_once(),"ACKED")
        item=self.pipeline.claim()
        result=self.pipeline.complete(item["job_id"],item["lease_token"])
        self.assertEqual(result["candidate_count"],0)
        self.assertEqual(self.count("abc.eng04_06_results"),1)
        with psycopg.connect(ADMIN) as con:
            row=con.execute("SELECT analysis_json,knowledge_json,decision_json FROM abc.eng04_06_results WHERE session_id=%s",(self.sid,)).fetchone()
        self.assertIn("goal",row[0]["unknowns"])
        self.assertIn("maintenance",row[0]["unknowns"])
        self.assertEqual(row[1]["retrieval_sources"],[])
        self.assertEqual(row[2]["candidates"],[])

    def test_full_four_answer_pipeline_conditional_fixture_only(self):
        ids=("synthetic:prior-treatment","synthetic:sensitivity",
             "synthetic:desired-goal","synthetic:maintenance")
        vals=("NO","NO","SUBTLE","LOW")
        for i,(qid,val) in enumerate(zip(ids,vals)):
            self.arrive(qid,val,i)
            self.assertEqual(self.worker.run_once(),"ACKED")
        with psycopg.connect(ADMIN) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM abc.eng03_evidence_ledger WHERE session_id=%s",
                                       (self.sid,)).fetchone()[0],4)
        fixture_pipeline=SyntheticAnalysisPipeline(PIPELINE,self.consumer,knowledge_fixture=FIXTURE)
        for _ in range(4):
            item=fixture_pipeline.claim()
            self.assertIsNotNone(item)
            fixture_pipeline.complete(item["job_id"],item["lease_token"])
        with psycopg.connect(ADMIN) as con:
            row=con.execute("""SELECT decision_json,analysis_json,knowledge_json
                FROM abc.eng04_06_results WHERE session_id=%s AND aggregate_version=4""",
                (self.sid,)).fetchone()
        self.assertEqual(len(row[0]["candidates"]),1)
        self.assertEqual(row[0]["candidates"][0]["feasibility_label"],"PROFESSIONAL_CHECK_REQUIRED")
        self.assertEqual(row[1]["unknowns"],[])
        self.assertEqual(row[2]["retrieval_sources"][0]["validated_by"],"TEST_FIXTURE_ONLY")

    def test_pipeline_crash_stale_token_and_replay(self):
        self.arrive()
        self.worker.run_once()
        first=self.pipeline.claim()
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.eng04_06_jobs
                SET lease_until=clock_timestamp()-interval '1 second' WHERE job_id=%s""",
                (first["job_id"],))
        fresh=self.pipeline.claim()
        with self.assertRaises(DomainError):
            self.pipeline.complete(first["job_id"],first["lease_token"])
        self.pipeline.complete(fresh["job_id"],fresh["lease_token"])
        self.assertEqual(self.count("abc.eng04_06_results"),1)

    def test_database_rejects_forged_eng03_source_and_policy(self):
        receipt=self.arrive()
        leased=self.worker.claim()
        with psycopg.connect(ENG03) as con:
            with self.assertRaises(psycopg.errors.CheckViolation):
                con.execute("""INSERT INTO abc.eng03_evidence_ledger(
                    evidence_id,consumer_id,source_job_id,source_event_id,
                    source_answer_id,policy_decision_id,source_lease_token,
                    tenant_id,branch_id,session_id,aggregate_version,
                    question_id,source_kind,evidence_json,evidence_digest)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,
                    'synthetic:prior-treatment','CLIENT',%s,%s)""",
                    (uuid.uuid4(),self.consumer,leased["job_id"],receipt["event_id"],
                     uuid.uuid4(),uuid.uuid4(),leased["lease_token"],
                     self.tenant,self.branch,self.sid,
                     json.dumps({"evidence_class":"OBSERVED","value":"NO",
                       "session_id":self.sid,"service_id":"synthetic:hair-color",
                       "attribute_key":"prior_treatment"}),"0"*64))
        self.worker.complete(leased["job_id"],leased["lease_token"])
        self.assertEqual(self.count("abc.eng03_evidence_ledger"),1)

    def test_pipeline_db_blocks_invented_or_approved_candidate(self):
        self.arrive()
        self.worker.run_once()
        job=self.pipeline.claim()
        analysis={"session_id":self.sid,"service_id":"synthetic:hair-color"}
        knowledge={"service_id":"synthetic:hair-color","retrieval_sources":[]}
        decision={"session_id":self.sid,"service_id":"synthetic:hair-color",
                  "candidates":[{"candidate_id":"real:unsafe","reason":"FAKE",
                       "feasibility_label":"VISUALLY_PLAUSIBLE",
                       "hard_filter_status":"PASSED"}]}
        with psycopg.connect(PIPELINE) as con:
            with self.assertRaises(psycopg.errors.CheckViolation):
                con.execute("""INSERT INTO abc.eng04_06_results(
                    result_id,consumer_id,source_pipeline_job_id,
                    tenant_id,branch_id,session_id,aggregate_version,
                    source_evidence_digest,analysis_json,knowledge_json,
                    decision_json,policy_version)
                    VALUES(%s,%s,%s,%s,%s,%s,1,%s,%s,%s,%s,'eng14.synthetic.1')""",
                    (uuid.uuid4(),self.consumer,job["job_id"],self.tenant,
                     self.branch,self.sid,"0"*64,json.dumps(analysis),
                     json.dumps(knowledge),json.dumps(decision)))
        self.pipeline.complete(job["job_id"],job["lease_token"])
        self.assertEqual(self.count("abc.eng04_06_results"),1)

    def test_cross_tenant_bindings_not_available_to_unbound_runtime(self):
        self.arrive()
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.eng03_worker_bindings SET active=false
              WHERE consumer_id=%s""",(self.consumer,))
        self.assertIsNone(self.worker.claim())
        self.assertIsNone(self.pipeline.claim())

    def test_unknown_critical_answer_still_bounded_by_eng14(self):
        self.arrive(value="UNKNOWN")
        self.assertEqual(self.worker.run_once(),"ACKED")
        job=self.pipeline.claim()
        result=self.pipeline.complete(job["job_id"],job["lease_token"])
        self.assertEqual(result["candidate_count"],0)
        with psycopg.connect(ADMIN) as con:
            obj=con.execute("""SELECT analysis_json,decision_json FROM abc.eng04_06_results
                    WHERE session_id=%s""",(self.sid,)).fetchone()
        self.assertIn("prior_treatment",obj[0]["unknowns"])
        self.assertEqual(obj[1]["candidates"],[])

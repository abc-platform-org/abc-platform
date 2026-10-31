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
from psycopg import sql
from psycopg.conninfo import make_conninfo
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
        self.eng03_dsn,self.pipeline_dsn,self.worker_login_eng03,self.worker_login_pipeline=self._provision_scoped_worker_logins(self.consumer)
        self.sid=PostgresStore(APP).create(self.human,{
            "branch_id":self.branch,"service_id":"synthetic:hair-color",
            "scope":"IN_SALON_SHARED_SCREEN"
        },"eng03-create-"+marker)["session_id"]
        self.writer=PGENG02CommandWriter(ORCH)
        self.answer_worker=AnswerIndexConsumer(ANSWER,self.consumer)
        self.worker=ENG03Executor(self.eng03_dsn,self.consumer)
        self.pipeline=SyntheticAnalysisPipeline(self.pipeline_dsn,self.consumer)

    def _provision_scoped_worker_logins(self,consumer):
        # Explicit administrator setup, never executed from an application
        # or workload role. Unique login per engine+consumer with NOINHERIT.
        short=uuid.uuid4().hex[:14]
        name_eng03="abc_e3_"+short
        name_pipeline="abc_p6_"+short
        dsn_pairs=[]
        with psycopg.connect(ADMIN) as con:
            for login,group,base in (
                (name_eng03,"abc_eng03_worker",ENG03),
                (name_pipeline,"abc_pipeline_worker",PIPELINE)):
                password="ci-synthetic-only-"+uuid.uuid4().hex
                con.execute(sql.SQL("""CREATE ROLE {} LOGIN NOINHERIT NOSUPERUSER
                    NOCREATEROLE NOCREATEDB NOBYPASSRLS PASSWORD {}""").format(
                    sql.Identifier(login),sql.Literal(password)))
                con.execute(sql.SQL(
                    "GRANT {} TO {} WITH INHERIT FALSE, SET TRUE").format(
                    sql.Identifier(group),sql.Identifier(login)))
                con.execute("""INSERT INTO abc.worker_login_bindings(
                    login_name,worker_role,consumer_id,tenant_id,active)
                    VALUES(%s,%s,%s,%s,true)""",
                    (login,group,consumer,self.tenant))
                dsn_pairs.append(make_conninfo(base,user=login,password=password))
        return (*dsn_pairs,name_eng03,name_pipeline)

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
        with self.worker._connect() as con:
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
        fresh=ENG03Executor(self.eng03_dsn,self.consumer).claim()
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
        with self.assertRaises(DomainError) as denied:
            self.worker.claim()
        self.assertEqual(denied.exception.status,403)

    def test_worker_cannot_forge_admin_grant_or_write_answer(self):
        with self.worker._connect() as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("UPDATE abc.eng03_worker_bindings SET active=true")
        with self.worker._connect() as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("SELECT * FROM abc.eng14_policy_audit")
        with self.pipeline._connect() as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("SELECT * FROM abc.eng02_answers")

    def test_eng03_repeated_crash_expired_lease_goes_to_dlq(self):
        self.arrive()
        for index in range(3):
            lease=self.worker.claim()
            self.assertIsNotNone(lease)
            with psycopg.connect(ADMIN) as con:
                con.execute("""UPDATE abc.eng03_input_jobs
                    SET lease_until=clock_timestamp()-interval '1 second'
                    WHERE job_id=%s""",(lease["job_id"],))
        self.assertIsNone(self.worker.claim())
        with psycopg.connect(ADMIN) as con:
            row=con.execute("""SELECT status,error_code,attempts
                FROM abc.eng03_input_jobs WHERE session_id=%s""",(self.sid,)).fetchone()
        self.assertEqual(row,("DLQ","LEASE_RETRY_EXHAUSTED",3))
        self.assertEqual(self.count("abc.eng03_evidence_ledger"),0)

    def test_analysis_repeated_crash_expired_lease_goes_to_dlq(self):
        self.arrive()
        self.worker.run_once()
        for index in range(3):
            lease=self.pipeline.claim()
            self.assertIsNotNone(lease)
            with psycopg.connect(ADMIN) as con:
                con.execute("""UPDATE abc.eng04_06_jobs
                    SET lease_until=clock_timestamp()-interval '1 second'
                    WHERE job_id=%s""",(lease["job_id"],))
        self.assertIsNone(self.pipeline.claim())
        with psycopg.connect(ADMIN) as con:
            row=con.execute("""SELECT status,error_code,attempts
                FROM abc.eng04_06_jobs WHERE session_id=%s""",(self.sid,)).fetchone()
        self.assertEqual(row,("DLQ","LEASE_RETRY_EXHAUSTED",3))
        self.assertEqual(self.count("abc.eng04_06_results"),0)

    def test_source_broker_requires_lease_and_correct_token(self):
        self.arrive()
        item=self.worker.claim()
        with self.worker._connect() as con:
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

    def _eng04_real_ledger_fixture(self):
        """Actual ENG02→ENG03 event/answer→ledger; no fabricated source."""
        from abc_foundation.eng04_review_worker import SyntheticEng04ReviewWorker
        from abc_foundation.pg_store import PostgresStore
        now=datetime.now(timezone.utc)
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.sessions SET client_id='eng04-synthetic-client'
                WHERE session_id=%s""",(self.sid,))
        ids=("synthetic:prior-treatment","synthetic:sensitivity",
             "synthetic:desired-goal","synthetic:maintenance")
        vals=("NO","NO","SUBTLE","LOW")
        for i,(qid,val) in enumerate(zip(ids,vals)):
            self.arrive(qid,val,i)
            self.assertEqual(self.worker.run_once(),"ACKED")
        with psycopg.connect(ADMIN) as con:
            version=con.execute("SELECT state_version FROM abc.sessions WHERE session_id=%s",
                                (self.sid,)).fetchone()[0]
            self.assertEqual(version,4)
            self.assertEqual(con.execute("""SELECT count(*) FROM abc.eng03_evidence_ledger
                WHERE session_id=%s AND consumer_id=%s""",
                (self.sid,self.consumer)).fetchone()[0],4)
            proof=uuid.uuid4()
            con.execute("""INSERT INTO abc.consent_evidence(
                consent_id,tenant_id,branch_id,session_id,client_id,status,
                purpose,evidence_digest,disclosure_version,retention_policy_id)
                VALUES(%s,%s,%s,%s,'eng04-synthetic-client','PENDING_VERIFICATION',
                ARRAY['AI_PROCESSING','INTERNAL_HANDOFF']::text[],%s,
                'CI-ENG04-NOT_LEGAL','CI-NO_CLIENT')""",
                (proof,self.tenant,self.branch,self.sid,"c"*64))
            con.execute("""UPDATE abc.consent_evidence SET status='ACTIVE',
                verified_at=%s,valid_until=%s WHERE consent_id=%s""",
                (now,now+__import__("datetime").timedelta(hours=1),proof))
            con.execute("""INSERT INTO abc.eng04_ci_worker_bindings(
                login_name,consumer_id,tenant_id,active)
                VALUES('abc_eng04_ci_login',%s,%s,true)""",
                (self.consumer,self.tenant))
            job=uuid.uuid4()
            con.execute("""INSERT INTO abc.eng04_ci_jobs(
                job_id,tenant_id,branch_id,session_id,consumer_id,state_version)
                VALUES(%s,%s,%s,%s,%s,%s)""",
                (job,self.tenant,self.branch,self.sid,self.consumer,version))
        worker=SyntheticEng04ReviewWorker(
            store=PostgresStore(os.environ["ABC_TEST_PG_ENG04_LOGIN_DSN"]),
            consumer_id=self.consumer)
        return worker,str(job),str(proof)

    def _eng04_same_artifact_authenticated_receiver(self):
        """Only synthetic, loopback identity issuer + independent DB gates.

        Starts with four actual ENG03 ACKed evidence rows. No fake SQL source
        ledger or patched consent/version records are injected downstream.
        """
        import threading
        from abc_foundation.distributed_replay import PostgresReplayLedger
        from abc_foundation.eng19_review_consumer import (
            AuthenticatedReviewConsumer,PostgresReviewInbox)
        from abc_foundation.eng19_review_transport import start_local_review_consumer
        from abc_foundation.pg_store import PostgresStore
        from test_private_engine_mtls import ManagedWorkloadMTLSTests

        worker,job,consent=self._eng04_real_ledger_fixture()
        processed=worker.process_once()
        self.assertEqual(processed["status"],"ACKED_REVIEW_ONLY")
        original=worker.review_candidate(job,
            correlation_id=str(uuid.uuid4()),handoff_id=str(uuid.uuid4()))
        with psycopg.connect(ADMIN) as con:
            stored=con.execute("""SELECT output_bytes,output_sha256,
              source_manifest_sha256 FROM abc.eng04_ci_results
              WHERE job_id=%s""",(job,)).fetchone()
        self.assertEqual(stored[0],__import__("abc_foundation.eng05_review_worker",
            fromlist=["canonical_bytes"]).canonical_bytes(original["source_artifact"]))
        self.assertEqual(stored[1],original["message"]["artifact_sha256"])
        self.assertEqual(stored[2],original["source_manifest_sha256"])

        fixture=ManagedWorkloadMTLSTests("test_real_tls13_mutual_certificate_and_bound_jwt")
        fixture.consumer_override=self.consumer
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        class ScopedAuthority:
            def __init__(authority,outer):
                authority.outer=outer
                authority.allowed=True
            def verify(authority,**claims):
                o=authority.outer
                return (authority.allowed and
                    claims.get("tenant_id")==o.tenant and
                    claims.get("branch_id")==o.branch and
                    claims.get("session_id")==o.sid and
                    claims.get("state_version")==4 and
                    claims.get("from_engine")=="ENG-04" and
                    claims.get("to_engine")=="ENG-05" and
                    claims.get("consumer_id")==o.consumer and
                    claims.get("artifact_kind")=="BEAUTY_ANALYSIS_REPORT" and
                    claims.get("certificate_sha256") is not None and
                    claims.get("policy_proof_ref")=="synthetic:eng14-policy-proof" and
                    (claims.get("purposes") is None or
                     claims.get("purposes")==("AI_PROCESSING","INTERNAL_HANDOFF")))
        session=ScopedAuthority(self)
        consent_gate=ScopedAuthority(self)
        policy=ScopedAuthority(self)
        app_store=PostgresStore(APP)
        receiver=AuthenticatedReviewConsumer(
            identity_verifier=fixture.verifier,
            session_authority=session,consent_authority=consent_gate,
            eng14_authority=policy,
            replay_ledger=PostgresReplayLedger(app_store),
            inbox=PostgresReviewInbox(app_store),
            caller_engine="ENG-04",target_engine="ENG-05",
            consumer_id=self.consumer)
        server=start_local_review_consumer(
            consumer=receiver,certfile=fixture.server_cert,
            keyfile=fixture.server_key,ca_file=fixture.ca_path)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        return {
            "fixture":fixture,"server":server,"candidate":original,
            "worker":worker,"job":job,"consent_id":consent,
            "policy":policy,"session":session,"consent_gate":consent_gate
        }

    def _deliver_saved_eng04(self,link,*,token=None,message=None,source=None):
        from abc_foundation.eng19_review_transport import send_local_review_handoff
        fixture=link["fixture"]
        candidate=link["candidate"]
        return send_local_review_handoff(
            port=link["server"].server_address[1],
            token=fixture.token() if token is None else token,
            message=candidate["message"] if message is None else message,
            source_artifact=candidate["source_artifact"] if source is None else source,
            client_cert=fixture.client_cert,client_key=fixture.client_key,
            server_ca=fixture.ca_path)

    def _verified_eng05_queue(self):
        from abc_foundation.eng05_review_worker import SyntheticEng05ReviewWorker
        from abc_foundation.pg_store import PostgresStore
        link=self._eng04_same_artifact_authenticated_receiver()
        admitted=self._deliver_saved_eng04(link)
        self.assertEqual(admitted["status"],"RECORDED_REVIEW_ONLY")
        with psycopg.connect(ADMIN) as con:
            con.execute("""INSERT INTO abc.eng05_worker_bindings(
              login_name,worker_role,consumer_id,tenant_id,active)
              VALUES('abc_eng05_ci_login','abc_eng05_worker',%s,%s,true)""",
              (self.consumer,self.tenant))
        worker=SyntheticEng05ReviewWorker(
            store=PostgresStore(os.environ["ABC_TEST_PG_ENG05_LOGIN_DSN"]),
            consumer_id=self.consumer)
        return link,worker

    def test_verified_eng05_processes_real_eng04_source_in_separate_os_process(self):
        import subprocess
        import sys
        link,worker=self._verified_eng05_queue()
        proc=subprocess.run(
          [sys.executable,"-m","abc_foundation.eng05_review_worker"],
          env={**os.environ,"ABC_ENG05_CI_CONSUMER":self.consumer},
          capture_output=True,text=True,timeout=20)
        self.assertEqual(proc.returncode,0,proc.stderr)
        receipt=json.loads(proc.stdout)
        self.assertEqual(receipt["engine_id"],"ENG-05")
        self.assertEqual(receipt["status"],"ACKED_REVIEW_ONLY")
        self.assertFalse(receipt["professional_validation_verified"])
        self.assertFalse(receipt["eng05_to_eng06_dispatched"])
        self.assertIsNone(worker.process_once())
        with psycopg.connect(ADMIN) as con:
            handoff=link["candidate"]["message"]["handoff_id"]
            res=con.execute("""SELECT j.status,j.attempts,j.source_sha256,
              r.source_sha256,r.output_bytes,r.output_sha256
              FROM abc.eng19_synthetic_jobs j
              JOIN abc.eng19_synthetic_results r USING(handoff_id)
              WHERE handoff_id=%s""",(handoff,)).fetchone()
            lineage=con.execute("""SELECT eng04_job_id,eng04_artifact_sha256,
              eng03_manifest_sha256,eng05_result_sha256,status
              FROM abc.eng05_ci_source_receipts WHERE handoff_id=%s""",
              (handoff,)).fetchone()
            out=con.execute("""SELECT status FROM abc.eng19_synthetic_outbox
              WHERE handoff_id=%s""",(handoff,)).fetchone()
            source=con.execute("""SELECT output_sha256,source_manifest_sha256
              FROM abc.eng04_ci_results WHERE job_id=%s""",
              (link["job"],)).fetchone()
        self.assertEqual(res[0:2],("ACKED",1))
        self.assertEqual(res[2],res[3])
        self.assertEqual(str(lineage[0]),link["job"])
        self.assertEqual((lineage[1],lineage[2]),source)
        self.assertEqual(lineage[3],res[5])
        self.assertEqual(lineage[4],"BLOCKED_PENDING_AUTHORITY")
        self.assertEqual(out[0],"BLOCKED_PENDING_AUTHORITY")
        output=json.loads(res[4])
        self.assertEqual(output["retrieval_sources"],[])
        self.assertEqual(output["grounded_facts"],[])
        self.assertEqual(output["unknowns"],["SOURCE_UNVERIFIED"])

    def test_eng05_verified_queue_parallel_claim_and_stale_ack_fencing(self):
        from abc_foundation.eng05_knowledge import SyntheticKnowledgeEngine
        from abc_foundation.eng02_consultation import SYNTHETIC_SERVICE
        link,worker=self._verified_eng05_queue()
        with ThreadPoolExecutor(max_workers=4) as pool:
            claimed=list(pool.map(lambda _:worker.claim(),range(4)))
        leases=[r for r in claimed if r is not None]
        self.assertEqual(len(leases),1)
        old=leases[0]
        self.assertTrue(old["eng04_verified_lineage"]["source_identity_verified"])
        self.assertEqual(old["eng04_verified_lineage"]["eng03_manifest_sha256"],
                         link["candidate"]["source_manifest_sha256"])
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.eng19_synthetic_jobs
              SET lease_until=clock_timestamp()-interval '1 second'
              WHERE handoff_id=%s""",(old["handoff_id"],))
        fresh=worker.claim()
        self.assertNotEqual(old["lease_token"],fresh["lease_token"])
        knowledge=SyntheticKnowledgeEngine().resolve(
            service_id=SYNTHETIC_SERVICE,fixture=None)
        with self.assertRaises(DomainError):
            worker.ack(old,knowledge,next_handoff_id=str(uuid.uuid4()))
        self.assertEqual(worker.ack(fresh,knowledge,
            next_handoff_id=str(uuid.uuid4()))["status"],"ACKED_REVIEW_ONLY")
        with psycopg.connect(ADMIN) as con:
            n=con.execute("""SELECT count(*) FROM abc.eng05_ci_source_receipts
                WHERE handoff_id=%s""",(fresh["handoff_id"],)).fetchone()[0]
        self.assertEqual(n,1)

    def test_eng05_verified_source_revoke_eng04_identity_blocks_claim_and_ack(self):
        from abc_foundation.eng05_knowledge import SyntheticKnowledgeEngine
        from abc_foundation.eng02_consultation import SYNTHETIC_SERVICE
        link,worker=self._verified_eng05_queue()
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.eng04_ci_worker_bindings SET active=false
                WHERE login_name='abc_eng04_ci_login' AND
                      consumer_id=%s AND tenant_id=%s""",
                (self.consumer,self.tenant))
        with self.assertRaises(DomainError):
            worker.claim()
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.eng04_ci_worker_bindings SET active=true
                WHERE login_name='abc_eng04_ci_login' AND
                      consumer_id=%s AND tenant_id=%s""",
                (self.consumer,self.tenant))
        claim=worker.claim()
        self.assertIsNotNone(claim)
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.eng04_ci_worker_bindings SET active=false
                WHERE login_name='abc_eng04_ci_login' AND
                      consumer_id=%s AND tenant_id=%s""",
                (self.consumer,self.tenant))
        knowledge=SyntheticKnowledgeEngine().resolve(
            service_id=SYNTHETIC_SERVICE,fixture=None)
        with self.assertRaises(DomainError):
            worker.ack(claim,knowledge,next_handoff_id=str(uuid.uuid4()))
        with psycopg.connect(ADMIN) as con:
            n=con.execute("""SELECT count(*) FROM abc.eng19_synthetic_results
              WHERE handoff_id=%s""",(claim["handoff_id"],)).fetchone()[0]
        self.assertEqual(n,0)

    def test_eng05_verified_source_consent_revoked_after_claim_denies_ack(self):
        from abc_foundation.eng05_knowledge import SyntheticKnowledgeEngine
        from abc_foundation.eng02_consultation import SYNTHETIC_SERVICE
        link,worker=self._verified_eng05_queue()
        claim=worker.claim()
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.consent_evidence
              SET status='WITHDRAWN',revoked_at=clock_timestamp()
              WHERE consent_id=%s""",(link["consent_id"],))
        knowledge=SyntheticKnowledgeEngine().resolve(
            service_id=SYNTHETIC_SERVICE,fixture=None)
        with self.assertRaises(DomainError):
            worker.ack(claim,knowledge,next_handoff_id=str(uuid.uuid4()))
        with psycopg.connect(ADMIN) as con:
            n=con.execute("""SELECT count(*) FROM abc.eng05_ci_source_receipts
              WHERE handoff_id=%s""",(claim["handoff_id"],)).fetchone()[0]
        self.assertEqual(n,0)

    def test_eng05_verified_queue_retries_then_dlq_and_no_eng06_outbox(self):
        link,worker=self._verified_eng05_queue()
        for i in range(3):
            claim=worker.claim()
            self.assertIsNotNone(claim)
            self.assertEqual(claim["attempt"],i+1)
            result=worker.fail(claim,error_code="CI_VERIFIED_RETRY_TEST")
            self.assertEqual(result,"DLQ" if i==2 else "QUEUED")
            if i<2:
                with psycopg.connect(ADMIN) as con:
                    con.execute("""UPDATE abc.eng19_synthetic_jobs
                      SET available_at=clock_timestamp()-interval '1 second'
                      WHERE handoff_id=%s""",(claim["handoff_id"],))
        self.assertIsNone(worker.claim())
        with psycopg.connect(ADMIN) as con:
            row=con.execute("""SELECT status,attempts FROM abc.eng19_synthetic_jobs
                WHERE handoff_id=%s""",(claim["handoff_id"],)).fetchone()
            n=con.execute("""SELECT count(*) FROM abc.eng19_synthetic_outbox
                WHERE handoff_id=%s""",(claim["handoff_id"],)).fetchone()[0]
        self.assertEqual(row,("DLQ",3))
        self.assertEqual(n,0)

    def test_eng05_verified_queue_denies_forged_professional_output_and_cross_role(self):
        from abc_foundation.eng05_knowledge import SyntheticKnowledgeEngine
        from abc_foundation.eng02_consultation import SYNTHETIC_SERVICE
        link,worker=self._verified_eng05_queue()
        claim=worker.claim()
        output=SyntheticKnowledgeEngine().resolve(
          service_id=SYNTHETIC_SERVICE,fixture=None)
        output["grounded_facts"]=[{"claim":"invented salon recommendation"}]
        with self.assertRaises(DomainError):
            worker.ack(claim,output,next_handoff_id=str(uuid.uuid4()))
        with psycopg.connect(os.environ["ABC_TEST_PG_ENG04_LOGIN_DSN"]) as con:
            con.execute("SET LOCAL ROLE abc_eng04_worker")
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("SELECT abc.eng19_claim_synthetic(%s,30)",
                            (self.consumer,))
        with psycopg.connect(ADMIN) as con:
            n=con.execute("""SELECT count(*) FROM abc.eng05_ci_source_receipts
                WHERE handoff_id=%s""",(claim["handoff_id"],)).fetchone()[0]
            self.assertEqual(n,0)
            perms=con.execute("""SELECT relrowsecurity,relforcerowsecurity
              FROM pg_class WHERE oid='abc.eng05_ci_source_receipts'::regclass""").fetchone()
            self.assertEqual(perms,(True,True))

    def test_eng04_actual_persisted_bytes_to_eng05_tls13_jwt_and_durable_receipt(self):
        link=self._eng04_same_artifact_authenticated_receiver()
        first=self._deliver_saved_eng04(link)
        self.assertEqual(first["status"],"RECORDED_REVIEW_ONLY")
        self.assertTrue(first["durable_review_receipt"])
        self.assertFalse(first["consumer_execution_authorized"])
        again=self._deliver_saved_eng04(link)
        self.assertEqual(again["status"],"ALREADY_RECORDED_REVIEW_ONLY")
        with psycopg.connect(ADMIN) as con:
            r=con.execute("""SELECT i.from_engine,i.to_engine,i.artifact_kind,
                j.source_bytes,j.source_sha256,j.status
                FROM abc.eng19_review_inbox i
                JOIN abc.eng19_synthetic_jobs j ON j.handoff_id=i.handoff_id
                WHERE i.handoff_id=%s""",
                (link["candidate"]["message"]["handoff_id"],)).fetchone()
            original=con.execute("""SELECT output_bytes,output_sha256
                FROM abc.eng04_ci_results WHERE job_id=%s""",
                (link["job"],)).fetchone()
            copies=con.execute("""SELECT count(*) FROM abc.eng19_synthetic_jobs
                WHERE handoff_id=%s""",
                (link["candidate"]["message"]["handoff_id"],)).fetchone()[0]
        self.assertEqual(r[:3],("ENG-04","ENG-05","BEAUTY_ANALYSIS_REPORT"))
        self.assertEqual((r[3],r[4]),original)
        self.assertEqual(r[5],"QUEUED")
        self.assertEqual(copies,1)
        # Receiving an envelope does NOT execute professional ENG05 or 06.
        self.assertFalse(first["customer_release_approved"])

    def test_eng04_saved_artifact_jwt_replay_wrong_identity_and_tamper_denied(self):
        link=self._eng04_same_artifact_authenticated_receiver()
        token=link["fixture"].token()
        self.assertEqual(self._deliver_saved_eng04(link,token=token)["status"],
                         "RECORDED_REVIEW_ONLY")
        replay=self._deliver_saved_eng04(link,token=token)
        self.assertEqual(replay["status"],"REJECTED")
        wrong=link["fixture"].token(engine="ENG-05")
        self.assertEqual(self._deliver_saved_eng04(link,token=wrong)["status"],
                         "REJECTED")
        other=link["fixture"].token(consumer="ci-foreign-consumer")
        self.assertEqual(self._deliver_saved_eng04(link,token=other)["status"],
                         "REJECTED")
        source=json.loads(json.dumps(link["candidate"]["source_artifact"]))
        source["attributes"][0]["value"]="FORGED"
        self.assertEqual(self._deliver_saved_eng04(link,source=source)["status"],
                         "REJECTED")
        conflict=json.loads(json.dumps(link["candidate"]["message"]))
        conflict["correlation_id"]=str(uuid.uuid4())
        self.assertEqual(self._deliver_saved_eng04(link,message=conflict)["status"],
                         "REJECTED")
        with psycopg.connect(ADMIN) as con:
            self.assertEqual(con.execute("""SELECT count(*)
                FROM abc.eng19_synthetic_jobs WHERE handoff_id=%s""",
                (link["candidate"]["message"]["handoff_id"],)).fetchone()[0],1)

    def test_eng04_dest_denies_revoked_consent_or_independent_policy(self):
        link=self._eng04_same_artifact_authenticated_receiver()
        link["policy"].allowed=False
        self.assertEqual(self._deliver_saved_eng04(link)["status"],"REJECTED")
        link["policy"].allowed=True
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.consent_evidence
                SET status='WITHDRAWN',revoked_at=clock_timestamp()
                WHERE consent_id=%s""",(link["consent_id"],))
        self.assertEqual(self._deliver_saved_eng04(link)["status"],"REJECTED")
        with psycopg.connect(ADMIN) as con:
            self.assertEqual(con.execute("""SELECT count(*)
                FROM abc.eng19_review_inbox WHERE handoff_id=%s""",
                (link["candidate"]["message"]["handoff_id"],)).fetchone()[0],0)
            self.assertEqual(con.execute("""SELECT count(*)
                FROM abc.eng19_synthetic_jobs WHERE handoff_id=%s""",
                (link["candidate"]["message"]["handoff_id"],)).fetchone()[0],0)

    def test_eng04_revoked_source_workload_binding_blocks_destination_receipt(self):
        link=self._eng04_same_artifact_authenticated_receiver()
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.eng04_ci_worker_bindings SET active=false
                WHERE consumer_id=%s AND tenant_id=%s
                  AND login_name='abc_eng04_ci_login'""",
                (self.consumer,self.tenant))
        self.assertEqual(self._deliver_saved_eng04(link)["status"],"REJECTED")
        with psycopg.connect(ADMIN) as con:
            self.assertEqual(con.execute("""SELECT count(*) FROM abc.eng19_review_inbox
                WHERE handoff_id=%s""",
                (link["candidate"]["message"]["handoff_id"],)).fetchone()[0],0)
            self.assertEqual(con.execute("""SELECT count(*) FROM abc.eng19_synthetic_jobs
                WHERE handoff_id=%s""",
                (link["candidate"]["message"]["handoff_id"],)).fetchone()[0],0)

    def test_eng04_terminal_network_outage_never_writes_partial_receipt(self):
        from abc_foundation.eng19_review_transport import deliver_review_with_bounded_retry
        link=self._eng04_same_artifact_authenticated_receiver()
        def disconnected(**kwargs):
            raise OSError("simulated_permanent_loopback_unavailable")
        fixture=link["fixture"]
        with self.assertRaises(DomainError) as exc:
            deliver_review_with_bounded_retry(
                transport=disconnected,token_provider=fixture.token,max_attempts=2,
                port=link["server"].server_address[1],
                message=link["candidate"]["message"],
                source_artifact=link["candidate"]["source_artifact"],
                client_cert=fixture.client_cert,client_key=fixture.client_key,
                server_ca=fixture.ca_path)
        self.assertEqual(exc.exception.status,503)
        with psycopg.connect(ADMIN) as con:
            self.assertEqual(con.execute("""SELECT count(*) FROM abc.eng19_review_inbox
                WHERE handoff_id=%s""",
                (link["candidate"]["message"]["handoff_id"],)).fetchone()[0],0)
        self.assertEqual(self._deliver_saved_eng04(link)["status"],
                         "RECORDED_REVIEW_ONLY")

    def test_eng04_network_outage_retry_fresh_jwt_no_duplicate_receipt(self):
        from abc_foundation.eng19_review_transport import (
            deliver_review_with_bounded_retry,send_local_review_handoff)
        link=self._eng04_same_artifact_authenticated_receiver()
        fixture=link["fixture"]
        hits=[]
        def flaky(**kwargs):
            hits.append(1)
            if len(hits)==1:
                raise OSError("simulated_loopback_outage")
            return send_local_review_handoff(**kwargs)
        receipt=deliver_review_with_bounded_retry(
            transport=flaky,token_provider=fixture.token,max_attempts=2,
            port=link["server"].server_address[1],
            message=link["candidate"]["message"],
            source_artifact=link["candidate"]["source_artifact"],
            client_cert=fixture.client_cert,client_key=fixture.client_key,
            server_ca=fixture.ca_path)
        self.assertEqual(receipt["status"],"RECORDED_REVIEW_ONLY")
        self.assertEqual(len(hits),2)
        self.assertEqual(self._deliver_saved_eng04(link)["status"],
                         "ALREADY_RECORDED_REVIEW_ONLY")
        with psycopg.connect(ADMIN) as con:
            self.assertEqual(con.execute("""SELECT count(*)
                FROM abc.eng19_synthetic_jobs WHERE handoff_id=%s""",
                (link["candidate"]["message"]["handoff_id"],)).fetchone()[0],1)

    def test_eng04_independent_real_eng03_provenance_ack_and_held_eng05_candidate(self):
        worker,job,proof=self._eng04_real_ledger_fixture()
        claimed=worker.claim()
        self.assertEqual(claimed["job_id"],job)
        self.assertEqual(len(claimed["sources"]),4)
        report=worker.analyse(claimed)
        self.assertEqual(report["source_manifest_sha256"],
                         claimed["source_manifest_sha256"])
        receipt=worker.ack(claimed,report)
        self.assertEqual(receipt["status"],"ACKED_REVIEW_ONLY")
        self.assertFalse(receipt["downstream_dispatched"])
        self.assertIsNone(worker.claim())
        candidate=worker.review_candidate(
            job,correlation_id=str(uuid.uuid4()),handoff_id=str(uuid.uuid4()))
        self.assertEqual(candidate["message"]["artifact_kind"],
                         "BEAUTY_ANALYSIS_REPORT")
        self.assertEqual(candidate["message"]["from_engine"],"ENG-04")
        self.assertEqual(candidate["message"]["to_engine"],"ENG-05")
        self.assertEqual(candidate["source_artifact"],report)
        self.assertFalse(candidate["dispatch_authorized"])
        with psycopg.connect(ADMIN) as con:
            row=con.execute("""SELECT status,attempts FROM abc.eng04_ci_jobs
                WHERE job_id=%s""",(job,)).fetchone()
            stored=con.execute("""SELECT status,output_sha256,
                source_manifest_sha256 FROM abc.eng04_ci_results
                WHERE job_id=%s""",(job,)).fetchone()
        self.assertEqual(row,("ACKED",1))
        self.assertEqual(stored[0],"BLOCKED_PENDING_AUTHORITY")
        self.assertEqual(stored[2],claimed["source_manifest_sha256"])

    def test_eng04_actual_separate_os_process_from_verified_eng03_ledger(self):
        import subprocess
        import sys
        worker,job,proof=self._eng04_real_ledger_fixture()
        proc=subprocess.run(
            [sys.executable,"-m","abc_foundation.eng04_review_worker"],
            env={**os.environ,"ABC_ENG04_CI_CONSUMER":self.consumer},
            capture_output=True,text=True,timeout=15)
        self.assertEqual(proc.returncode,0,proc.stderr)
        data=json.loads(proc.stdout)
        self.assertEqual(data["engine_id"],"ENG-04")
        self.assertEqual(data["status"],"ACKED_REVIEW_ONLY")
        self.assertFalse(data["downstream_dispatched"])
        self.assertIsNone(worker.process_once())
        exported=worker.review_candidate(job,correlation_id=str(uuid.uuid4()),
                                        handoff_id=str(uuid.uuid4()))
        self.assertEqual(exported["message"]["to_engine"],"ENG-05")
        self.assertFalse(exported["dispatch_authorized"])

    def test_eng04_separate_worker_parallel_claim_and_stale_lease_fencing(self):
        worker,job,proof=self._eng04_real_ledger_fixture()
        with ThreadPoolExecutor(max_workers=4) as pool:
            leases=list(pool.map(lambda _:worker.claim(),range(4)))
        claims=[x for x in leases if x is not None]
        self.assertEqual(len(claims),1)
        stale=claims[0]
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.eng04_ci_jobs SET
                lease_until=clock_timestamp()-interval '1 second'
                WHERE job_id=%s""",(job,))
        latest=worker.claim()
        self.assertNotEqual(stale["lease_token"],latest["lease_token"])
        with self.assertRaises(DomainError):
            worker.ack(stale,worker.analyse(stale))
        self.assertEqual(worker.ack(latest,worker.analyse(latest))["status"],
                         "ACKED_REVIEW_ONLY")
        with psycopg.connect(ADMIN) as con:
            count=con.execute("""SELECT count(*) FROM abc.eng04_ci_results
                WHERE job_id=%s""",(job,)).fetchone()[0]
        self.assertEqual(count,1)

    def test_eng04_db_broker_denies_forged_attribute_with_valid_manifest(self):
        from abc_foundation.eng05_review_worker import canonical_bytes
        worker,job,proof=self._eng04_real_ledger_fixture()
        claim=worker.claim()
        report=worker.analyse(claim)
        tampered=json.loads(json.dumps(report))
        tampered["attributes"][0]["value"]="FABRICATED"
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            with psycopg.connect(os.environ["ABC_TEST_PG_ENG04_LOGIN_DSN"]) as con:
                con.execute("SET LOCAL ROLE abc_eng04_worker")
                con.execute("""SELECT abc.eng04_ci_ack(%s,%s,%s,%s)""",
                    (job,claim["lease_token"],claim["source_manifest_sha256"],
                     canonical_bytes(tampered)))
        self.assertEqual(worker.ack(claim,report)["status"],
                         "ACKED_REVIEW_ONLY")
        with psycopg.connect(ADMIN) as con:
            self.assertEqual(con.execute("""SELECT count(*) FROM abc.eng04_ci_results
                WHERE job_id=%s""",(job,)).fetchone()[0],1)

    def test_eng04_independent_binding_revocation_blocks_ack(self):
        worker,job,proof=self._eng04_real_ledger_fixture()
        claim=worker.claim()
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.eng04_ci_worker_bindings SET active=false
                WHERE consumer_id=%s AND tenant_id=%s
                  AND login_name='abc_eng04_ci_login'""",
                (self.consumer,self.tenant))
        with self.assertRaises(DomainError):
            worker.ack(claim,worker.analyse(claim))
        with psycopg.connect(ADMIN) as con:
            self.assertEqual(con.execute("""SELECT count(*) FROM abc.eng04_ci_results
                WHERE job_id=%s""",(job,)).fetchone()[0],0)

    def test_eng04_worker_retry_then_terminal_dlq_without_handoff(self):
        worker,job,proof=self._eng04_real_ledger_fixture()
        for index in range(3):
            claim=worker.claim()
            self.assertEqual(claim["attempt"],index+1)
            self.assertEqual(worker.fail(claim,"CI_INJECTED_FAILURE"),
                "DLQ" if index==2 else "QUEUED")
            if index<2:
                with psycopg.connect(ADMIN) as con:
                    con.execute("""UPDATE abc.eng04_ci_jobs
                      SET available_at=clock_timestamp()-interval '1 second'
                      WHERE job_id=%s""",(job,))
        self.assertIsNone(worker.claim())
        with psycopg.connect(ADMIN) as con:
            status=con.execute("""SELECT status,attempts FROM abc.eng04_ci_jobs
                WHERE job_id=%s""",(job,)).fetchone()
            count=con.execute("""SELECT count(*) FROM abc.eng04_ci_results
                WHERE job_id=%s""",(job,)).fetchone()[0]
        self.assertEqual(status,("DLQ",3))
        self.assertEqual(count,0)

    def test_eng04_real_eng03_consent_revocation_prevents_ack_and_export(self):
        worker,job,proof=self._eng04_real_ledger_fixture()
        claim=worker.claim()
        self.assertIsNotNone(claim)
        report=worker.analyse(claim)
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.consent_evidence
                SET status='WITHDRAWN',revoked_at=clock_timestamp()
                WHERE consent_id=%s""",(proof,))
        with self.assertRaises(DomainError):
            worker.ack(claim,report)
        with self.assertRaises(DomainError):
            worker.review_candidate(
                job,correlation_id=str(uuid.uuid4()),handoff_id=str(uuid.uuid4()))
        with psycopg.connect(ADMIN) as con:
            self.assertEqual(con.execute("""SELECT count(*)
                FROM abc.eng04_ci_results WHERE job_id=%s""",
                (job,)).fetchone()[0],0)

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
        fixture_pipeline=SyntheticAnalysisPipeline(self.pipeline_dsn,self.consumer,knowledge_fixture=FIXTURE)
        for _ in range(4):
            item=fixture_pipeline.claim()
            self.assertIsNotNone(item)
            fixture_pipeline.complete(item["job_id"],item["lease_token"])
        with psycopg.connect(ADMIN) as con:
            row=con.execute("""SELECT decision_json,analysis_json,knowledge_json
                FROM abc.eng04_06_results WHERE session_id=%s AND aggregate_version=4""",
                (self.sid,)).fetchone()
        self.assertEqual(len(row[0]["candidates"]),1)
        with psycopg.connect(ADMIN) as con:
            previous=con.execute("""SELECT decision_json FROM abc.eng04_06_results
                 WHERE session_id=%s AND aggregate_version<4
                 ORDER BY aggregate_version""",(self.sid,)).fetchall()
        self.assertEqual(len(previous),3)
        self.assertTrue(all(not r[0]["candidates"] for r in previous))
        self.assertEqual(row[0]["candidates"][0]["feasibility_label"],"PROFESSIONAL_CHECK_REQUIRED")
        self.assertEqual(row[1]["unknowns"],[])
        self.assertEqual(row[2]["retrieval_sources"][0]["validated_by"],"TEST_FIXTURE_ONLY")

    def test_engine_runner_injection_preserves_persistent_provenance_and_ack(self):
        from abc_foundation.isolated_engine_runner import IsolatedEngineRunner
        class TraceRunner:
            def __init__(self):self.engine_ids=[]
            def call(self,engine_id,**kwargs):
                self.engine_ids.append(engine_id)
                return IsolatedEngineRunner().call(engine_id,**kwargs)
        self.arrive()
        self.worker.run_once()
        traced=TraceRunner()
        worker=SyntheticAnalysisPipeline(self.pipeline_dsn,self.consumer,
                                          engine_runner=traced)
        self.assertEqual(worker.run_once(),"ACKED")
        self.assertEqual(traced.engine_ids,["ENG-04","ENG-05","ENG-06"])
        self.assertEqual(self.count("abc.eng04_06_results"),1)
        self.assertIsNone(worker.run_once())

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
        with self.worker._connect() as con:
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
        with self.pipeline._connect() as con:
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
        for engine in (self.worker,self.pipeline):
            with self.assertRaises(DomainError) as denied:
                engine.claim()
            self.assertEqual(denied.exception.status,403)

    def test_two_authorized_consumers_keep_independent_evidence_lineage(self):
        # Same verified source can be independently delivered to two
        # admin-provisioned consumers without foreign-key cross-linking or
        # a global answer/evidence ID collision.
        other="eng03-second-"+uuid.uuid4().hex[:12]
        with psycopg.connect(ADMIN) as con:
            con.execute("""INSERT INTO abc.worker_subscriptions
                (consumer_id,tenant_id,event_type,active)
                VALUES(%s,%s,'ANSWER_RECORDED',true)""",(other,self.tenant))
            for role in ("abc_eng03_worker","abc_pipeline_worker"):
                con.execute("""INSERT INTO abc.eng03_worker_bindings
                   (worker_role,consumer_id,tenant_id,active)
                   VALUES(%s,%s,%s,true)""",(role,other,self.tenant))
        receipt=self.arrive()
        self.assertEqual(AnswerIndexConsumer(ANSWER,other).run_once(),"PROJECTED")
        first=self.worker.claim()
        other_e3,other_p6,_,_=self._provision_scoped_worker_logins(other)
        second_worker=ENG03Executor(other_e3,other)
        second=second_worker.claim()
        self.assertEqual(first["source_event_id"],second["source_event_id"])
        self.worker.complete(first["job_id"],first["lease_token"])
        second_worker.complete(second["job_id"],second["lease_token"])
        with psycopg.connect(ADMIN) as con:
            rows=con.execute("""SELECT evidence_id,source_answer_id,consumer_id
               FROM abc.eng03_evidence_ledger WHERE session_id=%s""",
               (self.sid,)).fetchall()
            self.assertEqual(len(rows),2)
            self.assertEqual({r[2] for r in rows},{self.consumer,other})
            self.assertEqual(len({r[0] for r in rows}),2)
            self.assertEqual({str(r[1]) for r in rows},{receipt["answer_id"]})
        self.assertEqual(SyntheticAnalysisPipeline(other_p6,other).run_once(),"ACKED")
        self.assertEqual(self.pipeline.run_once(),"ACKED")
        self.assertEqual(self.count("abc.eng04_06_results"),2)

    def test_pipeline_role_cannot_read_eng03_fencing_secrets(self):
        with self.pipeline._connect() as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("SELECT source_lease_token FROM abc.eng03_evidence_ledger")

    def test_shared_engine_groups_cannot_login_after_hardening(self):
        for direct in (ENG03,PIPELINE):
            with self.subTest(direct=direct.split("@")[0][:24]):
                with self.assertRaises(psycopg.OperationalError):
                    psycopg.connect(direct,connect_timeout=3)

    def test_valid_workload_login_cannot_claim_another_consumer(self):
        other="eng03-denied-"+uuid.uuid4().hex[:12]
        with psycopg.connect(ADMIN) as con:
            con.execute("""INSERT INTO abc.worker_subscriptions
              (consumer_id,tenant_id,event_type,active)
              VALUES(%s,%s,'ANSWER_RECORDED',true)""",(other,self.tenant))
            for role in ("abc_eng03_worker","abc_pipeline_worker"):
                con.execute("""INSERT INTO abc.eng03_worker_bindings
                    (worker_role,consumer_id,tenant_id,active)
                    VALUES(%s,%s,%s,true)""",(role,other,self.tenant))
        with self.assertRaises(DomainError) as e:
            ENG03Executor(self.eng03_dsn,other).claim()
        self.assertEqual(e.exception.status,403)
        with self.assertRaises(DomainError) as e:
            SyntheticAnalysisPipeline(self.pipeline_dsn,other).claim()
        self.assertEqual(e.exception.status,403)

    def test_revoked_individual_db_login_blocks_claim(self):
        self.arrive()
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.worker_login_bindings
                SET active=false WHERE login_name=%s""",(self.worker_login_eng03,))
        with self.assertRaises(DomainError) as e:
            self.worker.claim()
        self.assertEqual(e.exception.status,403)
        with psycopg.connect(ADMIN) as con:
            self.assertEqual(con.execute(
                "SELECT count(*) FROM abc.eng03_input_jobs WHERE consumer_id=%s AND status='LEASED'",
                (self.consumer,)).fetchone()[0],0)

    def test_workload_cannot_change_engine_role(self):
        with psycopg.connect(self.eng03_dsn) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("SET ROLE abc_pipeline_worker")
        with psycopg.connect(self.pipeline_dsn) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("SET ROLE abc_eng03_worker")

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

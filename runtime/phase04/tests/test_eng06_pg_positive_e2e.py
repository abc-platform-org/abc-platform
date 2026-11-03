"""Disposable PostgreSQL ENG05->ENG06 synthetic positive Claim/Lease/ACK.

CI administrator seeds only already-blocked upstream artifacts; never dispatches
ENG05, ENG07 or customer decisions. No real professional sources are used.
"""
import hashlib
import json
import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from abc_foundation.eng06_review_worker import SyntheticEng06ReviewWorker
from abc_foundation.pg_store import PostgresStore
from abc_foundation.eng05_review_worker import canonical_bytes

ADMIN=os.getenv("ABC_TEST_PG_ADMIN_DSN")
WORKER=os.getenv("ABC_TEST_PG_ENG06_LOGIN_DSN")

@unittest.skipUnless(os.getenv("ABC_ENV")=="LOCAL_INTEGRATION_ONLY" and ADMIN and WORKER,
                     "disposable PostgreSQL only")
class Eng06PositivePostgresTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg.conninfo import conninfo_to_dict
        self.assertEqual(conninfo_to_dict(ADMIN).get("dbname"),"abc_phase04_ci")
        self.assertEqual(conninfo_to_dict(WORKER).get("user"),"abc_eng06_ci_login")
        self.sid=uuid.uuid4()
        self.handoff=uuid.uuid4()
        self.consumer="ci-eng06-"+uuid.uuid4().hex[:16]
        self.tenant="tenant-test"
        self.branch="branch-test"
        now=datetime.now(timezone.utc)
        self.analysis={
            "session_id":str(self.sid),"service_id":"synthetic:hair-color",
            "service_scope":"SYNTHETIC_NON_MEDIA_ONLY",
            "engine_version":"eng04.synthetic-evidence.1",
            "evidence_ids":["ci:prior_treatment","ci:sensitivity_flag","ci:goal","ci:maintenance"],
            "attributes":[
                {"key":key,"value":value,"evidence_class":"USER_REPORTED",
                 "source_evidence_id":"ci:"+key}
                for key,value in (("prior_treatment","NO"),("sensitivity_flag","NO"),
                                  ("goal","SUBTLE"),("maintenance","LOW"))]
        }
        self.knowledge={
            "session_id":str(self.sid),"service_id":"synthetic:hair-color",
            "ontology_version":"synthetic-ontology.1",
            "retrieval_sources":[],"grounded_facts":[],
            "unknowns":["SOURCE_UNVERIFIED"]}
        a=canonical_bytes(self.analysis)
        k=canonical_bytes(self.knowledge)
        self.asha=hashlib.sha256(a).hexdigest()
        self.ksha=hashlib.sha256(k).hexdigest()
        with psycopg.connect(ADMIN) as con:
            con.execute("INSERT INTO abc.tenants(tenant_id) VALUES(%s) ON CONFLICT DO NOTHING",(self.tenant,))
            con.execute("""INSERT INTO abc.branches(tenant_id,branch_id)
                           VALUES(%s,%s) ON CONFLICT DO NOTHING""",(self.tenant,self.branch))
            con.execute("""INSERT INTO abc.sessions(session_id,tenant_id,branch_id,
                specialist_id,client_id,service_id,state,state_version,
                created_at,updated_at,last_event_id)
                VALUES(%s,%s,%s,'ci-specialist','ci-client','synthetic:hair-color',
                       'CREATED',2,%s,%s,%s)""",
                (self.sid,self.tenant,self.branch,now,now,uuid.uuid4()))
            consent=uuid.uuid4()
            con.execute("""INSERT INTO abc.consent_evidence(
                consent_id,tenant_id,branch_id,session_id,client_id,status,
                purpose,evidence_digest,disclosure_version,retention_policy_id)
                VALUES(%s,%s,%s,%s,'ci-client','PENDING_VERIFICATION',
                ARRAY['AI_PROCESSING','INTERNAL_HANDOFF'],%s,
                'CI-SYNTHETIC-NOT-LEGAL','CI-RETENTION-NO-CLIENT')""",
                (consent,self.tenant,self.branch,self.sid,"c"*64))
            con.execute("""UPDATE abc.consent_evidence
                SET status='ACTIVE',verified_at=%s,valid_until=%s
                WHERE consent_id=%s""",(now,now+timedelta(hours=1),consent))
            self.consent=consent
            con.execute("""INSERT INTO abc.eng19_review_inbox(
                handoff_id,tenant_id,branch_id,session_id,state_version,
                correlation_id,from_engine,to_engine,artifact_kind,message_sha256)
                VALUES(%s,%s,%s,%s,2,%s,'ENG-04','ENG-05',
                       'BEAUTY_ANALYSIS_REPORT',%s)""",
                (self.handoff,self.tenant,self.branch,self.sid,uuid.uuid4(),"d"*64))
            con.execute("""INSERT INTO abc.eng19_synthetic_jobs(
                handoff_id,tenant_id,branch_id,session_id,state_version,
                consumer_id,source_bytes,source_sha256,status,attempts)
                VALUES(%s,%s,%s,%s,2,%s,%s,%s,'ACKED',1)""",
                (self.handoff,self.tenant,self.branch,self.sid,self.consumer,a,self.asha))
            con.execute("""INSERT INTO abc.eng19_synthetic_results(
                handoff_id,worker_lease,consumer_id,engine_id,engine_version,
                source_sha256,output_sha256,output_bytes)
                VALUES(%s,%s,%s,'ENG-05','synthetic-ontology.1',%s,%s,%s)""",
                (self.handoff,uuid.uuid4(),self.consumer,self.asha,self.ksha,k))
            con.execute("""INSERT INTO abc.eng19_synthetic_outbox(
                handoff_id,target_handoff_id,from_engine,to_engine,artifact_kind,
                artifact_sha256,status)
                VALUES(%s,%s,'ENG-05','ENG-06','PROFESSIONAL_KNOWLEDGE_BUNDLE',
                       %s,'BLOCKED_PENDING_AUTHORITY')""",
                (self.handoff,uuid.uuid4(),self.ksha))
            con.execute("""INSERT INTO abc.eng06_ci_worker_bindings(
                login_name,consumer_id,tenant_id,active)
                VALUES('abc_eng06_ci_login',%s,%s,true)
                ON CONFLICT(login_name) DO UPDATE SET
                consumer_id=excluded.consumer_id,tenant_id=excluded.tenant_id,active=true""",
                (self.consumer,self.tenant))
            con.execute("""INSERT INTO abc.eng06_ci_jobs(
                upstream_handoff,consumer_id,tenant_id,branch_id,
                session_id,state_version)
                VALUES(%s,%s,%s,%s,%s,2)""",
                (self.handoff,self.consumer,self.tenant,self.branch,self.sid))
        self.worker=SyntheticEng06ReviewWorker(
            store=PostgresStore(WORKER),consumer_id=self.consumer)

    def test_real_claim_ack_persist_and_replay_denied(self):
        import psycopg
        claim=self.worker.claim()
        self.assertIsNotNone(claim)
        self.assertEqual(claim["attempt"],1)
        result=self.worker.decide_blocked(claim)
        self.assertEqual(result["status"],"BLOCKED_PROFESSIONAL_SOURCE")
        receipt=self.worker.ack(claim,result)
        self.assertEqual(receipt["status"],"ACKED_BLOCKED_REVIEW_ONLY")
        self.assertFalse(receipt["downstream_dispatched"])
        self.assertIsNone(self.worker.claim())
        with psycopg.connect(ADMIN) as con:
            row=con.execute("""SELECT j.status,r.status,r.output_sha256,
                o.status FROM abc.eng06_ci_jobs j
                JOIN abc.eng06_ci_results r USING(upstream_handoff)
                JOIN abc.eng19_synthetic_outbox o ON o.handoff_id=j.upstream_handoff
                WHERE j.upstream_handoff=%s""",(self.handoff,)).fetchone()
        self.assertEqual(row[0],"ACKED")
        self.assertEqual(row[1],"BLOCKED_PROFESSIONAL_SOURCE")
        self.assertEqual(row[2],receipt["output_sha256"])
        self.assertEqual(row[3],"BLOCKED_PENDING_AUTHORITY")
        with self.assertRaises(Exception):
            self.worker.ack(claim,result)

    def test_expired_lease_reclaim_fences_old_ack(self):
        import psycopg
        old=self.worker.claim()
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.eng06_ci_jobs
                SET lease_until=clock_timestamp()-interval '1 second'
                WHERE upstream_handoff=%s""",(self.handoff,))
        fresh=self.worker.claim()
        self.assertEqual(fresh["attempt"],2)
        self.assertNotEqual(old["lease_token"],fresh["lease_token"])
        with self.assertRaises(Exception):
            self.worker.ack(old,self.worker.decide_blocked(old))
        self.assertEqual(self.worker.ack(fresh,self.worker.decide_blocked(fresh))["status"],
                         "ACKED_BLOCKED_REVIEW_ONLY")

    def test_concurrent_claim_only_one_wins(self):
        def attempt(_):
            return SyntheticEng06ReviewWorker(
                store=PostgresStore(WORKER),consumer_id=self.consumer).claim()
        with ThreadPoolExecutor(max_workers=2) as pool:
            claims=list(pool.map(attempt,range(2)))
        self.assertEqual(sum(x is not None for x in claims),1)

    def test_revoked_consent_between_claim_and_ack_denied(self):
        import psycopg
        claim=self.worker.claim()
        result=self.worker.decide_blocked(claim)
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.consent_evidence
                SET status='WITHDRAWN',revoked_at=clock_timestamp()
                WHERE consent_id=%s""",(self.consent,))
        with self.assertRaises(Exception):
            self.worker.ack(claim,result)
        with psycopg.connect(ADMIN) as con:
            count=con.execute("""SELECT count(*) FROM abc.eng06_ci_results
                WHERE upstream_handoff=%s""",(self.handoff,)).fetchone()[0]
        self.assertEqual(count,0)

if __name__=="__main__":
    unittest.main()

"""Isolated ENG04 synthetic worker: provenance, identity and no-release tests."""
import hashlib
import os
import unittest
import uuid
from datetime import datetime,timedelta,timezone

import psycopg
from psycopg.rows import dict_row

from abc_foundation.eng04_review_worker import SyntheticEng04ReviewWorker
from abc_foundation.eng05_review_worker import canonical_bytes
from abc_foundation.pg_store import PostgresStore
from abc_foundation.store import DomainError

FIELDS=("prior_treatment","sensitivity_flag","goal","maintenance")

class PureProvenanceTests(unittest.TestCase):
    def setUp(self):
        class NoDatabase:
            def _connect(self):
                raise AssertionError("pure evidence test must never access database")
        self.worker=SyntheticEng04ReviewWorker(
            store=NoDatabase(),consumer_id="ci-eng04-pure")
        self.session=str(uuid.uuid4())
        src=[]
        for key in FIELDS:
            record={"evidence_id":str(uuid.uuid4()),"session_id":self.session,
              "service_id":"synthetic:hair-color","attribute_key":key,
              "value":"COOLER_BROWN" if key=="goal" else "NO",
              "evidence_class":"USER_REPORTED","source_type":"CLIENT_ANSWER"}
            src.append({"evidence":record,"evidence_id":record["evidence_id"],
              "digest":hashlib.sha256(canonical_bytes(record)).hexdigest(),
              "source_job_id":str(uuid.uuid4()),
              "source_answer_id":str(uuid.uuid4()),
              "policy_decision_id":str(uuid.uuid4())})
        manifest="|".join(sorted(s["evidence_id"]+":"+s["digest"] for s in src))
        self.claim={"engine_id":"ENG-04","artifact_kind":"BEAUTY_ANALYSIS_REPORT",
          "consumer_id":"ci-eng04-pure","session_id":self.session,
          "sources":src,"source_manifest_sha256":
             hashlib.sha256(manifest.encode()).hexdigest()}

    def test_report_deterministic_shape_from_four_verified_sources(self):
        output=self.worker.analyse(self.claim)
        self.assertEqual(output["engine_version"],"eng04.synthetic-evidence.1")
        self.assertEqual(output["service_scope"],"SYNTHETIC_NON_MEDIA_ONLY")
        self.assertEqual(len(output["evidence_ids"]),4)

    def test_tamper_record_digest_and_manifest_rejected(self):
        a=self.claim["sources"][0]["evidence"]
        a["value"]="INVENTED"
        with self.assertRaises(DomainError):
            self.worker.analyse(self.claim)
        a["value"]="NO"
        self.claim["source_manifest_sha256"]="0"*64
        with self.assertRaises(DomainError):
            self.worker.analyse(self.claim)

    def test_duplicate_attribute_forged_policy_and_missing_evidence_rejected(self):
        self.claim["sources"][1]["evidence"]["attribute_key"]="prior_treatment"
        with self.assertRaises(DomainError):
            self.worker.analyse(self.claim)
        self.claim["sources"][1]["evidence"]["attribute_key"]="sensitivity_flag"
        self.claim["sources"][0]["policy_decision_id"]=None
        with self.assertRaises(DomainError):
            self.worker.analyse(self.claim)
        self.claim["sources"].pop()
        with self.assertRaises(DomainError):
            self.worker.analyse(self.claim)

class PgEng04WorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dsn=os.environ.get("ABC_TEST_PG_ENG04_LOGIN_DSN")
        cls.admin=os.environ.get("ABC_TEST_PG_ADMIN_DSN")
        if not cls.dsn or not cls.admin or os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
            raise unittest.SkipTest("disposable PG CI environment only")

    def setUp(self):
        self.consumer="ci-eng04-"+uuid.uuid4().hex[:20]
        self.session=str(uuid.uuid4())
        self.job=str(uuid.uuid4())
        self.worker=SyntheticEng04ReviewWorker(
            store=PostgresStore(self.dsn),consumer_id=self.consumer)
        now=datetime.now(timezone.utc)
        self.tenant="tenant-test"
        with psycopg.connect(self.admin,autocommit=True) as con:
            con.execute("INSERT INTO abc.tenants(tenant_id) VALUES(%s) ON CONFLICT DO NOTHING",
                        (self.tenant,))
            con.execute("""INSERT INTO abc.branches(tenant_id,branch_id)
                           VALUES(%s,'branch-test') ON CONFLICT DO NOTHING""",
                           (self.tenant,))
            con.execute("""INSERT INTO abc.sessions(session_id,tenant_id,
                 branch_id,specialist_id,client_id,service_id,state,state_version,
                 created_at,updated_at,last_event_id)
                 VALUES(%s,%s,'branch-test','specialist-ci','client-ci',
                 'synthetic:hair-color','CREATED',2,%s,%s,%s)""",
                 (self.session,self.tenant,now,now,uuid.uuid4()))
            consent=str(uuid.uuid4())
            con.execute("""INSERT INTO abc.consent_evidence(
                 consent_id,tenant_id,branch_id,session_id,client_id,status,
                 purpose,evidence_digest,disclosure_version,retention_policy_id)
                 VALUES(%s,%s,'branch-test',%s,'client-ci','PENDING_VERIFICATION',
                 ARRAY['AI_PROCESSING','INTERNAL_HANDOFF'],%s,
                 'CI-NOT-LEGAL','CI-NO_CLIENT')""",
                 (consent,self.tenant,self.session,"a"*64))
            con.execute("""UPDATE abc.consent_evidence SET status='ACTIVE',
                 verified_at=%s,valid_until=%s WHERE consent_id=%s""",
                 (now,now+timedelta(hours=1),consent))
            con.execute("""INSERT INTO abc.eng04_ci_worker_bindings
                (login_name,consumer_id,tenant_id,active)
                VALUES('abc_eng04_ci_login',%s,%s,true)""",
                (self.consumer,self.tenant))
            con.execute("""INSERT INTO abc.eng04_ci_jobs
                (job_id,tenant_id,branch_id,session_id,consumer_id,state_version)
                VALUES(%s,%s,'branch-test',%s,%s,2)""",
                (self.job,self.tenant,self.session,self.consumer))

    def test_worker_denies_unproven_eng03_source_and_keeps_job_unleased(self):
        with self.assertRaises(DomainError):
            self.worker.claim()
        with psycopg.connect(self.admin) as con:
            row=con.execute("""SELECT status,attempts FROM abc.eng04_ci_jobs
                WHERE job_id=%s""",(self.job,)).fetchone()
        self.assertEqual(row,("QUEUED",0))

    def test_eng05_and_legacy_pipeline_cannot_claim_eng04_or_read_tables(self):
        with psycopg.connect(self.admin) as con:
            priv=con.execute("""SELECT
                has_function_privilege('abc_eng05_worker',
                    'abc.eng04_ci_claim(text,integer)','EXECUTE'),
                has_function_privilege('abc_pipeline_worker',
                    'abc.eng04_ci_ack(uuid,uuid,text,bytea)','EXECUTE'),
                has_function_privilege('abc_eng04_worker',
                    'abc.eng04_ci_claim(text,integer)','EXECUTE')""").fetchone()
            self.assertEqual(priv,(False,False,True))
            row=con.execute("""SELECT relrowsecurity,relforcerowsecurity FROM pg_class
                WHERE oid='abc.eng04_ci_jobs'::regclass""").fetchone()
            self.assertEqual(row,(True,True))
        for login in (self.dsn,os.environ["ABC_TEST_PG_ENG05_LOGIN_DSN"]):
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                with psycopg.connect(login) as con:
                    con.execute("SELECT * FROM abc.eng04_ci_jobs")

    def test_revoked_eng04_identity_denies_claim_and_report_export(self):
        with psycopg.connect(self.admin,autocommit=True) as con:
            con.execute("""UPDATE abc.eng04_ci_worker_bindings SET active=false
                WHERE login_name='abc_eng04_ci_login'
                AND consumer_id=%s""",(self.consumer,))
        with self.assertRaises(DomainError):
            self.worker.claim()
        with self.assertRaises(DomainError):
            self.worker.review_candidate(self.job,
                correlation_id=str(uuid.uuid4()),handoff_id=str(uuid.uuid4()))

if __name__=="__main__":
    unittest.main()

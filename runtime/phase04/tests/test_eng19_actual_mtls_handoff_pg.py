"""CI-only actual TLS1.3 producer→consumer, live PG16 consent and inbox.

All identity keys/certificates are ephemeral and test-generated. The policy,
session and consent authority doubles are not production implementations.
"""
import copy
import os
import ssl
import socket
import threading
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone

import psycopg
from psycopg.rows import dict_row

from abc_foundation.pg_store import PostgresStore
from abc_foundation.distributed_replay import PostgresReplayLedger
from abc_foundation.eng19_review_consumer import (
    PostgresReviewInbox,AuthenticatedReviewConsumer)
from abc_foundation.eng19_review_transport import (
    start_local_review_consumer,send_local_review_handoff)
from abc_foundation.store import DomainError
from test_private_engine_mtls import ManagedWorkloadMTLSTests


class AuthorityFixture:
    def __init__(self,session,gate="ALL",*,source="ENG-04",target="ENG-05",artifact="BEAUTY_ANALYSIS_REPORT"):
        self.session=session
        self.allowed=True
        self.gate=gate
        self.source=source
        self.target=target
        self.artifact=artifact
    def verify(self,**claims):
        return (self.allowed and claims.get("tenant_id")=="tenant-test"
            and claims.get("branch_id")=="branch-test"
            and claims.get("session_id")==self.session
            and claims.get("state_version")==2
            and claims.get("from_engine")==self.source
            and claims.get("to_engine")==self.target
            and claims.get("artifact_kind")==self.artifact
            and claims.get("certificate_sha256") is not None
            and claims.get("policy_proof_ref")=="synthetic:eng14-policy-proof"
            and (self.gate!="CONSENT" or
                claims.get("purposes")==("AI_PROCESSING","INTERNAL_HANDOFF")))


class RealReviewConsumerE2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=os.environ.get("ABC_TEST_PG_DSN")
        cls.admin=os.environ.get("ABC_TEST_PG_ADMIN_DSN")
        if (not cls.app or not cls.admin or
            os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY"):
            raise unittest.SkipTest("disposable PostgreSQL16 integration fixture required")

    def setUp(self):
        self.fixture=ManagedWorkloadMTLSTests("test_real_tls13_mutual_certificate_and_bound_jwt")
        # Every test owns a distinct authenticated consumer, certificate SAN,
        # JWT subject and subscription. An older QUEUED job must never be
        # claimable by a later test's worker.
        self.fixture.consumer_override="ci-review-"+uuid.uuid4().hex[:20]
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.session=str(uuid.uuid4())
        now=datetime.now(timezone.utc)
        self.consent=str(uuid.uuid4())
        with psycopg.connect(self.admin,autocommit=True) as con:
            con.execute("INSERT INTO abc.tenants(tenant_id) VALUES('tenant-test') ON CONFLICT DO NOTHING")
            con.execute("""INSERT INTO abc.branches(tenant_id,branch_id)
                VALUES('tenant-test','branch-test') ON CONFLICT DO NOTHING""")
            con.execute("""INSERT INTO abc.sessions(
                session_id,tenant_id,branch_id,specialist_id,client_id,
                service_id,state,state_version,created_at,updated_at,last_event_id)
                VALUES(%s,'tenant-test','branch-test','specialist-ci',
                  'client-ci','synthetic:hair-color','CREATED',2,%s,%s,%s)""",
                  (self.session,now,now,uuid.uuid4()))
            # Respect the DB lifecycle: new consent must start PENDING.
            con.execute("""INSERT INTO abc.consent_evidence(
                consent_id,tenant_id,branch_id,session_id,client_id,status,
                purpose,evidence_digest,disclosure_version,retention_policy_id)
                VALUES(%s,'tenant-test','branch-test',%s,'client-ci',
                'PENDING_VERIFICATION',ARRAY['AI_PROCESSING','INTERNAL_HANDOFF'],%s,
                'CI-SYNTHETIC-NOT_LEGAL','CI-RETENTION-NO_CLIENT')""",
                (self.consent,self.session,"c"*64))
            con.execute("""UPDATE abc.consent_evidence
                SET status='ACTIVE',verified_at=%s,valid_until=%s
                WHERE consent_id=%s""",
                (now,now+timedelta(hours=1),self.consent))
        self.session_gate=AuthorityFixture(self.session)
        self.consent_gate=AuthorityFixture(self.session,"CONSENT")
        self.policy_gate=AuthorityFixture(self.session)
        store=PostgresStore(self.app)
        self.receiver=AuthenticatedReviewConsumer(
            identity_verifier=self.fixture.verifier,
            session_authority=self.session_gate,
            consent_authority=self.consent_gate,
            eng14_authority=self.policy_gate,
            replay_ledger=PostgresReplayLedger(store),
            inbox=PostgresReviewInbox(store),
            caller_engine="ENG-04",target_engine="ENG-05",
            consumer_id=self.fixture.consumer)
        self.listeners=[]
        self._start()
        self.message={
            "handoff_id":str(uuid.uuid4()),
            "contract_version":"abc.internal.capability.v3.review",
            "from_engine":"ENG-04","to_engine":"ENG-05",
            "tenant_id":"tenant-test","branch_id":"branch-test",
            "session_id":self.session,"state_version":2,
            "correlation_id":str(uuid.uuid4()),
            "artifact_kind":"BEAUTY_ANALYSIS_REPORT",
            "artifact_sha256":"d"*64,
            "evidence_refs":["synthetic:evidence-hash-v1"],
            "policy_proof_ref":"synthetic:eng14-policy-proof",
            "status":"CANDIDATE_FOR_EXTERNAL_AUTHORIZATION",
            "execution_authorized":False,
            "customer_release_approved":False}

    def _start(self):
        server=start_local_review_consumer(consumer=self.receiver,
            certfile=self.fixture.server_cert,keyfile=self.fixture.server_key,
            ca_file=self.fixture.ca_path)
        self.listeners.append(server)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server.server_address[1]

    def call(self,*,token=None,message=None,port=None):
        return send_local_review_handoff(
           port=port or self.listeners[0].server_address[1],
           token=self.fixture.token() if token is None else token,
           message=message if message is not None else self.message,
           client_cert=self.fixture.client_cert,
           client_key=self.fixture.client_key,
           server_ca=self.fixture.ca_path)

    def test_real_tls13_jwt_consent_and_pg_review_receipt(self):
        receipt=self.call()
        self.assertEqual(receipt["status"],"RECORDED_REVIEW_ONLY")
        self.assertTrue(receipt["durable_review_receipt"])
        self.assertFalse(receipt["consumer_execution_authorized"])
        with psycopg.connect(self.admin,row_factory=dict_row) as con:
            rows=con.execute("""SELECT handoff_id,to_engine,message_sha256
                     FROM abc.eng19_review_inbox WHERE handoff_id=%s""",
                     (self.message["handoff_id"],)).fetchall()
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["to_engine"],"ENG-05")

    def test_fresh_jwt_retry_exactly_idempotent_with_two_tls_listeners(self):
        second=self._start()
        first=self.call()
        self.assertEqual(first["status"],"RECORDED_REVIEW_ONLY")
        retry=self.call(port=second)
        self.assertEqual(retry["status"],"ALREADY_RECORDED_REVIEW_ONLY")
        self.assertEqual(first["handoff_id"],retry["handoff_id"])

    def test_same_signed_jti_cannot_replay_across_tls_listeners(self):
        second=self._start()
        token=self.fixture.token()
        self.assertEqual(self.call(token=token)["status"],"RECORDED_REVIEW_ONLY")
        self.assertEqual(self.call(token=token,port=second)["status"],"REJECTED")

    def test_parallel_distinct_signed_jwt_single_durable_record(self):
        second=self._start()
        def send(index):
            return self.call(port=(self.listeners[index%2].server_address[1]))
        with ThreadPoolExecutor(max_workers=6) as pool:
            results=list(pool.map(send,range(6)))
        self.assertEqual(sum(x["status"]=="RECORDED_REVIEW_ONLY" for x in results),1)
        self.assertEqual(sum(x["status"]=="ALREADY_RECORDED_REVIEW_ONLY" for x in results),5)

    def test_modifying_same_handoff_id_denied_even_new_jti(self):
        self.assertEqual(self.call()["status"],"RECORDED_REVIEW_ONLY")
        other=copy.deepcopy(self.message)
        other["artifact_sha256"]="e"*64
        denied=self.call(message=other)
        self.assertEqual(denied["status"],"REJECTED")

    def test_consent_withdrawal_fences_next_jti_at_database(self):
        self.assertEqual(self.call()["status"],"RECORDED_REVIEW_ONLY")
        with psycopg.connect(self.admin,autocommit=True) as con:
            con.execute("""UPDATE abc.consent_evidence
                  SET status='WITHDRAWN',revoked_at=clock_timestamp()
                  WHERE consent_id=%s""",(self.consent,))
        self.assertEqual(self.call()["status"],"REJECTED")

    def test_external_consent_denial_before_jti_claim(self):
        token=self.fixture.token()
        self.consent_gate.allowed=False
        self.assertEqual(self.call(token=token)["status"],"REJECTED")
        self.consent_gate.allowed=True
        self.assertEqual(self.call(token=token)["status"],"RECORDED_REVIEW_ONLY")

    def test_eng14_and_session_denial_before_jti_claim(self):
        for authority in (self.session_gate,self.policy_gate):
            token=self.fixture.token()
            authority.allowed=False
            self.assertEqual(self.call(token=token)["status"],"REJECTED")
            authority.allowed=True
            self.assertEqual(self.call(token=token)["status"],"RECORDED_REVIEW_ONLY")
            # Fresh handoff ID to avoid accidental idempotent replay in later round.
            self.message["handoff_id"]=str(uuid.uuid4())

    def test_scope_wrong_engine_and_legacy_contract_denied(self):
        for changes in (
          {"tenant_id":"other-tenant"},
          {"branch_id":"other-branch"},
          {"state_version":1},
          {"to_engine":"ENG-06"},
          {"contract_version":"abc.internal.engine.v2.draft"},
          {"policy_proof_ref":None},
          {"artifact_kind":"WRONG_ARTIFACT"},
          {"execution_authorized":True}
        ):
            with self.subTest(changes=changes):
                self.assertEqual(self.call(message={**self.message,**changes})["status"],"REJECTED")

    def test_wrong_cert_binding_and_missing_client_cert_denied(self):
        self.assertEqual(self.call(token=self.fixture.token(
            binding="invalid-thumbprint"))["status"],"REJECTED")
        ctx=ssl.create_default_context(ssl.Purpose.SERVER_AUTH,cafile=self.fixture.ca_path)
        # TLS client authentication alerts can surface at first READ rather
        # than wrap_socket or sendall, depending on OpenSSL scheduling.
        from abc_foundation.private_engine_transport import _read_frame
        with self.assertRaises((ssl.SSLError,OSError,ConnectionError,ValueError)):
            with socket.create_connection(("127.0.0.1",self.listeners[0].server_address[1])) as sock:
                with ctx.wrap_socket(sock,server_hostname="localhost") as secured:
                    secured.settimeout(4)
                    secured.sendall(b"abcd")
                    _read_frame(secured)

    def test_no_hosted_start_or_untrusted_public_endpoint(self):
        from unittest.mock import patch
        with patch.dict(os.environ,{"ABC_ENV":"STAGING_PRIVATE"}):
            with self.assertRaises(ValueError):
                self._start()
            with self.assertRaises(ValueError):
                self.call()

    def test_lost_reply_after_commit_retries_with_new_jwt_and_same_handoff(self):
        from abc_foundation.eng19_review_transport import (
            deliver_review_with_bounded_retry)
        attempts=[]
        def simulate_lost_first_ack(**kwargs):
            reply=send_local_review_handoff(**kwargs)
            attempts.append(reply["status"])
            if len(attempts)==1:
                raise ConnectionResetError("CI simulated lost ACK after COMMIT")
            return reply
        received=deliver_review_with_bounded_retry(
            token_provider=self.fixture.token,max_attempts=2,
            transport=simulate_lost_first_ack,
            port=self.listeners[0].server_address[1],message=self.message,
            client_cert=self.fixture.client_cert,
            client_key=self.fixture.client_key,
            server_ca=self.fixture.ca_path)
        self.assertEqual(attempts,["RECORDED_REVIEW_ONLY",
                                    "ALREADY_RECORDED_REVIEW_ONLY"])
        self.assertEqual(received["status"],"ALREADY_RECORDED_REVIEW_ONLY")

    def test_retry_prohibits_reusing_jwt_or_retrying_business_denial(self):
        from abc_foundation.eng19_review_transport import (
            deliver_review_with_bounded_retry)
        repeated=self.fixture.token()
        def outage(**_kw):
            raise ConnectionResetError("CI-disposable transport failure")
        args={"port":self.listeners[0].server_address[1],
              "message":self.message,
              "client_cert":self.fixture.client_cert,
              "client_key":self.fixture.client_key,
              "server_ca":self.fixture.ca_path}
        with self.assertRaises(DomainError):
            deliver_review_with_bounded_retry(token_provider=lambda:repeated,
                max_attempts=2,transport=outage,**args)
        calls=[]
        def deny(**_kw):
            calls.append(True)
            return {"status":"REJECTED",
                    "durable_review_receipt":False,
                    "consumer_execution_authorized":False,
                    "customer_release_approved":False}
        with self.assertRaises(DomainError):
            deliver_review_with_bounded_retry(token_provider=self.fixture.token,
                max_attempts=3,transport=deny,**args)
        self.assertEqual(len(calls),1)

    def test_review_inbox_direct_dml_is_not_an_application_capability(self):
        for statement in (
           "SELECT * FROM abc.eng19_review_inbox",
           """DELETE FROM abc.eng19_review_inbox WHERE handoff_id=
              '11111111-1111-4111-8111-111111111111'"""
        ):
            with self.subTest(statement=statement):
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    with psycopg.connect(self.app) as con:
                        con.execute(statement)

    def test_database_state_version_fence_rejects_authenticated_stale_handoff(self):
        with psycopg.connect(self.admin,autocommit=True) as con:
            # State itself is unchanged; no prohibited state-transition
            # trigger is bypassed. The snapshot version becomes stale.
            con.execute("""UPDATE abc.sessions
               SET state_version=state_version+1
               WHERE session_id=%s""",(self.session,))
        self.assertEqual(self.call()["status"],"REJECTED")

    def test_real_bounded_eng04_synthetic_output_over_authenticated_network(self):
        from abc_foundation.eng04_analysis import SyntheticBeautyAnalysis,FIELDS
        from abc_foundation.eng02_consultation import SYNTHETIC_SERVICE
        from abc_foundation.eng19_review_producer import (
            eng04_synthetic_analysis_candidate)
        from abc_foundation.eng19_review_consumer import _canonical_sha
        data=[{"attribute_key":key,"evidence_id":str(uuid.uuid4()),
               "service_id":SYNTHETIC_SERVICE,"session_id":self.session,
               "evidence_class":"USER_REPORTED","source_type":"CLIENT_ANSWER",
               "value":"NO" if key!="goal" else "COOLER_BROWN"}
              for key in sorted(FIELDS)]
        analysis=SyntheticBeautyAnalysis().analyse(
            session_id=self.session,evidence=data)
        message=eng04_synthetic_analysis_candidate(
            analysis=analysis,tenant_id="tenant-test",
            branch_id="branch-test",state_version=2,
            correlation_id=self.message["correlation_id"],
            handoff_id=self.message["handoff_id"],
            policy_proof_ref="synthetic:eng14-policy-proof")
        self.assertEqual(message["artifact_sha256"],_canonical_sha(analysis))
        receipt=self.call(message=message)
        self.assertEqual(receipt["status"],"RECORDED_REVIEW_ONLY")
        self.assertFalse(receipt["consumer_execution_authorized"])
        analysis["service_scope"]="REAL_CUSTOMER"
        with self.assertRaises(DomainError):
            eng04_synthetic_analysis_candidate(
                analysis=analysis,tenant_id="tenant-test",
                branch_id="branch-test",state_version=2,
                correlation_id=self.message["correlation_id"],
                handoff_id=str(uuid.uuid4()),
                policy_proof_ref="synthetic:eng14-policy-proof")

    def _synthetic_job(self):
        from abc_foundation.eng04_analysis import SyntheticBeautyAnalysis,FIELDS
        from abc_foundation.eng02_consultation import SYNTHETIC_SERVICE
        from abc_foundation.eng19_review_producer import eng04_synthetic_analysis_candidate
        from abc_foundation.eng05_review_worker import SyntheticEng05ReviewWorker
        from abc_foundation.pg_store import PostgresStore
        data=[{"attribute_key":key,"evidence_id":str(uuid.uuid4()),
               "service_id":SYNTHETIC_SERVICE,"session_id":self.session,
               "evidence_class":"USER_REPORTED","source_type":"CLIENT_ANSWER",
               "value":"NO" if key!="goal" else "COOLER_BROWN"}
              for key in sorted(FIELDS)]
        source=SyntheticBeautyAnalysis().analyse(
            session_id=self.session,evidence=data)
        msg=eng04_synthetic_analysis_candidate(
            analysis=source,tenant_id="tenant-test",branch_id="branch-test",
            state_version=2,correlation_id=self.message["correlation_id"],
            handoff_id=self.message["handoff_id"],
            policy_proof_ref="synthetic:eng14-policy-proof")
        with psycopg.connect(self.admin,autocommit=True) as con:
            con.execute("""INSERT INTO abc.worker_subscriptions(
                consumer_id,tenant_id,event_type,active)
                VALUES(%s,'tenant-test','SESSION_CREATED',true)
                ON CONFLICT(consumer_id) DO UPDATE SET active=true""",
                (self.fixture.consumer,))
            con.execute("""INSERT INTO abc.eng03_worker_bindings(
                worker_role,consumer_id,tenant_id,active)
                VALUES('abc_pipeline_worker',%s,'tenant-test',true)
                ON CONFLICT(worker_role,consumer_id,tenant_id)
                DO UPDATE SET active=true""",(self.fixture.consumer,))
            con.execute("""INSERT INTO abc.worker_login_bindings(
                login_name,worker_role,consumer_id,tenant_id,active)
                VALUES('abc_eng05_ci_login','abc_pipeline_worker',%s,'tenant-test',true)
                ON CONFLICT(login_name) DO UPDATE SET
                  worker_role=EXCLUDED.worker_role,
                  consumer_id=EXCLUDED.consumer_id,
                  tenant_id=EXCLUDED.tenant_id,active=true""",
                (self.fixture.consumer,))
        response=send_local_review_handoff(
            port=self.listeners[0].server_address[1],
            token=self.fixture.token(),message=msg,source_artifact=source,
            client_cert=self.fixture.client_cert,
            client_key=self.fixture.client_key,server_ca=self.fixture.ca_path)
        self.assertEqual(response["status"],"RECORDED_REVIEW_ONLY")
        worker= SyntheticEng05ReviewWorker(
           store=PostgresStore(os.environ["ABC_TEST_PG_ENG05_LOGIN_DSN"]),
           consumer_id=self.fixture.consumer)
        return worker,source,msg

    def test_eng05_actual_synthetic_worker_claim_ack_result_and_blocked_eng06_handoff(self):
        worker,source,msg=self._synthetic_job()
        result=worker.process_once()
        self.assertEqual(result["status"],"ACKED_REVIEW_ONLY")
        self.assertEqual(result["engine_version"],"synthetic-ontology.1")
        self.assertFalse(result["downstream_dispatched"])
        self.assertEqual(result["outbound_status"],"BLOCKED_PENDING_AUTHORITY")
        self.assertIsNone(worker.process_once())
        with psycopg.connect(self.admin,row_factory=dict_row) as con:
            job=con.execute("""SELECT status,attempts,source_sha256
                FROM abc.eng19_synthetic_jobs WHERE handoff_id=%s""",
                (msg["handoff_id"],)).fetchone()
            results=con.execute("""SELECT engine_id,engine_version,
               source_sha256,output_sha256,output_bytes
               FROM abc.eng19_synthetic_results WHERE handoff_id=%s""",
               (msg["handoff_id"],)).fetchall()
            out=con.execute("""SELECT from_engine,to_engine,artifact_sha256,status
                FROM abc.eng19_synthetic_outbox WHERE handoff_id=%s""",
                (msg["handoff_id"],)).fetchone()
        self.assertEqual(job["status"],"ACKED")
        self.assertEqual(job["attempts"],1)
        self.assertEqual(len(results),1)
        self.assertEqual(results[0]["source_sha256"],job["source_sha256"])
        self.assertEqual(out["status"],"BLOCKED_PENDING_AUTHORITY")
        self.assertEqual((out["from_engine"],out["to_engine"]),
                         ("ENG-05","ENG-06"))
        self.assertEqual(out["artifact_sha256"],results[0]["output_sha256"])

    def test_worker_claim_lease_fencing_reacquire_and_exactly_one_ack(self):
        worker,_,msg=self._synthetic_job()
        with ThreadPoolExecutor(max_workers=4) as pool:
            claims=list(pool.map(lambda _:worker.claim(),range(4)))
        self.assertEqual(len([c for c in claims if c is not None]),1)
        old=next(x for x in claims if x is not None)
        with psycopg.connect(self.admin,autocommit=True) as con:
            con.execute("""UPDATE abc.eng19_synthetic_jobs
               SET lease_until=clock_timestamp()-interval '1 second'
               WHERE handoff_id=%s""",(msg["handoff_id"],))
        new=worker.claim()
        self.assertIsNotNone(new)
        self.assertNotEqual(new["lease_token"],old["lease_token"])
        from abc_foundation.eng05_knowledge import SyntheticKnowledgeEngine
        from abc_foundation.eng02_consultation import SYNTHETIC_SERVICE
        output=SyntheticKnowledgeEngine().resolve(
            service_id=SYNTHETIC_SERVICE,fixture=None)
        with self.assertRaises(DomainError):
            worker.ack(old,output,next_handoff_id=str(uuid.uuid4()))
        ack=worker.ack(new,output,next_handoff_id=str(uuid.uuid4()))
        self.assertEqual(ack["status"],"ACKED_REVIEW_ONLY")

    def test_revoked_consent_and_stale_session_fence_worker_ack(self):
        from abc_foundation.eng05_knowledge import SyntheticKnowledgeEngine
        from abc_foundation.eng02_consultation import SYNTHETIC_SERVICE
        worker,_,msg=self._synthetic_job()
        claim=worker.claim()
        output=SyntheticKnowledgeEngine().resolve(
            service_id=SYNTHETIC_SERVICE,fixture=None)
        with psycopg.connect(self.admin,autocommit=True) as con:
            con.execute("""UPDATE abc.consent_evidence
              SET status='WITHDRAWN',revoked_at=clock_timestamp()
              WHERE consent_id=%s""",(self.consent,))
        with self.assertRaises(DomainError):
            worker.ack(claim,output,next_handoff_id=str(uuid.uuid4()))
        with psycopg.connect(self.admin) as con:
            count=con.execute("""SELECT count(*) FROM abc.eng19_synthetic_results
                WHERE handoff_id=%s""",(msg["handoff_id"],)).fetchone()[0]
        self.assertEqual(count,0)

    def test_worker_failure_retry_and_dlq_after_three_attempts(self):
        worker,_,msg=self._synthetic_job()
        for turn in range(3):
            claim=worker.claim()
            self.assertIsNotNone(claim)
            self.assertEqual(claim["attempt"],turn+1)
            state=worker.fail(claim,error_code="CI_INJECTED_FAILURE")
            self.assertEqual(state,"DLQ" if turn==2 else "QUEUED")
            if turn<2:
                with psycopg.connect(self.admin,autocommit=True) as con:
                    con.execute("""UPDATE abc.eng19_synthetic_jobs
                         SET available_at=clock_timestamp()-interval '1 second'
                         WHERE handoff_id=%s""",(msg["handoff_id"],))
        self.assertIsNone(worker.claim())

    def test_independent_worker_role_cannot_read_or_edit_job_tables(self):
        self._synthetic_job()
        for dsn in (self.app,os.environ["ABC_TEST_PG_ENG05_LOGIN_DSN"]):
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                with psycopg.connect(dsn) as con:
                    con.execute("SELECT * FROM abc.eng19_synthetic_jobs")

    def test_revoked_physical_eng05_login_binding_fences_ack(self):
        from abc_foundation.eng05_knowledge import SyntheticKnowledgeEngine
        from abc_foundation.eng02_consultation import SYNTHETIC_SERVICE
        worker,_,message=self._synthetic_job()
        claim=worker.claim()
        self.assertIsNotNone(claim)
        with psycopg.connect(self.admin,autocommit=True) as con:
            con.execute("""UPDATE abc.worker_login_bindings SET active=false
                WHERE login_name='abc_eng05_ci_login'
                  AND worker_role='abc_pipeline_worker'""")
        output=SyntheticKnowledgeEngine().resolve(
            service_id=SYNTHETIC_SERVICE,fixture=None)
        with self.assertRaises(DomainError):
            worker.ack(claim,output,next_handoff_id=str(uuid.uuid4()))
        with psycopg.connect(self.admin) as con:
            row=con.execute("""SELECT count(*) FROM abc.eng19_synthetic_outbox
                WHERE handoff_id=%s""",(message["handoff_id"],)).fetchone()
        self.assertEqual(row[0],0)

    def _eng06_review_job(self):
        from abc_foundation.eng06_review_worker import SyntheticEng06ReviewWorker
        worker05,_,message=self._synthetic_job()
        accepted=worker05.process_once()
        self.assertEqual(accepted["status"],"ACKED_REVIEW_ONLY")
        with psycopg.connect(self.admin,autocommit=True) as con:
            con.execute("""INSERT INTO abc.eng06_ci_worker_bindings
                 (login_name,consumer_id,tenant_id,active)
                 VALUES('abc_eng06_ci_login',%s,'tenant-test',true)
                 ON CONFLICT(login_name) DO UPDATE SET
                   consumer_id=EXCLUDED.consumer_id,
                   tenant_id=EXCLUDED.tenant_id,active=true""",
                   (self.fixture.consumer,))
            # This is deliberately ADMIN CI SEEDING ONLY, not a release of the
            # blocked outbox. No runtime role receives INSERT on this table.
            con.execute("""INSERT INTO abc.eng06_ci_jobs(
                  upstream_handoff,consumer_id,tenant_id,branch_id,
                  session_id,state_version)
                  VALUES(%s,%s,'tenant-test','branch-test',%s,2)""",
                  (message["handoff_id"],self.fixture.consumer,self.session))
        worker06=SyntheticEng06ReviewWorker(
            store=PostgresStore(os.environ["ABC_TEST_PG_ENG06_LOGIN_DSN"]),
            consumer_id=self.fixture.consumer)
        return worker06,message

    def test_eng06_isolated_claim_decide_blocked_ack_without_automatic_dispatch(self):
        worker,message=self._eng06_review_job()
        receipt=worker.process_once()
        self.assertEqual(receipt["status"],"ACKED_BLOCKED_REVIEW_ONLY")
        self.assertEqual(receipt["engine_id"],"ENG-06")
        self.assertFalse(receipt["downstream_dispatched"])
        self.assertFalse(receipt["customer_release_approved"])
        self.assertIsNone(worker.process_once())
        with psycopg.connect(self.admin,row_factory=dict_row) as con:
            j=con.execute("""SELECT status,attempts FROM abc.eng06_ci_jobs
                 WHERE upstream_handoff=%s""",(message["handoff_id"],)).fetchone()
            out=con.execute("""SELECT status FROM abc.eng19_synthetic_outbox
                 WHERE handoff_id=%s""",(message["handoff_id"],)).fetchone()
            r=con.execute("""SELECT status,engine_id,engine_version,
                    analysis_sha256,knowledge_sha256,output_sha256,output_bytes
                    FROM abc.eng06_ci_results WHERE upstream_handoff=%s""",
                    (message["handoff_id"],)).fetchone()
        self.assertEqual(j["status"],"ACKED")
        self.assertEqual(j["attempts"],1)
        self.assertEqual(out["status"],"BLOCKED_PENDING_AUTHORITY")
        self.assertEqual(r["status"],"BLOCKED_PROFESSIONAL_SOURCE")
        result=__import__("json").loads(r["output_bytes"])
        self.assertEqual(result["decision"]["candidates"],[])
        self.assertEqual(len(result["decision"]["excluded_options"]),2)
        self.assertFalse(result["downstream_dispatch_authorized"])

    def test_eng06_runs_in_distinct_os_process_without_releasing_look(self):
        import subprocess
        import sys
        import json
        worker,message=self._eng06_review_job()
        env={**os.environ,"ABC_ENG06_CI_CONSUMER":self.fixture.consumer}
        run=subprocess.run([sys.executable,"-m",
              "abc_foundation.eng06_review_worker"],
              env=env,capture_output=True,text=True,timeout=15)
        self.assertEqual(run.returncode,0,run.stderr)
        payload=json.loads(run.stdout)
        self.assertEqual(payload["status"],"ACKED_BLOCKED_REVIEW_ONLY")
        self.assertFalse(payload["downstream_dispatched"])
        self.assertFalse(payload["customer_release_approved"])
        self.assertIsNone(worker.process_once())
        with psycopg.connect(self.admin) as con:
            status=con.execute("""SELECT status FROM abc.eng19_synthetic_outbox
              WHERE handoff_id=%s""",(message["handoff_id"],)).fetchone()[0]
        self.assertEqual(status,"BLOCKED_PENDING_AUTHORITY")

    def test_eng06_parallel_claim_single_lease_then_stale_reclaim(self):
        worker,msg=self._eng06_review_job()
        with ThreadPoolExecutor(max_workers=4) as pool:
            claims=list(pool.map(lambda _:worker.claim(),range(4)))
        self.assertEqual(len([c for c in claims if c is not None]),1)
        old=next(c for c in claims if c is not None)
        with psycopg.connect(self.admin,autocommit=True) as con:
            con.execute("""UPDATE abc.eng06_ci_jobs
              SET lease_until=clock_timestamp()-interval '1 second'
              WHERE upstream_handoff=%s""",(msg["handoff_id"],))
        fresh=worker.claim()
        self.assertIsNotNone(fresh)
        self.assertNotEqual(fresh["lease_token"],old["lease_token"])
        with self.assertRaises(DomainError):
            worker.ack(old,worker.decide_blocked(old))
        ack=worker.ack(fresh,worker.decide_blocked(fresh))
        self.assertEqual(ack["status"],"ACKED_BLOCKED_REVIEW_ONLY")

    def test_eng06_revoked_consent_fences_ack(self):
        worker,msg=self._eng06_review_job()
        claim=worker.claim()
        self.assertIsNotNone(claim)
        output=worker.decide_blocked(claim)
        with psycopg.connect(self.admin,autocommit=True) as con:
            con.execute("""UPDATE abc.consent_evidence SET
              status='WITHDRAWN',revoked_at=clock_timestamp()
              WHERE consent_id=%s""",(self.consent,))
        with self.assertRaises(DomainError):
            worker.ack(claim,output)
        with psycopg.connect(self.admin) as con:
            count=con.execute("""SELECT count(*) FROM abc.eng06_ci_results
              WHERE upstream_handoff=%s""",(msg["handoff_id"],)).fetchone()[0]
        self.assertEqual(count,0)

    def test_eng06_physical_login_revocation_fences_ack(self):
        worker,msg=self._eng06_review_job()
        claim=worker.claim()
        self.assertIsNotNone(claim)
        with psycopg.connect(self.admin,autocommit=True) as con:
            con.execute("""UPDATE abc.eng06_ci_worker_bindings SET active=false
               WHERE login_name='abc_eng06_ci_login'""")
        with self.assertRaises(DomainError):
            worker.ack(claim,worker.decide_blocked(claim))
        with psycopg.connect(self.admin) as con:
            count=con.execute("""SELECT count(*) FROM abc.eng06_ci_results
              WHERE upstream_handoff=%s""",(msg["handoff_id"],)).fetchone()[0]
        self.assertEqual(count,0)

    def test_eng06_failed_worker_retries_then_dlq(self):
        worker,msg=self._eng06_review_job()
        for attempt in range(3):
            claim=worker.claim()
            self.assertEqual(claim["attempt"],attempt+1)
            status=worker.fail(claim,"CI_INJECTED_FAILURE")
            self.assertEqual(status,"DLQ" if attempt==2 else "QUEUED")
            if attempt<2:
                with psycopg.connect(self.admin,autocommit=True) as con:
                    con.execute("""UPDATE abc.eng06_ci_jobs
                       SET available_at=clock_timestamp()-interval '1 second'
                       WHERE upstream_handoff=%s""",(msg["handoff_id"],))
        self.assertIsNone(worker.claim())

    def test_eng06_direct_database_access_and_live_environment_denied(self):
        worker,msg=self._eng06_review_job()
        for dsn in (self.app,os.environ["ABC_TEST_PG_ENG06_LOGIN_DSN"]):
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                with psycopg.connect(dsn) as con:
                    con.execute("SELECT * FROM abc.eng06_ci_jobs")
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            with psycopg.connect(os.environ["ABC_TEST_PG_ENG06_LOGIN_DSN"]) as con:
                con.execute("""INSERT INTO abc.eng06_ci_jobs(upstream_handoff,
                  consumer_id,tenant_id,branch_id,session_id,state_version)
                  VALUES(%s,%s,'tenant-test','branch-test',%s,2)""",
                  (str(uuid.uuid4()),self.fixture.consumer,self.session))
        from unittest.mock import patch
        with patch.dict(os.environ,{"ABC_ENV":"STAGING_PRIVATE"}):
            with self.assertRaises(DomainError):
                worker.claim()

    def test_eng05_to_eng06_mtls_review_only_durable_receipt(self):
        """A real TLS1.3 ENG05→ENG06 receive, never ENG06 decision execution."""
        f=ManagedWorkloadMTLSTests("test_real_tls13_mutual_certificate_and_bound_jwt")
        f.consumer_override="ci-review-"+uuid.uuid4().hex[:20]
        f.source_engine_override="ENG-05"
        f.target_engine_override="ENG-06"
        f.setUp()
        self.addCleanup(f.doCleanups)
        gate_args={"source":"ENG-05","target":"ENG-06",
                   "artifact":"PROFESSIONAL_KNOWLEDGE_BUNDLE"}
        session_gate=AuthorityFixture(self.session,**gate_args)
        consent_gate=AuthorityFixture(self.session,"CONSENT",**gate_args)
        policy_gate=AuthorityFixture(self.session,**gate_args)
        store=PostgresStore(self.app)
        receiver=AuthenticatedReviewConsumer(
            identity_verifier=f.verifier,session_authority=session_gate,
            consent_authority=consent_gate,eng14_authority=policy_gate,
            replay_ledger=PostgresReplayLedger(store),
            inbox=PostgresReviewInbox(store),
            caller_engine="ENG-05",target_engine="ENG-06",
            consumer_id=f.consumer)
        server=start_local_review_consumer(
            consumer=receiver,certfile=f.server_cert,
            keyfile=f.server_key,ca_file=f.ca_path)
        self.addCleanup(server.server_close)
        runner=threading.Thread(target=server.serve_forever,daemon=True)
        runner.start()
        self.addCleanup(server.shutdown)
        msg={**self.message,
            "handoff_id":str(uuid.uuid4()),
            "from_engine":"ENG-05",
            "to_engine":"ENG-06",
            "artifact_kind":"PROFESSIONAL_KNOWLEDGE_BUNDLE",
            "artifact_sha256":"a"*64}
        def call(message):
            return send_local_review_handoff(
                port=server.server_address[1],token=f.token(),
                message=message,client_cert=f.client_cert,
                client_key=f.client_key,server_ca=f.ca_path)
        first=call(msg)
        self.assertEqual(first["status"],"RECORDED_REVIEW_ONLY")
        self.assertTrue(first["durable_review_receipt"])
        self.assertFalse(first["consumer_execution_authorized"])
        self.assertFalse(first["customer_release_approved"])
        self.assertEqual(call(msg)["status"],"ALREADY_RECORDED_REVIEW_ONLY")
        forged={**msg,"handoff_id":str(uuid.uuid4()),
                "from_engine":"ENG-04",
                "artifact_kind":"BEAUTY_ANALYSIS_REPORT"}
        self.assertEqual(call(forged)["status"],"REJECTED")
        policy_gate.allowed=False
        rejected={**msg,"handoff_id":str(uuid.uuid4())}
        self.assertEqual(call(rejected)["status"],"REJECTED")
        with psycopg.connect(self.admin) as con:
            row=con.execute("""SELECT from_engine,to_engine,artifact_kind
                FROM abc.eng19_review_inbox WHERE handoff_id=%s""",
                (msg["handoff_id"],)).fetchone()
        self.assertEqual(tuple(row),
            ("ENG-05","ENG-06","PROFESSIONAL_KNOWLEDGE_BUNDLE"))

    def test_source_artifact_tamper_is_rejected_before_job_creation(self):
        worker,source,message=self._synthetic_job()
        forged={**source,"service_scope":"REAL_CUSTOMER"}
        another={**message,"handoff_id":str(uuid.uuid4())}
        denied=send_local_review_handoff(
            port=self.listeners[0].server_address[1],token=self.fixture.token(),
            message=another,source_artifact=forged,
            client_cert=self.fixture.client_cert,
            client_key=self.fixture.client_key,server_ca=self.fixture.ca_path)
        self.assertEqual(denied["status"],"REJECTED")
        with psycopg.connect(self.admin) as con:
            self.assertEqual(con.execute(
                 "SELECT count(*) FROM abc.eng19_synthetic_jobs WHERE handoff_id=%s",
                 (another["handoff_id"],)).fetchone()[0],0)

    def test_final_crashed_lease_is_reconciled_to_dlq(self):
        worker,_,message=self._synthetic_job()
        for attempt in range(3):
            current=worker.claim()
            self.assertIsNotNone(current)
            with psycopg.connect(self.admin,autocommit=True) as con:
                con.execute("""UPDATE abc.eng19_synthetic_jobs
                     SET lease_until=clock_timestamp()-interval '1 second'
                     WHERE handoff_id=%s""",(message["handoff_id"],))
        self.assertIsNone(worker.claim())
        with psycopg.connect(self.admin) as con:
            row=con.execute("""SELECT status,attempts,failure_code
                FROM abc.eng19_synthetic_jobs WHERE handoff_id=%s""",
                (message["handoff_id"],)).fetchone()
        self.assertEqual(row,("DLQ",3,"CI_LEASE_EXHAUSTED"))

    def test_revoked_worker_binding_forbids_ack(self):
        from abc_foundation.eng05_knowledge import SyntheticKnowledgeEngine
        from abc_foundation.eng02_consultation import SYNTHETIC_SERVICE
        worker,_,message=self._synthetic_job()
        claim=worker.claim()
        with psycopg.connect(self.admin,autocommit=True) as con:
            con.execute("""UPDATE abc.eng03_worker_bindings SET active=false
              WHERE worker_role='abc_pipeline_worker'
                AND consumer_id=%s AND tenant_id='tenant-test'""",
                (self.fixture.consumer,))
        output=SyntheticKnowledgeEngine().resolve(
            service_id=SYNTHETIC_SERVICE,fixture=None)
        with self.assertRaises(DomainError):
            worker.ack(claim,output,next_handoff_id=str(uuid.uuid4()))
        with psycopg.connect(self.admin) as con:
            self.assertEqual(con.execute("""SELECT count(*)
                FROM abc.eng19_synthetic_outbox WHERE handoff_id=%s""",
                (message["handoff_id"],)).fetchone()[0],0)

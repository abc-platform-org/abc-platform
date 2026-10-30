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
    def __init__(self,session,gate="ALL"):
        self.session=session
        self.allowed=True
        self.gate=gate
    def verify(self,**claims):
        return (self.allowed and claims.get("tenant_id")=="tenant-test"
            and claims.get("branch_id")=="branch-test"
            and claims.get("session_id")==self.session
            and claims.get("state_version")==2
            and claims.get("from_engine")=="ENG-04"
            and claims.get("to_engine")=="ENG-05"
            and claims.get("artifact_kind")=="BEAUTY_ANALYSIS_REPORT"
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

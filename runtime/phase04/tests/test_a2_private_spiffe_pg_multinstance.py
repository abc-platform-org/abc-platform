"""A2 real disposable PG16 + separate TLS listeners/processes; synthetic ONLY.

Tests use actual physical CI database logins, a shared durable ENG14 JTI
ledger and live mTLS sockets; no provider PKI, external reviewer or cloud
staging approval is asserted. All records are synthetic.
"""
import copy
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import multiprocessing
import os
import threading
import unittest
import uuid
from datetime import datetime, timedelta, timezone

import psycopg
from cryptography.hazmat.primitives import serialization

from abc_foundation.isolated_engine_service import dispatch
from abc_foundation.private_engine_transport import (
    private_engine_server,send_private_engine_message)
from abc_foundation.private_pg_atomic_admission import PgAtomicPrivateAdmission
from abc_foundation.store import DomainError
from abc_foundation.service_mesh_identity import canonical_spiffe_id
from test_private_engine_mtls import ManagedWorkloadMTLSTests


def _process_tls_probe(args):
    # Executed by a new Python interpreter and a distinct SQL/TLS session.
    return send_private_engine_message(**args)


class PrivateAtomicPostgresMultiInstanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin=os.environ.get("ABC_TEST_PG_ADMIN_DSN")
        cls.eng05=os.environ.get("ABC_TEST_PG_ENG05_LOGIN_DSN")
        cls.eng04=os.environ.get("ABC_TEST_PG_ENG04_LOGIN_DSN")
        if (os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY"
            or not all((cls.admin,cls.eng05,cls.eng04))):
            raise unittest.SkipTest("requires disposable PostgreSQL 16 and physical CI logins")

    def setUp(self):
        self.fixture=ManagedWorkloadMTLSTests(
            "test_real_tls13_mutual_certificate_and_bound_jwt")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.tenant="a2privtenant"+uuid.uuid4().hex[:10]
        self.branch="a2privbranch"+uuid.uuid4().hex[:10]
        self.subject="a2-specialist-"+uuid.uuid4().hex[:10]
        self.human_issuer="https://oidc.a2-ci.example"
        self.session=str(uuid.uuid4())
        self.consent=str(uuid.uuid4())
        self.cert_sha=hashlib.sha256(self.fixture.client.public_bytes(
            serialization.Encoding.DER)).hexdigest()
        self._provision()
        self.message={**self.fixture.message,"session_id":self.session,
                      "request_id":str(uuid.uuid4())}
        self.listeners=[]
        self.port=self._start()

    def _provision(self):
        now=datetime.now(timezone.utc)
        with psycopg.connect(self.admin,autocommit=True) as con:
            con.execute("INSERT INTO abc.tenants(tenant_id) VALUES(%s)",(self.tenant,))
            con.execute("INSERT INTO abc.branches(tenant_id,branch_id) VALUES(%s,%s)",
                        (self.tenant,self.branch))
            con.execute("""INSERT INTO abc.memberships(
                       issuer,subject,tenant_id,branch_id,role,active,verified_qualification)
                    VALUES(%s,%s,%s,%s,'SPECIALIST',true,true)""",
                        (self.human_issuer,self.subject,self.tenant,self.branch))
            con.execute("""INSERT INTO abc.sessions(
                         session_id,tenant_id,branch_id,specialist_id,client_id,
                         service_id,state,state_version,created_at,updated_at,last_event_id)
                     VALUES(%s,%s,%s,%s,'a2-private-synthetic-client',
                       'synthetic:hair-color','CREATED',0,%s,%s,%s)""",
                        (uuid.UUID(self.session),self.tenant,self.branch,self.subject,
                         now,now,uuid.uuid4()))
            con.execute("""INSERT INTO abc.consent_evidence(
                        consent_id,tenant_id,branch_id,session_id,client_id,status,
                        purpose,evidence_digest,disclosure_version,retention_policy_id)
                   VALUES(%s,%s,%s,%s,'a2-private-synthetic-client',
                     'PENDING_VERIFICATION',%s,%s,'a2-ci-disclosure','a2-ci-retention')""",
                        (uuid.UUID(self.consent),self.tenant,self.branch,
                         uuid.UUID(self.session),
                         ["AI_STUDIO_SYNTHETIC_PREVIEW"],"f"*64))
            con.execute("""UPDATE abc.consent_evidence
                       SET status='ACTIVE',verified_at=%s,valid_until=%s
                       WHERE consent_id=%s""",
                        (now,now+timedelta(minutes=15),uuid.UUID(self.consent)))
            con.execute("""INSERT INTO abc.a2_private_synthetic_bindings(
                        tenant_id,branch_id,login_name,caller_engine,target_engine,
                        consumer_id,spiffe_id,certificate_sha256,
                        human_issuer,specialist_subject,active,valid_until)
                       VALUES(%s,%s,'abc_eng05_ci_login','ENG-04','ENG-05',
                          %s,%s,%s,%s,%s,true,%s)""",
                        (self.tenant,self.branch,self.fixture.consumer,
                         self.fixture.client_uri,self.cert_sha,
                         self.human_issuer,self.subject,now+timedelta(minutes=15)))

    def _admission(self,dsn=None,**overrides):
        args={
            "dsn":dsn or self.eng05,"tenant_id":self.tenant,
            "branch_id":self.branch,"human_issuer":self.human_issuer,
            "specialist_subject":self.subject,"caller_engine":"ENG-04",
            "target_engine":"ENG-05","consumer_id":self.fixture.consumer,
            "state_version":0}
        args.update(overrides)
        return PgAtomicPrivateAdmission(**args)

    def _start(self,dsn=None):
        server=private_engine_server(
            host="127.0.0.1",port=0,target_engine="ENG-05",
            caller_engine="ENG-04",consumer_id=self.fixture.consumer,
            certfile=self.fixture.server_cert,keyfile=self.fixture.server_key,
            ca_file=self.fixture.ca_path,verifier=self.fixture.verifier,
            atomic_admission=self._admission(dsn))
        self.listeners.append(server)
        thread=threading.Thread(target=server.serve_forever,
                                kwargs={"poll_interval":0.05},daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server.server_address[1]

    def _args(self,token=None,port=None,message=None):
        return dict(host="127.0.0.1",port=port or self.port,
             server_name="localhost",certfile=self.fixture.client_cert,
             keyfile=self.fixture.client_key,ca_file=self.fixture.ca_path,
             token=self.fixture.token() if token is None else token,
             message=self.message if message is None else message)

    def call(self,**kw):
        return send_private_engine_message(**self._args(**kw))

    def audit_count(self):
        with psycopg.connect(self.admin) as con:
            return con.execute("""SELECT count(*) FROM abc.a2_private_synthetic_audit
                     WHERE tenant_id=%s""",(self.tenant,)).fetchone()[0]

    def test_01_real_tls_and_pg_transaction_release_remains_blocked(self):
        v=self.call()
        self.assertEqual(v["engine_id"],"ENG-05")
        self.assertFalse(v["release_approved"])
        self.assertEqual(v["result"]["unknowns"],["SOURCE_UNVERIFIED"])
        self.assertEqual(self.audit_count(),1)

    def test_02_same_signed_jti_across_two_independent_receivers_one_winner(self):
        port2=self._start()
        t=self.fixture.token()
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(lambda port:self.call(token=t,port=port),
                               (self.port,port2)))
        self.assertEqual(sum(v.get("engine_id")=="ENG-05" for v in responses),1,responses)
        self.assertEqual(sum(v.get("error")=="engine_request_rejected" for v in responses),1)
        self.assertEqual(self.audit_count(),1)

    def test_03_eight_real_processes_multiple_tls_listeners_one_db_jti(self):
        ports=[self.port,self._start(),self._start()]
        token=self.fixture.token()
        requests=[self._args(token=token,port=ports[i%len(ports)]) for i in range(8)]
        with ProcessPoolExecutor(max_workers=8,
            mp_context=multiprocessing.get_context("spawn")) as pool:
            responses=list(pool.map(_process_tls_probe,requests))
        self.assertEqual(sum(r.get("engine_id")=="ENG-05" for r in responses),1,responses)
        self.assertEqual(sum(r.get("error")=="engine_request_rejected" for r in responses),7)
        self.assertEqual(self.audit_count(),1)

    def test_04_no_consent_denies_no_jti_or_audit_consumption(self):
        t=self.fixture.token()
        with psycopg.connect(self.admin,autocommit=True) as con:
            con.execute("""UPDATE abc.consent_evidence
                       SET status='WITHDRAWN',revoked_at=clock_timestamp()
                       WHERE consent_id=%s""",(uuid.UUID(self.consent),))
        self.assertEqual(self.call(token=t)["error"],"engine_request_rejected")
        self.assertEqual(self.audit_count(),0)

    def test_05_revoked_certificate_binding_denied(self):
        with psycopg.connect(self.admin,autocommit=True) as con:
            con.execute("""UPDATE abc.a2_private_synthetic_bindings
                  SET active=false,revoked_at=clock_timestamp()
                  WHERE tenant_id=%s""",(self.tenant,))
        self.assertEqual(self.call()["error"],"engine_request_rejected")
        self.assertEqual(self.audit_count(),0)

    def test_06_unqualified_or_revoked_human_denied(self):
        with psycopg.connect(self.admin,autocommit=True) as con:
            con.execute("""UPDATE abc.memberships SET verified_qualification=false
                       WHERE tenant_id=%s""",(self.tenant,))
        self.assertEqual(self.call()["error"],"engine_request_rejected")
        with psycopg.connect(self.admin,autocommit=True) as con:
            con.execute("""UPDATE abc.memberships
                         SET verified_qualification=true,active=false
                         WHERE tenant_id=%s""",(self.tenant,))
        self.assertEqual(self.call()["error"],"engine_request_rejected")
        self.assertEqual(self.audit_count(),0)

    def test_07_state_version_race_denied(self):
        with psycopg.connect(self.admin,autocommit=True) as con:
            con.execute("""UPDATE abc.sessions SET state_version=state_version+1
                     WHERE session_id=%s""",(uuid.UUID(self.session),))
        self.assertEqual(self.call()["error"],"engine_request_rejected")
        self.assertEqual(self.audit_count(),0)

    def test_08_wrong_physical_db_login_denied_even_with_valid_tls(self):
        bad_listener=self._start(self.eng04)
        self.assertEqual(self.call(port=bad_listener)["error"],"engine_request_rejected")
        self.assertEqual(self.audit_count(),0)

    def test_09_wrong_tenant_binding_denied(self):
        bad=self._admission(tenant_id="tenant-that-does-not-exist")
        ident=self.fixture.verifier.verify(
            self.fixture.token(),self.fixture.client.public_bytes(serialization.Encoding.DER),
            expected_engine="ENG-04",expected_consumer=self.fixture.consumer)
        with self.assertRaises(DomainError):
            bad.admit_and_execute(ident,self.message,
                                  lambda:dispatch(self.message,"ENG-05"))
        self.assertEqual(self.audit_count(),0)

    def test_10_spoofed_jwt_consumer_engine_and_cert_are_denied(self):
        for forged in (
            self.fixture.token(engine="ENG-06"),
            self.fixture.token(consumer="another-consumer"),
            self.fixture.token(binding="a" * 43),
        ):
            with self.subTest(forged=forged[-8:]):
                self.assertEqual(self.call(token=forged)["error"],
                                 "engine_request_rejected")
        self.assertEqual(self.audit_count(),0)

    def test_11_bare_application_role_has_no_private_admission_privilege(self):
        registry=Path(__file__).resolve().parents[3] / "governance" / "abc_w1_workload_trust_boundaries.v0.review.json"
        inventory=json.loads(registry.read_text())
        self.assertEqual(len(inventory["workloads"]),7)
        for item in inventory["workloads"]:
            with self.subTest(engine=item["engine_id"]):
                self.assertEqual(item["proposed_spiffe_id"],
                                 canonical_spiffe_id(item["engine_id"]))
        sig=("abc.a2_private_atomic_admit(text,text,uuid,integer,"
             "text,text,text,text,text,text,text,text,text,uuid,"
             "timestamptz,uuid,text)")
        with psycopg.connect(self.admin) as con:
            self.assertFalse(con.execute(
                "SELECT has_function_privilege('abc_app',%s,'EXECUTE')",
                (sig,)).fetchone()[0])
            for name in ("a2_private_synthetic_bindings",
                         "a2_private_synthetic_audit"):
                state=con.execute("""SELECT relrowsecurity,relforcerowsecurity
                             FROM pg_class WHERE oid=%s::regclass""",
                            ("abc."+name,)).fetchone()
                self.assertEqual(state,(True,True))
                self.assertFalse(con.execute(
                    "SELECT has_table_privilege('abc_app',%s,'SELECT')",
                    ("abc."+name,)).fetchone()[0])

    def test_12_db_connection_failure_is_closed(self):
        bad_dsn=self.eng05.replace(":5432/",":59999/")+"?connect_timeout=1"
        port=self._start(bad_dsn)
        self.assertEqual(self.call(port=port)["error"],"engine_request_rejected")
        self.assertEqual(self.audit_count(),0)

    def test_13_atomic_rollback_on_bounded_execution_error(self):
        token=self.fixture.token()
        ident=self.fixture.verifier.verify(
            token,self.fixture.client.public_bytes(serialization.Encoding.DER),
            expected_engine="ENG-04",expected_consumer=self.fixture.consumer)
        def failed_execution():
            raise DomainError(500,"test_worker_crash")
        with self.assertRaises(DomainError):
            self._admission().admit_and_execute(ident,self.message,failed_execution)
        self.assertEqual(self.audit_count(),0)
        # The same token remains unclaimed because the DB transaction rolled back.
        valid=self._admission().admit_and_execute(
            ident,self.message,lambda:dispatch(self.message,"ENG-05"))
        self.assertEqual(valid["engine_id"],"ENG-05")
        self.assertEqual(self.audit_count(),1)

    def test_14_revocation_race_waits_for_atomic_execution(self):
        token=self.fixture.token()
        ident=self.fixture.verifier.verify(
            token,self.fixture.client.public_bytes(serialization.Encoding.DER),
            expected_engine="ENG-04",expected_consumer=self.fixture.consumer)
        entered=threading.Event()
        release=threading.Event()
        def work():
            entered.set()
            if not release.wait(timeout=7):
                raise DomainError(503,"timeout")
            return dispatch(self.message,"ENG-05")
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(self._admission().admit_and_execute,ident,self.message,work)
            try:
                self.assertTrue(entered.wait(timeout=6))
                with psycopg.connect(self.admin) as con:
                    con.execute("SET LOCAL lock_timeout='400ms'")
                    with self.assertRaises(psycopg.errors.LockNotAvailable):
                        con.execute("""UPDATE abc.consent_evidence
                                  SET status='WITHDRAWN',revoked_at=clock_timestamp()
                                  WHERE consent_id=%s""",(uuid.UUID(self.consent),))
            finally:
                release.set()
            self.assertEqual(future.result(timeout=6)["engine_id"],"ENG-05")
        with psycopg.connect(self.admin,autocommit=True) as con:
            con.execute("""UPDATE abc.consent_evidence
                      SET status='WITHDRAWN',revoked_at=clock_timestamp()
                      WHERE consent_id=%s""",(uuid.UUID(self.consent),))
        self.assertEqual(self.call()["error"],"engine_request_rejected")
        self.assertEqual(self.audit_count(),1)

    def test_15_managed_required_mode_cannot_use_synthetic_broker(self):
        with psycopg.connect(self.admin,autocommit=True) as con:
            con.execute("""INSERT INTO abc.eng14_tenant_workload_mode(
                          tenant_id,managed_required,activated_at,activated_by)
                      VALUES(%s,true,clock_timestamp(),'ci-operator')""",(self.tenant,))
        self.assertEqual(self.call()["error"],"engine_request_rejected")
        self.assertEqual(self.audit_count(),0)

    def test_16_frozen_v1_message_cannot_insert_unsafe_release_or_alter_session(self):
        for message in (
            {**self.message,"release_approved":True},
            {**self.message,"session_id":str(uuid.uuid4())},
            {**self.message,"consumer_id":"other-signed-consumer"}
        ):
            with self.subTest(keys=list(message)):
                self.assertEqual(self.call(message=message)["error"],
                                 "engine_request_rejected")
        self.assertEqual(self.audit_count(),0)


def load_tests(loader, _unused, _pattern):
    # Imported TLS fixture is reusable but must not inflate mandatory counts.
    return loader.loadTestsFromTestCase(PrivateAtomicPostgresMultiInstanceTests)


if __name__=="__main__":
    unittest.main()

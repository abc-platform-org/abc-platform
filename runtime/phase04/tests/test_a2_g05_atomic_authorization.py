"""A2-G05 real PostgreSQL16 + TLS1.3 mTLS + ENG14 consent/replay acceptance.

Each case creates an isolated tenant, qualified synthetic specialist, session,
and initially PENDING consent, activated through the existing state machine.
No real customer information, externally issued identity, or engine release.
"""
import copy
import hashlib
import os
import socket
import ssl
import threading
import time
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import psycopg
from cryptography.hazmat.primitives import serialization

from abc_foundation.eng01_v2_authenticated_ingress import ScopedV2Ingress
from abc_foundation.g05_postgres_admission import G05PostgresAdmission
from abc_foundation.pg_store import PostgresStore
from abc_foundation.private_engine_transport import _read_frame, _write_frame
from abc_foundation.private_v2_engine_transport import create_local_v2_mtls_server
from abc_foundation.store import DomainError
from test_engine_v2_contracts import request
from test_private_engine_mtls import ManagedWorkloadMTLSTests

ISSUER = "https://oidc.g05-ci.example"
PURPOSE = "AI_STUDIO_SYNTHETIC_PREVIEW"


class G05TransactionalWorkloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = os.environ.get("ABC_TEST_PG_ADMIN_DSN")
        cls.app = os.environ.get("ABC_TEST_PG_DSN")
        if (os.environ.get("ABC_ENV") != "LOCAL_INTEGRATION_ONLY"
            or not cls.admin or not cls.app):
            raise unittest.SkipTest("disposable local PostgreSQL 16 required")

    def setUp(self):
        self.tenant = "g05tenant" + uuid.uuid4().hex[:11]
        self.branch = "g05branch" + uuid.uuid4().hex[:10]
        self.specialist = "g05-specialist-" + uuid.uuid4().hex[:9]
        self.session = str(uuid.uuid4())
        self.consent = str(uuid.uuid4())
        self.fixture = ManagedWorkloadMTLSTests(
            "test_real_tls13_mutual_certificate_and_bound_jwt"
        )
        self.fixture.setUp()
        self.cert_sha256 = hashlib.sha256(self.fixture.client.public_bytes(
            serialization.Encoding.DER)).hexdigest()
        self.addCleanup(self.fixture.doCleanups)
        self._provision()
        self.listeners = []
        self._start()
        self.message = request("ENG-05")
        self.message.update({
            "request_id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()),
            "tenant_id": self.tenant, "branch_id": self.branch,
            "session_id": self.session, "state_version": 0,
            "consumer_id": self.fixture.consumer,
        })
        self.message["payload"]["recommendation_ref"].update({
            "tenant_id": self.tenant, "branch_id": self.branch,
            "session_id": self.session,
        })

    def _provision(self):
        now = datetime.now(timezone.utc)
        with psycopg.connect(self.admin, autocommit=True) as con:
            con.execute("INSERT INTO abc.tenants(tenant_id) VALUES(%s)",
                        (self.tenant,))
            con.execute("INSERT INTO abc.branches(tenant_id,branch_id) VALUES(%s,%s)",
                        (self.tenant, self.branch))
            con.execute("""INSERT INTO abc.memberships(
                  issuer,subject,tenant_id,branch_id,role,active,verified_qualification
                ) VALUES(%s,%s,%s,%s,'SPECIALIST',true,true)""",
                        (ISSUER, self.specialist, self.tenant, self.branch))
            con.execute("""INSERT INTO abc.sessions(
                  session_id,tenant_id,branch_id,specialist_id,client_id,
                  service_id,state,state_version,created_at,updated_at,last_event_id
                ) VALUES(%s,%s,%s,%s,'g05-synthetic-client',
                  'synthetic:hair-color','CREATED',0,%s,%s,%s)""",
                        (uuid.UUID(self.session), self.tenant, self.branch,
                         self.specialist, now, now, uuid.uuid4()))
            # The actual database trigger disallows inserting ACTIVE directly.
            con.execute("""INSERT INTO abc.consent_evidence(
                  consent_id,tenant_id,branch_id,session_id,client_id,status,
                  purpose,evidence_digest,disclosure_version,retention_policy_id
                ) VALUES(%s,%s,%s,%s,'g05-synthetic-client',
                  'PENDING_VERIFICATION',%s,%s,'g05-ci-disclosure-1',
                  'g05-ci-retention')""",
                        (uuid.UUID(self.consent), self.tenant, self.branch,
                         uuid.UUID(self.session), [PURPOSE], "a" * 64))
            con.execute("""UPDATE abc.consent_evidence
                  SET status='ACTIVE',verified_at=%s,valid_until=%s
                  WHERE consent_id=%s""",
                        (now, now + timedelta(minutes=15), uuid.UUID(self.consent)))
            con.execute("""INSERT INTO abc.g05_synthetic_cert_grants(
                  tenant_id,caller_engine,target_engine,consumer_id,
                  client_cert_sha256,active,valid_until
                ) VALUES (%s,'ENG-04','ENG-05',%s,%s,true,%s)""",
                        (self.tenant, self.fixture.consumer, self.cert_sha256,
                         now + timedelta(minutes=15)))

    def _ingress(self):
        admission = G05PostgresAdmission(
            store=PostgresStore(self.app),
            human_issuer=ISSUER, specialist_subject=self.specialist,
        )
        return ScopedV2Ingress(
            identity_verifier=self.fixture.verifier,
            scope_authority=None, replay_ledger=None,
            caller_engine="ENG-04",
            consumer_id=self.fixture.consumer,
            transactional_admission=admission,
        )

    def _start(self):
        service = create_local_v2_mtls_server(
            target_engine="ENG-05", port=0,
            certfile=self.fixture.server_cert, keyfile=self.fixture.server_key,
            ca_file=self.fixture.ca_path, ingress=self._ingress(),
        )
        self.listeners.append(service)
        thread = threading.Thread(
            target=service.serve_forever,
            kwargs={"poll_interval": 0.05}, daemon=True,
        )
        thread.start()
        # LIFO: shutdown the service before closing its listening socket.
        self.addCleanup(service.server_close)
        self.addCleanup(service.shutdown)
        return service.server_address[1]

    def call(self, *, message=None, token=None, port=None, certificate=True):
        ctx = ssl.create_default_context(cafile=self.fixture.ca_path)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        if certificate:
            ctx.load_cert_chain(self.fixture.client_cert, self.fixture.client_key)
        address = ("127.0.0.1", port or self.listeners[0].server_address[1])
        with socket.create_connection(address, timeout=4) as tcp:
            with ctx.wrap_socket(tcp, server_hostname="localhost") as secure:
                secure.settimeout(4)
                _write_frame(secure, {
                    "token": self.fixture.token() if token is None else token,
                    "message": self.message if message is None else message,
                })
                return _read_frame(secure)

    def test_full_positive_mtls_consent_and_eng14_output_remains_blocked(self):
        result = self.call()
        self.assertEqual(result["engine_id"], "ENG-05")
        self.assertEqual(result["result"]["status"], "BLOCKED")
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["release_approved"])
        self.assertEqual(result["result"]["eligible_looks"], [])

    def test_atomic_replay_across_two_independent_mtls_listeners(self):
        second = self._start()
        signed = self.fixture.token()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(self.call, token=signed, port=port)
                for port in (self.listeners[0].server_address[1], second)
            ]
            results = [f.result(timeout=10) for f in futures]
        self.assertEqual(
            sorted(x.get("release_approved") for x in results),
            [False, False],
        )
        self.assertEqual(sum("engine_id" in x for x in results), 1, results)
        self.assertEqual(
            sum(x.get("error") == "v2_authenticated_request_rejected"
                for x in results), 1, results,
        )
        self.assertEqual(self.call(port=second)["engine_id"], "ENG-05")

    def test_tenant_branch_and_session_mismatch_denied_at_db(self):
        for field, value in (
            ("tenant_id", "other-g05-tenant"),
            ("branch_id", "other-g05-branch"),
            ("session_id", str(uuid.uuid4())),
            ("state_version", 5),
        ):
            with self.subTest(field=field):
                message = copy.deepcopy(self.message)
                message[field] = value
                if field in ("tenant_id", "branch_id", "session_id"):
                    message["payload"]["recommendation_ref"][field] = value
                self.assertEqual(
                    self.call(message=message)["error"],
                    "v2_authenticated_request_rejected",
                )

    def test_withdrawal_denies_immediately_with_new_jti(self):
        with psycopg.connect(self.admin, autocommit=True) as con:
            con.execute("""UPDATE abc.consent_evidence SET
                  status='WITHDRAWN',revoked_at=clock_timestamp()
                  WHERE consent_id=%s""", (uuid.UUID(self.consent),))
        self.assertEqual(
            self.call()["error"], "v2_authenticated_request_rejected"
        )

    def test_revoked_specialist_membership_and_qualification_denied(self):
        with psycopg.connect(self.admin, autocommit=True) as con:
            con.execute("""UPDATE abc.memberships SET active=false
                  WHERE issuer=%s AND subject=%s AND tenant_id=%s""",
                        (ISSUER, self.specialist, self.tenant))
        self.assertEqual(
            self.call()["error"], "v2_authenticated_request_rejected"
        )
        with psycopg.connect(self.admin, autocommit=True) as con:
            con.execute("""UPDATE abc.memberships
                  SET active=true,verified_qualification=false
                  WHERE issuer=%s AND subject=%s AND tenant_id=%s""",
                        (ISSUER, self.specialist, self.tenant))
        self.assertEqual(
            self.call()["error"], "v2_authenticated_request_rejected"
        )

    def test_certificate_grant_can_be_revoked_without_changing_jwt_or_ca(self):
        # Same valid cryptographic identity is denied by the operator's
        # database certificate authorization policy.
        with psycopg.connect(self.admin, autocommit=True) as con:
            con.execute("""UPDATE abc.g05_synthetic_cert_grants
                  SET active=false,revoked_at=clock_timestamp()
                  WHERE tenant_id=%s AND client_cert_sha256=%s""",
                        (self.tenant, self.cert_sha256))
        self.assertEqual(
            self.call()["error"], "v2_authenticated_request_rejected"
        )

    def test_correct_cert_wrong_consumer_grant_denied(self):
        with psycopg.connect(self.admin, autocommit=True) as con:
            con.execute("""UPDATE abc.g05_synthetic_cert_grants
                  SET consumer_id='different-ci-consumer'
                  WHERE tenant_id=%s AND client_cert_sha256=%s""",
                        (self.tenant, self.cert_sha256))
        self.assertEqual(
            self.call()["error"], "v2_authenticated_request_rejected"
        )

    def test_pending_consent_is_not_equivalent_to_active(self):
        with psycopg.connect(self.admin, autocommit=True) as con:
            con.execute("""UPDATE abc.consent_evidence SET
                  status='WITHDRAWN',revoked_at=clock_timestamp()
                  WHERE consent_id=%s""", (uuid.UUID(self.consent),))
            con.execute("""INSERT INTO abc.consent_evidence(
                consent_id,tenant_id,branch_id,session_id,client_id,status,
                purpose,evidence_digest,disclosure_version,retention_policy_id
                ) VALUES (%s,%s,%s,%s,'g05-synthetic-client',
                 'PENDING_VERIFICATION',%s,%s,'g05-ci-disclosure-1',
                 'g05-ci-retention')""",
                (uuid.uuid4(), self.tenant, self.branch,
                 uuid.UUID(self.session), [PURPOSE], "b"*64))
        self.assertEqual(
            self.call()["error"], "v2_authenticated_request_rejected"
        )

    def test_consent_for_different_purpose_cannot_authorize_ai_preview(self):
        with psycopg.connect(self.admin, autocommit=True) as con:
            con.execute("""UPDATE abc.consent_evidence SET
                  status='WITHDRAWN',revoked_at=clock_timestamp()
                  WHERE consent_id=%s""", (uuid.UUID(self.consent),))
            other = uuid.uuid4()
            con.execute("""INSERT INTO abc.consent_evidence(
                consent_id,tenant_id,branch_id,session_id,client_id,status,
                purpose,evidence_digest,disclosure_version,retention_policy_id
                ) VALUES (%s,%s,%s,%s,'g05-synthetic-client',
                 'PENDING_VERIFICATION',%s,%s,'g05-ci-disclosure-1',
                 'g05-ci-retention')""",
                (other, self.tenant, self.branch, uuid.UUID(self.session),
                 ["UNRELATED_TEST_PURPOSE"], "c" * 64))
            con.execute("""UPDATE abc.consent_evidence
                  SET status='ACTIVE',verified_at=clock_timestamp(),
                      valid_until=clock_timestamp()+interval '15 minutes'
                  WHERE consent_id=%s""", (other,))
        self.assertEqual(
            self.call()["error"], "v2_authenticated_request_rejected"
        )

    def test_managed_tenant_requires_physical_clientcert_db_login(self):
        with psycopg.connect(self.admin, autocommit=True) as con:
            con.execute("""INSERT INTO abc.eng14_tenant_workload_mode(
                  tenant_id,managed_required,activated_at,activated_by
                ) VALUES (%s,true,clock_timestamp(),'G05_TEST_ONLY')""",
                        (self.tenant,))
        self.assertEqual(
            self.call()["error"], "v2_authenticated_request_rejected"
        )

    def test_certificate_token_identity_and_target_are_mandatory(self):
        with self.assertRaises((ssl.SSLError, OSError, ConnectionError)):
            self.call(certificate=False)
        for signed in (
            self.fixture.token(binding="wrong-certificate-sha256"),
            self.fixture.token(engine="ENG-06"),
            self.fixture.token(consumer="wrong-consumer"),
            "",
        ):
            with self.subTest(bad_token=signed[-9:]):
                self.assertEqual(
                    self.call(token=signed)["error"],
                    "v2_authenticated_request_rejected",
                )

    def test_race_revocation_waits_until_protected_dispatch_commits(self):
        # Real PG FOR SHARE lock protects read + replay + bounded execution.
        admission = G05PostgresAdmission(
            store=PostgresStore(self.app), human_issuer=ISSUER,
            specialist_subject=self.specialist,
        )
        peer = self.fixture.client.public_bytes(serialization.Encoding.DER)
        identity = self.fixture.verifier.verify(
            self.fixture.token(), peer,
            expected_engine="ENG-04", expected_consumer=self.fixture.consumer,
        )
        entered = threading.Event()
        finish = threading.Event()

        def bounded_execute():
            entered.set()
            if not finish.wait(timeout=8):
                raise RuntimeError("test lock barrier timed out")
            return {
                "engine_id": "ENG-05", "request_id": self.message["request_id"],
                "session_id": self.session,
                "consumer_id": self.fixture.consumer,
                "release_approved": False, "execution_authorized": False,
            }

        def gate():
            return admission.admit_and_execute(
                message=self.message, identity=identity, caller_engine="ENG-04",
                execute_fn=bounded_execute,
            )

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(gate)
            try:
                self.assertTrue(entered.wait(timeout=7),
                                "admission did not reach the protected section")
                # A concurrent withdrawal cannot commit before protected work.
                with psycopg.connect(self.admin) as con:
                    con.execute("SET LOCAL lock_timeout='350ms'")
                    with self.assertRaises(psycopg.errors.LockNotAvailable):
                        con.execute("""UPDATE abc.consent_evidence
                             SET status='WITHDRAWN',revoked_at=clock_timestamp()
                             WHERE consent_id=%s""", (uuid.UUID(self.consent),))
            finally:
                finish.set()
            self.assertEqual(future.result(timeout=7)["engine_id"], "ENG-05")

        with psycopg.connect(self.admin, autocommit=True) as con:
            con.execute("""UPDATE abc.consent_evidence SET
                  status='WITHDRAWN',revoked_at=clock_timestamp()
                  WHERE consent_id=%s""", (uuid.UUID(self.consent),))
        self.assertEqual(
            self.call()["error"], "v2_authenticated_request_rejected"
        )

    def test_runtime_worker_cannot_call_privileged_g05_broker(self):
        signature = (
            "abc.eng14_g05_cert_bound_admit_and_claim(text,text,uuid,integer,"
            "text,text,text,text,text,text,text,uuid,timestamptz,text)"
        )
        old_signature = (
            "abc.eng14_g05_admit_and_claim(text,text,uuid,integer,text,text,"
            "text,text,text,text,text,uuid,timestamptz)"
        )
        with psycopg.connect(self.admin) as con:
            self.assertEqual(con.execute(
                """SELECT has_function_privilege(
                     'abc_eng03_worker',%s,'EXECUTE')""",
                (signature,),
            ).fetchone(), (False,))
            self.assertEqual(con.execute(
                """SELECT has_function_privilege(
                     'abc_app',%s,'EXECUTE')""",
                (signature,),
            ).fetchone(), (True,))
            # The previous unbound entrypoint MUST be revoked even from abc_app.
            self.assertEqual(con.execute(
                """SELECT has_function_privilege('abc_app',%s,'EXECUTE')""",
                (old_signature,),
            ).fetchone(), (False,))

    def test_missing_transactional_gate_never_claims_g05(self):
        with self.assertRaisesRegex(
            ValueError, "external_identity_scope_replay_authority_required"
        ):
            ScopedV2Ingress(
                identity_verifier=self.fixture.verifier,
                scope_authority=None, replay_ledger=None,
                caller_engine="ENG-04",
                consumer_id=self.fixture.consumer,
            )


if __name__ == "__main__":
    unittest.main()

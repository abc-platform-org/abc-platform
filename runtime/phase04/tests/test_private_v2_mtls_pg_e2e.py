"""Actual loopback TLS1.3 v2 endpoint with real PG single-use replay.

CI-only disposable certs/RS256 JWTs. Session policy authority is explicitly
a test fixture, NOT real ENG01 policy, specialist approval or real deployment.
"""
import os
import socket
import ssl
import threading
import unittest
import uuid
from unittest.mock import patch

import psycopg

from abc_foundation.distributed_replay import PostgresReplayLedger
from abc_foundation.eng01_v2_authenticated_ingress import ScopedV2Ingress
from abc_foundation.pg_store import PostgresStore
from abc_foundation.private_engine_transport import _read_frame,_write_frame
from abc_foundation.private_v2_engine_transport import create_local_v2_mtls_server
from abc_foundation.store import DomainError
from test_engine_v2_contracts import request
from test_private_engine_mtls import ManagedWorkloadMTLSTests


class TestOnlySessionScope:
    def verify(self,**claims):
        return (claims["tenant_id"]=="tenant-test" and
            claims["branch_id"]=="branch-test" and
            claims["state_version"]==2 and
            claims["caller_engine"]=="ENG-04" and
            claims["target_engine"]=="ENG-05" and
            claims["consumer_id"]=="ci-consumer-01")


class ActualV2NetworkMTLSTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=os.environ.get("ABC_TEST_PG_DSN")
        cls.admin=os.environ.get("ABC_TEST_PG_ADMIN_DSN")
        if not cls.app or not cls.admin or os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
            raise unittest.SkipTest("requires isolated CI PostgreSQL16")
        with psycopg.connect(cls.admin,autocommit=True) as con:
            con.execute("INSERT INTO abc.tenants(tenant_id) VALUES('tenant-test') ON CONFLICT DO NOTHING")

    def setUp(self):
        self.fixture=ManagedWorkloadMTLSTests("test_real_tls13_mutual_certificate_and_bound_jwt")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.ledger=PostgresReplayLedger(PostgresStore(self.app))
        self.ingress=ScopedV2Ingress(
            identity_verifier=self.fixture.verifier,
            scope_authority=TestOnlySessionScope(),
            replay_ledger=self.ledger,
            caller_engine="ENG-04",consumer_id=self.fixture.consumer)
        self.listeners=[];self.threads=[]
        self._start()
        self.message=request("ENG-05")
        self.message["consumer_id"]=self.fixture.consumer

    def _start(self):
        listener=create_local_v2_mtls_server(
            target_engine="ENG-05",port=0,certfile=self.fixture.server_cert,
            keyfile=self.fixture.server_key,ca_file=self.fixture.ca_path,
            ingress=self.ingress)
        self.listeners.append(listener)
        thread=threading.Thread(target=listener.serve_forever,daemon=True)
        thread.start()
        self.threads.append(thread)
        self.addCleanup(listener.server_close)
        self.addCleanup(listener.shutdown)
        return listener.server_address[1]

    def call(self,token=None,message=None,port=None,client_cert=True):
        ctx=ssl.create_default_context(ssl.Purpose.SERVER_AUTH,
             cafile=self.fixture.ca_path)
        if client_cert:
            ctx.load_cert_chain(certfile=self.fixture.client_cert,
                                keyfile=self.fixture.client_key)
        target_port=port if port is not None else self.listeners[0].server_address[1]
        with socket.create_connection(("127.0.0.1",target_port),timeout=4) as sock:
            with ctx.wrap_socket(sock,server_hostname="localhost") as secured:
                secured.settimeout(4)
                _write_frame(secured,{"token":token if token is not None else
                       self.fixture.token(),"message":message if message is not None else
                       self.message})
                return _read_frame(secured)

    def test_real_tls_certificate_and_signed_jwt_then_v2_contract(self):
        r=self.call()
        self.assertEqual(r["engine_id"],"ENG-05")
        self.assertEqual(r["contract_version"],"abc.internal.engine.v2.draft")
        self.assertEqual(r["result"]["status"],"BLOCKED")
        self.assertFalse(r["execution_authorized"])
        self.assertFalse(r["release_approved"])

    def test_duplicate_jti_across_two_separate_servers_is_denied(self):
        second=self._start()
        signed=self.fixture.token()
        accepted=self.call(token=signed)
        self.assertEqual(accepted["engine_id"],"ENG-05")
        replay=self.call(token=signed,port=second)
        self.assertEqual(replay["error"],"v2_authenticated_request_rejected")
        self.assertFalse(replay["release_approved"])
        self.assertEqual(self.call(port=second)["engine_id"],"ENG-05")

    def test_false_peer_bad_jwt_cross_tenant_and_version_rejected(self):
        signed=self.fixture.token(binding="forged-thumbprint")
        self.assertEqual(self.call(token=signed)["error"],
                         "v2_authenticated_request_rejected")
        for patch_msg in (
           {"tenant_id":"other-tenant"},
           {"contract_version":"abc.internal.engine.synthetic.v1"},
           {"consumer_id":"unbound-consumer"},
           {"engine_id":"ENG-06"}
        ):
            with self.subTest(patch_msg=patch_msg):
                req={**self.message,**patch_msg}
                self.assertEqual(self.call(message=req)["error"],
                              "v2_authenticated_request_rejected")
        with self.assertRaises((ssl.SSLError,OSError,ConnectionError)):
            self.call(client_cert=False)

    def test_private_v2_listener_refuses_staging_or_public_override(self):
        with patch.dict(os.environ,{"ABC_ENV":"STAGING_PRIVATE"}):
            with self.assertRaisesRegex(ValueError,"unapproved_v2_mtls_engine_environment"):
                self._start()


if __name__=="__main__":
    unittest.main()

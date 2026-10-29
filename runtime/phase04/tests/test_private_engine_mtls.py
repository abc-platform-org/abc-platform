"""Real loopback TLS1.3 mutual certificate + asymmetric service JWT tests.

All certificates and signed tokens are generated per test in disposable memory;
no external CA, managed issuer or production secrets are provisioned.
"""
import base64
import hashlib
import tempfile
import threading
import unittest
import uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path
from types import SimpleNamespace
import jwt
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID
from abc_foundation.private_engine_transport import (
     private_engine_server,send_private_engine_message)
from abc_foundation.service_mesh_identity import BoundEngineIdentity
from abc_foundation.isolated_engine_service import VERSION
from abc_foundation.private_engine_service_server import configure_private_engine_service
from abc_foundation.managed_engine_client import ManagedMTLSEngineClient
from abc_foundation.store import DomainError


def _write(p,blob):
    Path(p).write_bytes(blob)
    return str(p)


class FakeJWKS:
    def __init__(self,key):self.key=key
    def get_signing_key_from_jwt(self,token):
        return SimpleNamespace(key=self.key.public_key())


class ManagedWorkloadMTLSTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        now=datetime.now(timezone.utc)
        self.now=now
        def key():
            return rsa.generate_private_key(public_exponent=65537,key_size=2048)
        self.ca=key()
        self.signer=key()
        name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,"ABC CI CA")])
        self.ca_cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(self.ca.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now-timedelta(minutes=5))
            .not_valid_after(now+timedelta(days=1))
            .add_extension(x509.BasicConstraints(ca=True,path_length=None),critical=True)
            .sign(self.ca,hashes.SHA256()))
        self.ca_path=_write(self.root/"ca.pem",
            self.ca_cert.public_bytes(serialization.Encoding.PEM))
        self.consumer="ci-consumer-01"
        self.client_uri="spiffe://abc.internal/eng04/"+self.consumer
        def issue(common,san,is_server):
            private=key()
            subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,common)])
            certificate=(x509.CertificateBuilder().subject_name(subject)
                 .issuer_name(self.ca_cert.subject).public_key(private.public_key())
                 .serial_number(x509.random_serial_number())
                 .not_valid_before(now-timedelta(minutes=5))
                 .not_valid_after(now+timedelta(minutes=30))
                 .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
                 .add_extension(x509.SubjectAlternativeName([san]),critical=False)
                 .add_extension(x509.ExtendedKeyUsage([
                    ExtendedKeyUsageOID.SERVER_AUTH if is_server else ExtendedKeyUsageOID.CLIENT_AUTH
                 ]),critical=False)
                 .sign(self.ca,hashes.SHA256()))
            cert_path=_write(self.root/(common+"-cert.pem"),
                              certificate.public_bytes(serialization.Encoding.PEM))
            key_path=_write(self.root/(common+"-key.pem"),
                              private.private_bytes(serialization.Encoding.PEM,
                              serialization.PrivateFormat.PKCS8,
                              serialization.NoEncryption()))
            return cert_path,key_path,certificate
        self.server_cert,self.server_key,_=issue("server",x509.DNSName("localhost"),True)
        self.client_cert,self.client_key,self.client=issue(
             "client",x509.UniformResourceIdentifier(self.client_uri),False)
        self.verifier=BoundEngineIdentity(
            issuer="https://issuer.abc-ci.example",audience="abc-engine:ENG-05",
            jwks_uri="https://issuer.abc-ci.example/.well-known/jwks.json",
            jwks_client=FakeJWKS(self.signer))
        self.server=private_engine_server(host="127.0.0.1",port=0,
           target_engine="ENG-05",caller_engine="ENG-04",
           consumer_id=self.consumer,certfile=self.server_cert,
           keyfile=self.server_key,ca_file=self.ca_path,verifier=self.verifier)
        self.addCleanup(self.server.server_close)
        runner=threading.Thread(target=self.server.serve_forever,daemon=True)
        runner.start()
        self.addCleanup(self.server.shutdown)
        self.port=self.server.server_address[1]
        self.message={"request_id":str(uuid.uuid4()),"engine_id":"ENG-05",
                      "contract_version":VERSION,"consumer_id":self.consumer,
                      "session_id":str(uuid.uuid4()),
                      "payload":{"service_id":"synthetic:hair-color","fixture":None}}

    def token(self,*,consumer=None,binding=None,engine="ENG-04",expires=65):
        thumb=base64.urlsafe_b64encode(hashlib.sha256(
            self.client.public_bytes(serialization.Encoding.DER)).digest()).rstrip(b"=").decode()
        claims={"iss":"https://issuer.abc-ci.example","aud":"abc-engine:ENG-05",
             "sub":self.client_uri,"engine_id":engine,
             "consumer_id":consumer or self.consumer,"token_use":"service",
             "iat":int(self.now.timestamp()),"nbf":int(self.now.timestamp()),
             "exp":int(self.now.timestamp())+expires,
             "jti":str(uuid.uuid4()),"cnf":{"x5t#S256":binding or thumb}}
        return jwt.encode(claims,self.signer,algorithm="RS256",
                          headers={"kid":"ci-rotation-1"})

    def call(self,token=None,message=None):
        return send_private_engine_message(
            host="127.0.0.1",port=self.port,server_name="localhost",
            certfile=self.client_cert,keyfile=self.client_key,ca_file=self.ca_path,
            token=self.token() if token is None else token,
            message=self.message if message is None else message)

    def test_real_tls13_mutual_certificate_and_bound_jwt(self):
        r=self.call()
        self.assertEqual(r["engine_id"],"ENG-05")
        self.assertEqual(r["result"]["unknowns"],["SOURCE_UNVERIFIED"])
        self.assertFalse(r["release_approved"])

    def test_correct_signed_token_wrong_certificate_thumbprint_denied(self):
        r=self.call(token=self.token(binding="invalid-cert-binding"))
        self.assertEqual(r["error"],"engine_request_rejected")

    def test_wrong_caller_engine_and_consumer_denied(self):
        for token in (self.token(engine="ENG-06"),self.token(consumer="elsewhere")):
            with self.subTest(token=token[-10:]):
                self.assertEqual(self.call(token=token)["error"],"engine_request_rejected")

    def test_cross_tenant_request_mismatch_denied(self):
        r=self.call(message={**self.message,"consumer_id":"other-consumer"})
        self.assertEqual(r["error"],"engine_request_rejected")

    def test_missing_auth_header_denied_and_no_plain_network_listener(self):
        self.assertEqual(self.call(token="")["error"],"engine_request_rejected")
        with self.assertRaises(ValueError):
            private_engine_server(host="0.0.0.0",port=1,target_engine="ENG-05",
                caller_engine="ENG-04",consumer_id=self.consumer,
                certfile=self.server_cert,keyfile=self.server_key,
                ca_file=self.ca_path,verifier=self.verifier)

    def test_real_mtls_client_adapter_executes_independent_eng05(self):
        adapter=ManagedMTLSEngineClient(
            endpoints={"ENG-05":{"host":"127.0.0.1","port":self.port,
                       "server_name":"localhost"}},
            client_cert=self.client_cert,client_key=self.client_key,
            trust_ca=self.ca_path,
            workload_token_provider=lambda target,consumer:self.token())
        result=adapter.call("ENG-05",consumer_id=self.consumer,
            session_id=self.message["session_id"],payload=self.message["payload"])
        self.assertEqual(result["ontology_version"],"synthetic-ontology.1")
        with self.assertRaises(DomainError):
            adapter.call("ENG-04",consumer_id=self.consumer,
                         session_id=self.message["session_id"],payload={})

    def test_remote_client_rejects_unbound_token(self):
        adapter=ManagedMTLSEngineClient(
            endpoints={"ENG-05":{"host":"127.0.0.1","port":self.port,
                       "server_name":"localhost"}},
            client_cert=self.client_cert,client_key=self.client_key,
            trust_ca=self.ca_path,
            workload_token_provider=lambda target,consumer:self.token(
                      binding="forged-certificate-thumbprint"))
        with self.assertRaises(DomainError):
            adapter.call("ENG-05",consumer_id=self.consumer,
                session_id=self.message["session_id"],payload=self.message["payload"])

    def test_wrong_token_lifetime_denied(self):
        self.assertEqual(self.call(token=self.token(expires=121))["error"],
                         "engine_request_rejected")
        self.assertEqual(self.call(token=self.token(expires=-30))["error"],
                         "engine_request_rejected")
    def test_three_independent_servers_cannot_start_without_managed_material(self):
        config={"ABC_ENV":"LOCAL_INTEGRATION_ONLY",
                "ABC_NETWORK_BOUNDARY":"LOOPBACK_ONLY",
                "ABC_ENGINE_SYNTHETIC_ONLY":"true",
                "ABC_ENGINE_ID":"ENG-05",
                "ABC_CALLER_ENGINE_ID":"ENG-04",
                "ABC_ENGINE_CONSUMER_ID":"ci-consumer-01",
                "ABC_ENGINE_PORT":"11005"}
        with self.assertRaisesRegex(ValueError,"externally_managed_tls"):
            configure_private_engine_service(config)
        for change in ({"ABC_ENV":"PRODUCTION"},
                       {"ABC_NETWORK_BOUNDARY":"PUBLIC_HTTP"},
                       {"ABC_ENGINE_SYNTHETIC_ONLY":"false"},
                       {"ABC_ENGINE_ID":"ENG-04"},
                       {"ABC_ENGINE_PORT":"80"}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                configure_private_engine_service({**config,**change})

    def test_private_staging_service_must_be_distinct_and_externally_provisioned(self):
        from unittest.mock import patch,Mock
        env={"ABC_ENV":"STAGING_PRIVATE",
             "ABC_NETWORK_BOUNDARY":"RENDER_PRIVATE_SERVICE",
             "ABC_RENDER_SERVICE_KIND":"PRIVATE",
             "ABC_STAGING_PURPOSE":"SYNTHETIC_NO_CLIENT_DATA",
             "ABC_ENGINE_SYNTHETIC_ONLY":"true",
             "ABC_ENGINE_ID":"ENG-05","ABC_CALLER_ENGINE_ID":"ENG-03",
             "ABC_ENGINE_CONSUMER_ID":"ci-consumer-01",
             "ABC_ENGINE_PORT":"11005",
             "ABC_TLS_CERT_FILE":"/run/secrets/engine.crt",
             "ABC_TLS_KEY_FILE":"/run/secrets/engine.key",
             "ABC_TLS_CA_FILE":"/run/secrets/trust.crt",
             "ABC_WORKLOAD_ISSUER":"https://issuer.abc-ci.example",
             "ABC_WORKLOAD_JWKS_URL":"https://issuer.abc-ci.example/jwks"}
        with patch("abc_foundation.private_engine_service_server.private_engine_server",
                   return_value=Mock()) as builder:
            configure_private_engine_service(env)
            self.assertEqual(builder.call_args.kwargs["host"],"0.0.0.0")
            self.assertTrue(builder.call_args.kwargs["managed_private"])
        for tamper in ({"ABC_RENDER_SERVICE_KIND":"WEB"},
                       {"ABC_NETWORK_BOUNDARY":"PUBLIC_HTTP"},
                       {"ABC_TLS_KEY_FILE":""},
                       {"ABC_ENV":"PRODUCTION"}):
            with self.subTest(tamper=tamper),self.assertRaises(ValueError):
                configure_private_engine_service({**env,**tamper})

    def test_managed_private_client_rejects_public_and_unpinned_dns(self):
        for host in ("public.example.com","abc-engine.onrender.com",
                     "abc-engine.internal.evil.com","http://abc-engine.internal"):
            with self.subTest(host=host),self.assertRaises(ValueError):
                send_private_engine_message(host=host,port=10000,
                    server_name=host,certfile="unused",keyfile="unused",
                    ca_file="unused",token="unused",message={},
                    managed_private=True)

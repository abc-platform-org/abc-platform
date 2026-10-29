"""Three real independent OS processes, genuine TLS1.3 mTLS, JWT-bound synthetic E2E.

All private keys/CA are ephemeral test fixtures, generated in CI's temporary
directory and destroyed at end. NOT managed PKI or deployed Render services.
"""
import base64
import hashlib
import multiprocessing
import os
import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import jwt
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

from abc_foundation.eng02_consultation import SYNTHETIC_SERVICE
from abc_foundation.eng04_analysis import FIELDS
from abc_foundation.managed_engine_client import ManagedMTLSEngineClient
from abc_foundation.private_engine_transport import private_engine_server
from abc_foundation.service_mesh_identity import BoundEngineIdentity


ISSUER = "https://issuer.abc-ci.example"
CONSUMER = "ci-pipeline-worker"
CALLER = "ENG-03"
TARGETS = ("ENG-04","ENG-05","ENG-06")


class _OfflineJWKS:
    def __init__(self, public_key):
        self.public_key=public_key
    def get_signing_key_from_jwt(self, unused_token):
        return SimpleNamespace(key=self.public_key)


def _engine_child(engine, cert, key, ca, pub_pem, pipe):
    server=None
    try:
        public=serialization.load_pem_public_key(pub_pem)
        verifier=BoundEngineIdentity(
            issuer=ISSUER, audience="abc-engine:"+engine,
            jwks_uri=ISSUER+"/.well-known/jwks.json",
            jwks_client=_OfflineJWKS(public))
        server=private_engine_server(
            host="127.0.0.1",port=0,
            target_engine=engine,caller_engine=CALLER,
            consumer_id=CONSUMER,certfile=cert,keyfile=key,
            ca_file=ca,verifier=verifier)
        pipe.send(server.server_address[1])
        pipe.close()
        server.serve_forever(poll_interval=0.05)
    except BaseException as error:
        try:pipe.send({"startup_error":type(error).__name__})
        except (OSError,EOFError):pass
    finally:
        if server:server.server_close()
        pipe.close()


class IndependentPrivateEngineE2E(unittest.TestCase):
    def test_real_three_process_mtls_identity_and_bounded_decision(self):
        with tempfile.TemporaryDirectory(prefix="abc-ci-pki-") as temp:
            root=Path(temp)
            now=datetime.now(timezone.utc)
            def key():
                return rsa.generate_private_key(public_exponent=65537,key_size=2048)
            def save(name,private,certificate):
                private_path=root/(name+".key")
                cert_path=root/(name+".crt")
                private_path.write_bytes(private.private_bytes(
                    serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,
                    serialization.NoEncryption()))
                os.chmod(private_path,0o600)
                cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
                return str(cert_path),str(private_path)
            ca_key=key()
            ca_name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,"ABC disposable CI CA")])
            ca_cert=(x509.CertificateBuilder().subject_name(ca_name)
               .issuer_name(ca_name).public_key(ca_key.public_key())
               .serial_number(x509.random_serial_number())
               .not_valid_before(now-timedelta(minutes=2))
               .not_valid_after(now+timedelta(hours=2))
               .add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True)
               .sign(ca_key,hashes.SHA256()))
            ca=root/"ca.crt"
            ca.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))
            def issue(name,san,server):
                private=key()
                certificate=(x509.CertificateBuilder()
                    .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,name)]))
                    .issuer_name(ca_cert.subject).public_key(private.public_key())
                    .serial_number(x509.random_serial_number())
                    .not_valid_before(now-timedelta(minutes=1))
                    .not_valid_after(now+timedelta(minutes=15))
                    .add_extension(x509.BasicConstraints(ca=False,path_length=None),
                                   critical=True)
                    .add_extension(x509.SubjectAlternativeName([san]),critical=False)
                    .add_extension(x509.ExtendedKeyUsage([
                        ExtendedKeyUsageOID.SERVER_AUTH if server
                        else ExtendedKeyUsageOID.CLIENT_AUTH]),critical=False)
                    .sign(ca_key,hashes.SHA256()))
                return (*save(name,private,certificate),certificate)
            client_cert,client_key,client=issue(
                "eng03-client",x509.UniformResourceIdentifier(
                    "spiffe://abc.internal/eng03/"+CONSUMER),False)
            signing_key=key()
            pub_pem=signing_key.public_key().public_bytes(
                serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
            thumb=base64.urlsafe_b64encode(hashlib.sha256(client.public_bytes(
                serialization.Encoding.DER)).digest()).rstrip(b"=").decode("ascii")
            def token(engine,consumer):
                clock=int(datetime.now(timezone.utc).timestamp())
                claims={"iss":ISSUER,"aud":"abc-engine:"+engine,
                    "sub":"spiffe://abc.internal/eng03/"+CONSUMER,
                    "engine_id":CALLER,"consumer_id":consumer,
                    "token_use":"service","iat":clock,"nbf":clock,
                    "exp":clock+60,"jti":str(uuid.uuid4()),
                    "cnf":{"x5t#S256":thumb}}
                return jwt.encode(claims,signing_key,algorithm="RS256",
                                  headers={"kid":"ci-only-ephemeral"})
            ctx=multiprocessing.get_context("spawn")
            children=[]
            endpoints={}
            try:
                for target in TARGETS:
                    cert_path,key_path,_=issue(
                        target.lower()+"-server",x509.DNSName("localhost"),True)
                    receive,send=ctx.Pipe(duplex=False)
                    child=ctx.Process(target=_engine_child,args=(
                        target,cert_path,key_path,str(ca),pub_pem,send),daemon=True)
                    child.start()
                    send.close()
                    self.assertTrue(receive.poll(12),
                                    "independent engine startup timed out")
                    port=receive.recv()
                    receive.close()
                    self.assertIsInstance(port,int,port)
                    self.assertTrue(child.is_alive())
                    children.append(child)
                    endpoints[target]={"host":"127.0.0.1","port":port,
                                       "server_name":"localhost"}
                client_adapter=ManagedMTLSEngineClient(
                    endpoints=endpoints,client_cert=client_cert,
                    client_key=client_key,trust_ca=str(ca),
                    workload_token_provider=token)
                session=str(uuid.uuid4())
                evidence=[{"attribute_key":field,
                    "evidence_id":str(uuid.uuid4()),"service_id":SYNTHETIC_SERVICE,
                    "session_id":session,"evidence_class":"UNKNOWN",
                    "source_type":"NOT_AVAILABLE","value":None}
                    for field in sorted(FIELDS)]
                analysis=client_adapter.call(
                    "ENG-04",consumer_id=CONSUMER,session_id=session,
                    payload={"evidence":evidence})
                knowledge=client_adapter.call(
                    "ENG-05",consumer_id=CONSUMER,session_id=session,
                    payload={"service_id":SYNTHETIC_SERVICE,"fixture":None})
                decision=client_adapter.call(
                    "ENG-06",consumer_id=CONSUMER,session_id=session,
                    payload={"analysis":analysis,"knowledge":knowledge})
                self.assertEqual(analysis["session_id"],session)
                self.assertEqual(len(analysis["unknowns"]),4)
                self.assertEqual(knowledge["unknowns"],["SOURCE_UNVERIFIED"])
                self.assertEqual(decision["candidates"],[])
                self.assertTrue(decision["excluded_options"])
                # No specialized professional treatment or release is authorized.
                self.assertNotIn("treatment_approved",decision)
                self.assertEqual(len({child.pid for child in children}),3)
                self.assertTrue(all(child.is_alive() for child in children))
            finally:
                for child in children:
                    child.terminate()
                for child in children:
                    child.join(timeout=5)
                    if child.is_alive():
                        child.kill()
                        child.join(timeout=2)

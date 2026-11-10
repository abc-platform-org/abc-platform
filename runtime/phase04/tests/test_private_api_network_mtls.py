"""Actual TLS1.3 handshake and URI-SAN authorization for private staging API.

Temporary cryptographic certificates are generated only inside disposable CI,
never as production identity material.
"""
import http.client
import os
import ssl
import tempfile
import threading
import unittest
from datetime import datetime,timedelta,timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID

from abc_foundation.private_api_mtls import (
    BoundMTLSHTTPServer,parse_allowed_private_callers)
from abc_foundation.service_mesh_identity import require_mtls_context

CALLER="spiffe://abc.internal/gateway/approved-client"


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"synthetic-protected")
    def log_message(self,*_):pass


class RealPrivateAPIHandshake(unittest.TestCase):
    def test_real_tls13_rejects_missing_or_wrong_client_identity(self):
        with tempfile.TemporaryDirectory(prefix="abc-private-api-ci-") as dirname:
            root=Path(dirname)
            now=datetime.now(timezone.utc)
            def key():
                return rsa.generate_private_key(public_exponent=65537,key_size=2048)
            def private(k):
                return k.private_bytes(serialization.Encoding.PEM,
                    serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
            name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,"ABC disposable test CA")])
            cak=key()
            ca=(x509.CertificateBuilder().subject_name(name).issuer_name(name)
                .public_key(cak.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(now-timedelta(minutes=2))
                .not_valid_after(now+timedelta(hours=1))
                .add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True)
                .sign(cak,hashes.SHA256()))
            ca_path=root/"ca.crt"
            ca_path.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
            def issue(label,subject_name,server):
                k=key()
                cert=(x509.CertificateBuilder()
                    .subject_name(x509.Name([
                        x509.NameAttribute(NameOID.COMMON_NAME,label)]))
                    .issuer_name(ca.subject).public_key(k.public_key())
                    .serial_number(x509.random_serial_number())
                    .not_valid_before(now-timedelta(minutes=2))
                    .not_valid_after(now+timedelta(minutes=20))
                    .add_extension(x509.BasicConstraints(ca=False,path_length=None),
                                   critical=True)
                    .add_extension(x509.SubjectAlternativeName([
                        x509.DNSName(subject_name) if server
                        else x509.UniformResourceIdentifier(subject_name)]),
                        critical=False)
                    .add_extension(x509.ExtendedKeyUsage([
                        ExtendedKeyUsageOID.SERVER_AUTH if server
                        else ExtendedKeyUsageOID.CLIENT_AUTH]),critical=False)
                    .sign(cak,hashes.SHA256()))
                crt=root/(label+".crt")
                pem=root/(label+".key")
                crt.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
                pem.write_bytes(private(k));os.chmod(pem,0o600)
                return str(crt),str(pem)
            srv_cert,srv_key=issue("server","localhost",True)
            client_cert,client_key=issue("allowed",CALLER,False)
            wrong_cert,wrong_key=issue("unapproved",
                "spiffe://abc.internal/gateway/unapproved-client",False)
            old_engine_cert,old_engine_key=issue("legacy-engine",
                "spiffe://abc.internal/eng03/eng03-worker",False)
            canonical_engine_cert,canonical_engine_key=issue("canonical-engine",
                "spiffe://abc.internal/staging/eng-03",False)
            server=BoundMTLSHTTPServer(("127.0.0.1",0),_Handler,
                context=require_mtls_context(certificate=srv_cert,
                    key=srv_key,ca_file=str(ca_path),server=True),
                allowed_client_uris=parse_allowed_private_callers(CALLER))
            self.addCleanup(server.server_close)
            thread=threading.Thread(target=server.serve_forever,
                                    kwargs={"poll_interval":0.05},daemon=True)
            thread.start()
            self.addCleanup(server.shutdown)

            def request(cert=None,keyfile=None):
                context=ssl.create_default_context(cafile=str(ca_path))
                context.minimum_version=ssl.TLSVersion.TLSv1_3
                if cert:
                    context.load_cert_chain(cert,keyfile)
                con=http.client.HTTPSConnection("localhost",
                    port=server.server_address[1],context=context,timeout=3)
                try:
                    con.request("GET","/healthz")
                    r=con.getresponse()
                    return r.status,r.read(100)
                finally:con.close()
            self.assertEqual(request(client_cert,client_key),
                             (200,b"synthetic-protected"))
            for creds in (
                (None,None),
                (wrong_cert,wrong_key),
                (old_engine_cert,old_engine_key),
                (canonical_engine_cert,canonical_engine_key),
            ):
                with self.subTest(credentials=creds),self.assertRaises(
                    (OSError,ssl.SSLError,http.client.HTTPException)):
                    request(*creds)

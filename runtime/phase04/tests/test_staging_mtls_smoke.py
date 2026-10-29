"""Private-network TLS probe never falls back to HTTP or bearer auth."""
import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from abc_foundation.staging_mtls_smoke import (
    check_mtls_api_url,run_mtls_smoke)


BASE="https://abc-p04-private-api-synthetic-abc123:10000"


class PrivateAPIMTLSSmokeTests(unittest.TestCase):
    def test_strict_private_https_host_san_and_port(self):
        self.assertEqual(check_mtls_api_url(BASE),BASE)
        for url in (
            "http://abc-p04-private-api-synthetic-abc123:10000",
            "https://abc-p04-private-api-synthetic-abc123.onrender.com:10000",
            "https://abc-p04-private-api-synthetic-abc123.example.com:10000",
            "https://abc-p04-private-api-synthetic-abc123:10001",
            "https://127.0.0.1:10000",
            BASE+"/v1/consultations",
            BASE+"?token=secret",
            BASE+"#fragment",
            "https://user:password@abc-p04-private-api-synthetic-abc123:10000",
        ):
            with self.subTest(url=url),self.assertRaises(ValueError):
                check_mtls_api_url(url)

    def test_real_probe_contract_has_no_client_data_and_denies_anonymous_write(self):
        class Response:
            status=200
            def __enter__(self):return self
            def __exit__(self,*_):return False
            def read(self,unused):return b'{"status":"ok","capability":"OIDC_PG_LOOPBACK"}'
        requests=[]
        def transport(req,timeout):
            requests.append((req.full_url,req.get_method(),
                             req.headers.get("Authorization"),timeout))
            if req.get_method()=="POST":
                raise HTTPError(req.full_url,401,"unauthenticated",{},
                    io.BytesIO(b'{"error":"unauthenticated"}'))
            return Response()
        with patch("abc_foundation.staging_mtls_smoke.require_mtls_context"):
            result=run_mtls_smoke(BASE,client_cert="/mounted/client.crt",
                   client_key="/mounted/client.key",root_ca="/mounted/ca.crt",
                   transport=transport)
        self.assertFalse(result["release_approved"])
        self.assertEqual(result["status"],{
            "/healthz":200,"/v1/consultations":401})
        self.assertEqual(len(requests),2)
        self.assertTrue(all(authorization is None and timeout==5
                            for _,_,authorization,timeout in requests))

    def test_false_health_must_fail_closed(self):
        class UntrustedResponse:
            status=200
            def __enter__(self):return self
            def __exit__(self,*_):return False
            def read(self,unused):return b'{"status":"ok","capability":"PRODUCTION"}'
        with patch("abc_foundation.staging_mtls_smoke.require_mtls_context"):
            with self.assertRaisesRegex(RuntimeError,"unexpected_capability"):
                run_mtls_smoke(BASE,client_cert="x",client_key="y",root_ca="z",
                     transport=lambda *_:UntrustedResponse())

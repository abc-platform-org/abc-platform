"""Fail-closed staging deployment guard tests; no cloud credentials."""
import os
import pathlib
import unittest
from unittest.mock import Mock

from abc_foundation.staging_api import validate_staging_dsn, make_private_server, assert_staging_database
from abc_foundation.staging_worker import configure_worker
from abc_foundation.staging_migrate import validate_migrator_config, planned_migrations, FILENAMES
from abc_foundation.staging_smoke import check_private_url, smoke

STAGING_ENV={
    "ABC_ENV":"STAGING_PRIVATE",
    "ABC_STAGING_PURPOSE":"SYNTHETIC_NO_CLIENT_DATA",
    "ABC_NETWORK_BOUNDARY":"RENDER_PRIVATE_SERVICE",
    "PORT":"10876",
}

class StagingGuardTests(unittest.TestCase):
    def test_migration_manifest_complete_and_sha256(self):
        plan=planned_migrations()
        self.assertEqual(tuple(x[0] for x in plan),FILENAMES)
        self.assertEqual(len(plan),9)
        self.assertTrue(all(len(digest)==64 for _,digest in plan))

    def test_staging_dsn_rejects_admin_or_missing_tls(self):
        for dsn in (
            "postgresql://abc_staging_migrator:secret@db.internal/abc_staging?sslmode=require",
            "postgresql://abc_app:secret@db.internal/abc_staging",
            "postgresql://abc_app:secret@localhost/abc_staging?sslmode=require",
        ):
            with self.assertRaises(ValueError):
                validate_staging_dsn(dsn,"abc_app")
        self.assertTrue(validate_staging_dsn(
            "postgresql://abc_app:secret@db.internal/abc_staging?sslmode=require","abc_app"))

    def test_private_staging_refuses_public_or_missing_boundary(self):
        for patch in (
            {"ABC_ENV":"PRODUCTION"},
            {"ABC_STAGING_PURPOSE":"REAL_CUSTOMER"},
            {"ABC_NETWORK_BOUNDARY":"PUBLIC_WEB"},
            {"PORT":"80"},
        ):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                make_private_server(environ={**STAGING_ENV,**patch},store=Mock(),verifier=Mock())

    def test_private_staging_port_zero_refused(self):
        with self.assertRaises(ValueError):
            make_private_server(environ={**STAGING_ENV,"PORT":"0"},store=Mock(),verifier=Mock())
    def test_worker_rejects_http_service_boundary(self):
        with self.assertRaises(ValueError):
            configure_worker({**STAGING_ENV,"ABC_WORKER_DSN":"none","ABC_CONSUMER_ID":"test-consumer"})


    def test_private_smoke_rejects_public_and_unexpected_urls(self):
        bad=[
            "https://abc-p04-private-api-abc.onrender.com",
            "https://abc-p04-private-api-abc",
            "http://example.com",
            "http://localhost:10000",
            "http://abc-p04-private-api-abc.example.org:10000",
            "http://abc-p04-private-api-abc:10001",
            "http://abc-p04-private-api-abc:10000/anything",
            "http://abc-p04-private-api-abc:10000/?token=secret",
            "http://user:password@abc-p04-private-api-abc:10000",
        ]
        for url in bad:
            with self.subTest(url=url),self.assertRaises(ValueError):
                check_private_url(url)
        self.assertEqual(check_private_url("http://abc-p04-private-api-abc:10000"),
                         "http://abc-p04-private-api-abc:10000")

    def test_staging_smoke_health_and_negative_auth_without_token(self):
        import io
        from urllib.error import HTTPError
        calls=[]
        class Good:
            def __init__(self,body):
                self.status=200
                self.stream=io.BytesIO(body)
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,n): return self.stream.read(n)
        def transport(req,timeout):
            calls.append((req.full_url,req.get_method(),req.headers.get("Authorization")))
            if req.get_method()=="POST":
                raise HTTPError(req.full_url,401,"blocked",{},io.BytesIO(b'{"error":"unauthenticated"}'))
            return Good(b'{"status":"ok","capability":"OIDC_PG_LOOPBACK"}')
        output=smoke("http://abc-p04-private-api-test:10000",transport)
        self.assertEqual(output,{"/healthz":200,"/v1/consultations":401})
        self.assertTrue(all(authorization is None for _,_,authorization in calls))

    def test_staging_smoke_refuses_false_health(self):
        import io
        class Bad:
            status=200
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,n): return b'{"status":"ok","capability":"PRODUCTION"}'
        with self.assertRaises(RuntimeError):
            smoke("http://abc-p04-private-api-test:10000",lambda *_args,**_kwargs:Bad())

    def test_migrator_rejects_prod_admin_and_weak_secrets(self):
        base={
            "ABC_ENV":"STAGING_MIGRATION_PRIVATE",
            "ABC_MIGRATION_APPROVAL":"APPROVED_STAGING_ONLY",
            "ABC_STAGING_MIGRATOR_DSN":"postgresql://abc_staging_migrator@db.private/abc_staging?sslmode=require",
            "ABC_STAGING_APP_PASSWORD":"A"*32,
            "ABC_STAGING_WORKER_PASSWORD":"B"*32,
            "ABC_STAGING_ORCHESTRATOR_PASSWORD":"C"*32,
            "ABC_STAGING_ANSWER_WORKER_PASSWORD":"D"*32,
        }
        self.assertIsInstance(validate_migrator_config(base),str)
        for bad in (
            {"ABC_ENV":"PRODUCTION"},
            {"ABC_MIGRATION_APPROVAL":""},
            {"ABC_STAGING_APP_PASSWORD":"weak"},
            {"ABC_STAGING_WORKER_PASSWORD":"A"*32},
            {"ABC_STAGING_ORCHESTRATOR_PASSWORD":"A"*32},
            {"ABC_STAGING_ORCHESTRATOR_PASSWORD":"short"},
            {"ABC_STAGING_ANSWER_WORKER_PASSWORD":"A"*32},
            {"ABC_STAGING_ANSWER_WORKER_PASSWORD":"short"},
            {"ABC_STAGING_MIGRATOR_DSN":"postgresql://postgres@db.private/abc_staging?sslmode=require"},
            {"ABC_STAGING_MIGRATOR_DSN":"postgresql://abc_staging_migrator@db.private/abc_staging"},
        ):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                validate_migrator_config({**base,**bad})

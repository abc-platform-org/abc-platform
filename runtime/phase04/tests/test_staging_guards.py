"""Fail-closed staging deployment guard tests; no cloud credentials."""
import os
import pathlib
import unittest
from unittest.mock import Mock

from abc_foundation.staging_api import validate_staging_dsn, make_private_server, assert_staging_database
from abc_foundation.staging_worker import configure_worker
from abc_foundation.staging_migrate import validate_migrator_config, planned_migrations, FILENAMES

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
        self.assertEqual(len(plan),6)
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

    def test_migrator_rejects_prod_admin_and_weak_secrets(self):
        base={
            "ABC_ENV":"STAGING_MIGRATION_PRIVATE",
            "ABC_MIGRATION_APPROVAL":"APPROVED_STAGING_ONLY",
            "ABC_STAGING_MIGRATOR_DSN":"postgresql://abc_staging_migrator@db.private/abc_staging?sslmode=require",
            "ABC_STAGING_APP_PASSWORD":"A"*32,
            "ABC_STAGING_WORKER_PASSWORD":"B"*32,
        }
        self.assertIsInstance(validate_migrator_config(base),str)
        for bad in (
            {"ABC_ENV":"PRODUCTION"},
            {"ABC_MIGRATION_APPROVAL":""},
            {"ABC_STAGING_APP_PASSWORD":"weak"},
            {"ABC_STAGING_WORKER_PASSWORD":"A"*32},
            {"ABC_STAGING_MIGRATOR_DSN":"postgresql://postgres@db.private/abc_staging?sslmode=require"},
            {"ABC_STAGING_MIGRATOR_DSN":"postgresql://abc_staging_migrator@db.private/abc_staging"},
        ):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                validate_migrator_config({**base,**bad})

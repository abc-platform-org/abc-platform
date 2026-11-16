"""P0 security: private API cannot start before signed external authorization.

Synthetic config, legacy DB compatibility, or dependency injection are never
deployment authority. No live endpoint, secret or managed identity is used.
"""
import os
import socket
import unittest
from unittest.mock import Mock, patch

from abc_foundation.staging_api import make_private_server, main, validate_staging_dsn

BASE = {
    "ABC_ENV": "STAGING_PRIVATE",
    "ABC_STAGING_PURPOSE": "SYNTHETIC_NO_CLIENT_DATA",
    "ABC_NETWORK_BOUNDARY": "RENDER_PRIVATE_SERVICE",
    "PORT": "10000",
}
MANAGED = {
    "ABC_DB_AUTH_MODE": "MANAGED_MTLS",
    "ABC_DB_WORKLOAD_LOGIN": "abc_api_managed",
    "ABC_DB_CLIENT_DN": "CN=abc-api",
    "ABC_DB_ISSUER_DN": "CN=external-issuer",
    "ABC_DB_CERT_SERIAL": "opaque-test-only",
    "ABC_PG_DSN": "postgresql://abc_api_managed@db.private/abc?sslmode=verify-full",
    "ABC_API_TRANSPORT": "MTLS_TLS13",
    "ABC_API_TLS_CERT_FILE": "/external/api.crt",
    "ABC_API_TLS_KEY_FILE": "/external/api.key",
    "ABC_API_TLS_CA_FILE": "/external/issuer.crt",
    "ABC_API_ALLOWED_CLIENT_URIS": "spiffe://abc.internal/gateway/test-caller",
    "ABC_OIDC_ISSUER": "https://identity.invalid/",
    "ABC_OIDC_AUDIENCE": "abc-api",
    "ABC_OIDC_JWKS_URI": "https://identity.invalid/jwks",
}


class StagingOwnerHoldNegativeTests(unittest.TestCase):
    def test_correct_looking_managed_env_still_blocked(self):
        with self.assertRaisesRegex(ValueError,
                                    "staging_owner_cost_and_external_identity_hold"):
            make_private_server(environ={**BASE, **MANAGED})

    def test_injected_dependencies_and_forged_approval_cannot_bypass(self):
        env = {
            **BASE, **MANAGED,
            "ABC_STAGING_APPROVAL": "APPROVED",
            "ABC_SECURITY_SIGNOFF": "APPROVED",
            "ABC_SRE_SIGNOFF": "APPROVED",
            "ABC_OWNER_COST_AUTHORIZED": "true",
        }
        for store, verifier in ((None,None),(Mock(),Mock()),(Mock(),None),(None,Mock())):
            with self.subTest(store=store is not None, verifier=verifier is not None):
                with self.assertRaisesRegex(
                        ValueError, "staging_owner_cost_and_external_identity_hold"):
                    make_private_server(environ=env,store=store,verifier=verifier)

    def test_explicit_legacy_database_flags_always_denied(self):
        legacy = {
            "ABC_DB_AUTH_MODE": "LEGACY_SYNTHETIC",
            "ABC_PG_DSN":
                "postgresql://abc_app:synthetic@db.private/abc?sslmode=require",
        }
        for opts in (legacy, {**legacy, "ABC_SYNTHETIC_LEGACY_DB_COMPAT":"true"},
                     {**MANAGED, "ABC_SYNTHETIC_LEGACY_DB_COMPAT":"true"}):
            with self.subTest(config=opts.get("ABC_DB_AUTH_MODE")):
                with self.assertRaisesRegex(
                        ValueError,"legacy_shared_database_login_forbidden_in_staging"):
                    make_private_server(environ={**BASE,**opts},store=Mock(),
                                        verifier=Mock())

    def test_fake_flags_cannot_force_a_listener_or_database_connection(self):
        with (patch("socket.socket",side_effect=AssertionError("socket_bound")) as sock,
              patch("psycopg.connect",side_effect=AssertionError("db_connected")) as db):
            with self.assertRaisesRegex(
                    ValueError,"staging_owner_cost_and_external_identity_hold"):
                make_private_server(environ={**BASE,**MANAGED},store=Mock(),
                                    verifier=Mock())
            sock.assert_not_called()
            db.assert_not_called()

    def test_main_entrypoint_fails_closed_before_listener(self):
        with patch.dict(os.environ,{**BASE,**MANAGED},clear=True):
            with patch("socket.socket",side_effect=AssertionError("socket_bound")) as sock:
                with self.assertRaisesRegex(
                        ValueError,"staging_owner_cost_and_external_identity_hold"):
                    main()
                sock.assert_not_called()

    def test_historical_dsn_check_is_not_staging_authorization(self):
        dsn="postgresql://abc_app:password@db.private/abc?sslmode=require"
        self.assertTrue(validate_staging_dsn(dsn,"abc_app"))
        with self.assertRaisesRegex(
                ValueError,"legacy_shared_database_login_forbidden_in_staging"):
            make_private_server(environ={**BASE,"ABC_DB_AUTH_MODE":"LEGACY_SYNTHETIC",
                "ABC_SYNTHETIC_LEGACY_DB_COMPAT":"true","ABC_PG_DSN":dsn})

    def test_no_public_network_customer_purpose_or_bad_port(self):
        for patch_env, error in (
            ({"ABC_ENV":"PRODUCTION"}, "private_staging_gate_not_approved"),
            ({"ABC_STAGING_PURPOSE":"REAL_CUSTOMER"},"private_staging_gate_not_approved"),
            ({"ABC_NETWORK_BOUNDARY":"PUBLIC_WEB"},"private_network_boundary_not_declared"),
            ({"PORT":"0"},"invalid_staging_port"),
            ({"PORT":"not-a-port"},"invalid_staging_port"),
        ):
            with self.subTest(patch=patch_env),self.assertRaisesRegex(ValueError,error):
                make_private_server(environ={**BASE,**patch_env})


if __name__ == "__main__":
    unittest.main()

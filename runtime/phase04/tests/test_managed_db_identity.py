"""Mutual TLS and physical PostgreSQL service identity admission tests."""
import unittest
from unittest.mock import Mock
from abc_foundation.managed_db_identity import (
    validate_managed_db_dsn,assert_managed_db_peer)

LOGIN="abc_api_c33a4d5c6a21"
DSN=("postgresql://"+LOGIN+"@abc-db.private/abc_staging?"
     "sslmode=verify-full&sslcert=/run/secrets/workload.crt"
     "&sslkey=/run/secrets/workload.key&sslrootcert=/run/secrets/ca.crt")


class ManagedDBAdmissionTests(unittest.TestCase):
    def test_strict_pinned_managed_dsn(self):
        self.assertTrue(validate_managed_db_dsn(DSN,expected_login=LOGIN))
        bad=(DSN.replace("verify-full","require"),
             DSN.replace("abc-db.private","public.example.com"),
             DSN.replace(LOGIN,"abc_app"),
             DSN.replace("abc_staging","production"),
             DSN.replace("&sslrootcert=/run/secrets/ca.crt",""))
        for item in bad:
            with self.subTest(dsn=item),self.assertRaises(ValueError):
                validate_managed_db_dsn(item,expected_login=LOGIN)

    def test_db_peer_checked_from_immutable_login_and_tls_view(self):
        approved={"login":LOGIN,"active_role":LOGIN,"ssl":True,
                  "version":"TLSv1.3","client_dn":"CN=ABC workload",
                  "issuer_dn":"CN=Approved CA","client_serial":43707}
        con=Mock()
        con.execute.return_value.fetchone.return_value=approved
        proof=assert_managed_db_peer(con,expected_login=LOGIN,
                      client_dn="CN=ABC workload",issuer_dn="CN=Approved CA",
                      certificate_serial="43707")
        self.assertEqual(proof["authorization"],"NOT_YET_PROVISIONED")
        self.assertIn("pg_stat_ssl",con.execute.call_args.args[0])
        for patch in ({"login":"abc_app"},{"version":"TLSv1.2"},
                      {"ssl":False},{"client_dn":"CN=Other"},
                      {"issuer_dn":"CN=Untrusted"},{"client_serial":44},{"active_role":"abc_app"}):
            with self.subTest(patch=patch),self.assertRaises(ValueError):
                con.execute.return_value.fetchone.return_value={**approved,**patch}
                assert_managed_db_peer(con,expected_login=LOGIN,
                      client_dn="CN=ABC workload",issuer_dn="CN=Approved CA",
                      certificate_serial="43707")

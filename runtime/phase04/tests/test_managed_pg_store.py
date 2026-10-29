"""Managed PostgreSQL runtime adapter unit tests; external CA issuance is not simulated."""
import unittest
from unittest.mock import MagicMock,patch

from abc_foundation.managed_pg_store import ManagedMTLSPostgresStore

LOGIN="abc_api_c33a4d5c6a21"
DSN=("postgresql://"+LOGIN+"@abc-db.private/abc_staging?"
     "sslmode=verify-full&sslcert=/run/secrets/workload.crt"
     "&sslkey=/run/secrets/workload.key&sslrootcert=/run/secrets/ca.crt")


class ManagedDBRuntimeTests(unittest.TestCase):
    def store(self):
        return ManagedMTLSPostgresStore(
            DSN,expected_login=LOGIN,client_dn="CN=approved-service",
            issuer_dn="CN=approved-issuer",certificate_serial="43707")

    def test_physical_client_identity_verified_before_switch_to_app_role(self):
        con=MagicMock()
        con.execute.return_value.fetchone.return_value={
            "role":"abc_app","login":LOGIN}
        with (patch("abc_foundation.managed_pg_store.psycopg.connect",
                    return_value=con) as connect,
              patch("abc_foundation.managed_pg_store.assert_managed_db_peer")
                    as verify):
            returned=self.store()._connect()
        self.assertIs(returned,con)
        self.assertEqual(connect.call_args.kwargs["row_factory"].__name__,"dict_row")
        verify.assert_called_once()
        self.assertEqual(verify.call_args.kwargs["expected_login"],LOGIN)
        self.assertEqual(verify.call_args.kwargs["certificate_serial"],"43707")
        self.assertEqual([call.args[0] for call in con.execute.call_args_list],
                         ["SET ROLE abc_app",
                          "SELECT current_user AS role,session_user AS login"])

    def test_unverified_client_certificate_closes_connection(self):
        con=MagicMock()
        with (patch("abc_foundation.managed_pg_store.psycopg.connect",
                    return_value=con),
              patch("abc_foundation.managed_pg_store.assert_managed_db_peer",
                    side_effect=ValueError("not_verified"))):
            with self.assertRaisesRegex(ValueError,"not_verified"):
                self.store()._connect()
        con.close.assert_called_once()
        con.execute.assert_not_called()

    def test_failed_role_switch_closes_connection(self):
        con=MagicMock()
        con.execute.return_value.fetchone.return_value={
            "role":"abc_app","login":"wrong_credential"}
        with (patch("abc_foundation.managed_pg_store.psycopg.connect",
                    return_value=con),
              patch("abc_foundation.managed_pg_store.assert_managed_db_peer")):
            with self.assertRaisesRegex(ValueError,"role_transition_denied"):
                self.store()._connect()
        con.close.assert_called_once()

    def test_reject_unverified_postgres_host_or_auth_mode(self):
        with self.assertRaises(ValueError):
            ManagedMTLSPostgresStore(
                DSN.replace("verify-full","require"),
                expected_login=LOGIN,client_dn="CN=s",issuer_dn="CN=ca",
                certificate_serial="43707")
        with self.assertRaises(ValueError):
            ManagedMTLSPostgresStore(
                DSN,expected_login=LOGIN,client_dn="CN=s",
                issuer_dn="CN=ca",certificate_serial="")

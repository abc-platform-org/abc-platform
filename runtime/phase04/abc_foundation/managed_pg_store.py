"""Runtime adapter: physical managed mTLS PostgreSQL login, then scoped app role.

The certificate is validated by PostgreSQL hostssl clientcert=verify-full and
the server certificate is validated by libpq sslmode=verify-full. This code only
consumes externally provisioned credentials; it never creates a real PKI.
"""
import psycopg
from psycopg.rows import dict_row

from .pg_store import PostgresStore
from .managed_db_identity import validate_managed_db_dsn,assert_managed_db_peer


class ManagedMTLSPostgresStore(PostgresStore):
    def __init__(self,dsn,*,expected_login,client_dn,issuer_dn,certificate_serial):
        validate_managed_db_dsn(dsn,expected_login=expected_login)
        if not all(isinstance(x,str) and x.strip() for x in (
            client_dn,issuer_dn,certificate_serial)):
            raise ValueError("managed_service_certificate_identity_pins_required")
        super().__init__(dsn)
        self.expected_login=expected_login
        self.client_dn=client_dn
        self.issuer_dn=issuer_dn
        self.certificate_serial=certificate_serial

    def _connect(self):
        con=psycopg.connect(self.dsn,row_factory=dict_row,connect_timeout=4)
        try:
            assert_managed_db_peer(con,
                expected_login=self.expected_login,client_dn=self.client_dn,
                issuer_dn=self.issuer_dn,certificate_serial=self.certificate_serial)
            # Physical LOGIN must be NOINHERIT with a scoped operator-issued
            # SET ROLE grant; post-connection role cannot change session_user.
            con.execute("SET ROLE abc_app")
            role=con.execute(
                "SELECT current_user AS role,session_user AS login"
            ).fetchone()
            if (not role or role["role"]!="abc_app"
                or role["login"]!=self.expected_login):
                raise ValueError("managed_database_role_transition_denied")
            return con
        except BaseException:
            con.close()
            raise

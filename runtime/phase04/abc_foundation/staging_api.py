"""Private-only staging API process. Hosting provider MUST enforce private network."""
import os

from psycopg.conninfo import conninfo_to_dict
from .http_api import handler_factory
from .oidc import OIDCVerifier
from .pg_store import PostgresStore
from .managed_pg_store import ManagedMTLSPostgresStore
from .private_api_mtls import create_private_api_server


def validate_staging_dsn(dsn, expected_role):
    if not dsn or not isinstance(dsn, str):
        raise ValueError("missing_database_dsn")
    parsed = conninfo_to_dict(dsn)
    if parsed.get("user") != expected_role:
        raise ValueError("staging_database_role_mismatch")
    if parsed.get("sslmode") != "require":
        raise ValueError("staging_requires_explicit_tls")
    if parsed.get("host") in (None, "", "localhost", "127.0.0.1", "::1"):
        raise ValueError("staging_requires_managed_database_host")
    return True


def assert_staging_database(store, expected_role, required_tables):
    with store._connect() as con:
        info = con.execute("""
            SELECT current_user AS role,
              (SELECT rolsuper OR rolbypassrls OR rolcreaterole
                 FROM pg_roles WHERE rolname=current_user) AS privileged
        """).fetchone()
        if info["role"] != expected_role or info["privileged"]:
            raise ValueError("database_privilege_boundary_violation")
        for table in required_tables:
            row = con.execute("""
                SELECT cls.relrowsecurity AS rls,cls.relforcerowsecurity AS forced
                FROM pg_class cls
                WHERE cls.oid=to_regclass(%s)
            """, (table,)).fetchone()
            if row is None or not (row["rls"] and row["forced"]):
                raise ValueError("missing_forced_rls_on_"+table.replace(".","_"))


def make_private_server(environ=None, store=None, verifier=None):
    env = os.environ if environ is None else environ
    if env.get("ABC_ENV") != "STAGING_PRIVATE" or env.get("ABC_STAGING_PURPOSE") != "SYNTHETIC_NO_CLIENT_DATA":
        raise ValueError("private_staging_gate_not_approved")
    if env.get("ABC_NETWORK_BOUNDARY") != "RENDER_PRIVATE_SERVICE":
        raise ValueError("private_network_boundary_not_declared")
    port = int(env.get("PORT", "10000"))
    if port < 1024 or port > 65535:
        raise ValueError("invalid_staging_port")
    if store is None:
        dsn=env.get("ABC_PG_DSN")
        auth_mode=env.get("ABC_DB_AUTH_MODE","UNCONFIGURED")
        if auth_mode=="MANAGED_MTLS":
            required=("ABC_DB_WORKLOAD_LOGIN","ABC_DB_CLIENT_DN",
                      "ABC_DB_ISSUER_DN","ABC_DB_CERT_SERIAL")
            if any(not env.get(item) for item in required):
                raise ValueError("managed_mtls_database_identity_pins_required")
            store=ManagedMTLSPostgresStore(
                dsn,expected_login=env["ABC_DB_WORKLOAD_LOGIN"],
                client_dn=env["ABC_DB_CLIENT_DN"],issuer_dn=env["ABC_DB_ISSUER_DN"],
                certificate_serial=env["ABC_DB_CERT_SERIAL"])
        elif auth_mode=="LEGACY_SYNTHETIC":
            if env.get("ABC_SYNTHETIC_LEGACY_DB_COMPAT")!="true":
                raise ValueError("legacy_shared_database_login_not_explicitly_approved")
            validate_staging_dsn(dsn,"abc_app")
            store=PostgresStore(dsn)
        else:
            raise ValueError("unapproved_database_auth_mode")
        assert_staging_database(store,"abc_app",
            ["abc.sessions","abc.memberships","abc.consent_evidence"])
    if verifier is None:
        for key in ("ABC_OIDC_ISSUER", "ABC_OIDC_AUDIENCE", "ABC_OIDC_JWKS_URI"):
            if not env.get(key):
                raise ValueError("missing_"+key)
        verifier = OIDCVerifier(
            issuer=env["ABC_OIDC_ISSUER"], audience=env["ABC_OIDC_AUDIENCE"],
            jwks_uri=env["ABC_OIDC_JWKS_URI"])
    # Private hosting is necessary but insufficient: the listener itself
    # must validate a managed client certificate before parsing HTTP/OIDC.
    # No plaintext fallback, even if the database is synthetic-only.
    return create_private_api_server(
        ("0.0.0.0",port), handler_factory(store,None,verifier),env)


def main():
    http = make_private_server()
    try:
        print("ABC synthetic-only PRIVATE staging API; client/media endpoints disabled", flush=True)
        http.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        http.server_close()


if __name__ == "__main__":
    main()

"""Private-only staging API process. Hosting provider MUST enforce private network."""
import os
from http.server import ThreadingHTTPServer

from psycopg.conninfo import conninfo_to_dict
from .http_api import handler_factory
from .oidc import OIDCVerifier
from .pg_store import PostgresStore


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
        dsn = env.get("ABC_PG_DSN")
        validate_staging_dsn(dsn, "abc_app")
        store = PostgresStore(dsn)
        assert_staging_database(store, "abc_app", ["abc.sessions", "abc.memberships", "abc.consent_evidence"])
    if verifier is None:
        for key in ("ABC_OIDC_ISSUER", "ABC_OIDC_AUDIENCE", "ABC_OIDC_JWKS_URI"):
            if not env.get(key):
                raise ValueError("missing_"+key)
        verifier = OIDCVerifier(
            issuer=env["ABC_OIDC_ISSUER"], audience=env["ABC_OIDC_AUDIENCE"],
            jwks_uri=env["ABC_OIDC_JWKS_URI"])
    # Binding to all interfaces is permitted ONLY because hosting is private-service.
    # An environment variable by itself does not enforce network isolation.
    return ThreadingHTTPServer(("0.0.0.0", port), handler_factory(store, None, verifier))


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

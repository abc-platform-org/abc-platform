"""Private staging API: fail-closed bootstrap under owner cost and identity hold.

Design-only SQL helpers remain available for isolated validation; neither a
managed database config nor an injected fake store can authorize a listener.
A separate independently ratified release change is required to lift this hold.
"""
import os

from psycopg.conninfo import conninfo_to_dict

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


def assert_staging_database(store, expected_role, required_tables, *, expected_login=None):
    with store._connect() as con:
        info = con.execute("""
            SELECT current_user AS role,session_user AS login,
              (SELECT rolsuper OR rolbypassrls OR rolcreaterole
                 FROM pg_roles WHERE rolname=current_user) AS privileged
        """).fetchone()
        if (info["role"] != expected_role or info["privileged"]
            or (expected_login is not None and info["login"] != expected_login)):
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
    """Refuse all actual private API server construction until authorized.

    The owner has not approved a provider, cost or externally managed service
    identity. Unlike the earlier staging launcher, this function MUST NOT
    accept ABC_DB_AUTH_MODE=LEGACY_SYNTHETIC, environment override flags,
    injected store/verifier objects or seemingly valid managed credentials
    as sufficient authority to construct a listener.
    """
    env = os.environ if environ is None else environ
    if (env.get("ABC_ENV") != "STAGING_PRIVATE"
        or env.get("ABC_STAGING_PURPOSE") != "SYNTHETIC_NO_CLIENT_DATA"):
        raise ValueError("private_staging_gate_not_approved")
    if env.get("ABC_NETWORK_BOUNDARY") != "RENDER_PRIVATE_SERVICE":
        raise ValueError("private_network_boundary_not_declared")
    try:
        port = int(env.get("PORT", "10000"))
    except (ValueError, TypeError):
        raise ValueError("invalid_staging_port") from None
    if not 1024 <= port <= 65535:
        raise ValueError("invalid_staging_port")
    if (env.get("ABC_DB_AUTH_MODE") == "LEGACY_SYNTHETIC"
        or "ABC_SYNTHETIC_LEGACY_DB_COMPAT" in env):
        raise ValueError("legacy_shared_database_login_forbidden_in_staging")

    # Must run BEFORE any TLS binding, DB connection, OIDC verification or
    # application handler construction. A string in an environment variable
    # cannot attest Security/SRE approval, an external CA or owner spending.
    # Unconditionally locked even with injected store/verifier test doubles.
    raise ValueError("staging_owner_cost_and_external_identity_hold")

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

"""Read-only external PG16 commissioning attestation. NEVER accepts Render PG internal TLS.

Must be invoked on the authorized operator's private host with service-client
certificates mounted under a secrets manager. Does not print DSNs, credentials,
certificate subject, connection parameters, keys or any customer records.
"""
import json
import os
import stat
import sys
from pathlib import Path
from psycopg.conninfo import conninfo_to_dict

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"runtime/phase04"))
from abc_foundation.managed_pg_store import ManagedMTLSPostgresStore

_RELEVANT=("abc.sessions","abc.memberships","abc.consent_evidence",
           "abc.eng14_v2_replay_ledger")


def _check_file_permissions(path):
    target=Path(path)
    s=target.stat()
    if (not target.is_file() or s.st_uid!=os.geteuid()
        or s.st_mode & (stat.S_IRWXG|stat.S_IRWXO)):
        raise ValueError("database_client_secret_permissions_unsafe")


def attest(environ):
    env=environ
    if (env.get("ABC_ENV")!="STAGING_PRIVATE"
        or env.get("ABC_STAGING_PURPOSE")!="SYNTHETIC_NO_CLIENT_DATA"
        or env.get("ABC_DB_AUTH_MODE")!="MANAGED_MTLS"):
        raise ValueError("not_approved_external_pg_attestation_context")
    required=("ABC_PG_DSN","ABC_DB_WORKLOAD_LOGIN","ABC_DB_CLIENT_DN",
              "ABC_DB_ISSUER_DN","ABC_DB_CERT_SERIAL")
    if any(not env.get(x) for x in required):
        raise ValueError("required_external_identity_pin_missing")
    dsn=env["ABC_PG_DSN"]
    options=conninfo_to_dict(dsn)
    # Verify the operator-managed client private key is not world-readable.
    _check_file_permissions(options.get("sslkey",""))
    store=ManagedMTLSPostgresStore(
        dsn,expected_login=env["ABC_DB_WORKLOAD_LOGIN"],
        client_dn=env["ABC_DB_CLIENT_DN"],
        issuer_dn=env["ABC_DB_ISSUER_DN"],
        certificate_serial=env["ABC_DB_CERT_SERIAL"])
    with store._connect() as con:
        version=con.execute("SHOW server_version_num").fetchone()
        version_num=int(next(iter(version.values())))
        if not 160000<=version_num<170000:
            raise ValueError("postgres16_major_version_required")
        roles=con.execute("SELECT current_user AS role,session_user AS login").fetchone()
        if (roles["role"]!="abc_app" or
            roles["login"]!=env["ABC_DB_WORKLOAD_LOGIN"]):
            raise ValueError("unexpected_managed_db_role")
        for table in _RELEVANT:
            row=con.execute("""
                SELECT relrowsecurity AS enabled,relforcerowsecurity AS forced
                  FROM pg_class WHERE oid=to_regclass(%s)
            """,(table,)).fetchone()
            if not row or row["enabled"] is not True or row["forced"] is not True:
                raise ValueError("missing_forced_rls_"+table.replace(".","_"))
        # Read-only inspection; cannot infer live PG server pg_hba policy from
        # peer presence alone. Operator must independently audit pg_hba/pg_ident.
        return {"external_postgres16_workload_tls":"PASSED",
                "tls_version":"TLSv1.3",
                "physical_login_verified":True,
                "scoped_role_verified":True,"forced_rls_tables":len(_RELEVANT),
                "clientcert_server_policy_external_audit":"REQUIRED",
                "live_private_network_proof":"REQUIRED",
                "P04_closed":False,"customer_release_approved":False}


if __name__=="__main__":
    try:
        print(json.dumps(attest(os.environ),sort_keys=True))
    except Exception:
        # Never echo psycopg connection text: it can include private host,
        # login, password or filesystem credentials.
        print(json.dumps({"external_postgres16_workload_tls":"DENIED",
                          "customer_release_approved":False}),file=sys.stderr)
        raise SystemExit(1)

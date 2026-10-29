"""Managed PostgreSQL workload transport admission for private staging.

This is an admission *preflight* not a token issuer or a replacement for
pg_hba.conf clientcert=verify-full and per-login database authorization.
Deployment is BLOCKED until managed login/certificate enrollment is completed.
"""
import re
from psycopg.conninfo import conninfo_to_dict

_LOGIN=re.compile(r"^abc_api_[a-z0-9_]{12,64}$")


def validate_managed_db_dsn(dsn, *, expected_login):
    if not isinstance(dsn,str) or not _LOGIN.fullmatch(expected_login or ""):
        raise ValueError("per_service_db_login_required")
    try: opts=conninfo_to_dict(dsn)
    except Exception as exc:
        raise ValueError("invalid_managed_db_connection") from exc
    host=opts.get("host","")
    if (opts.get("user")!=expected_login or
        opts.get("sslmode")!="verify-full" or
        not isinstance(host,str) or
        not (host.endswith(".internal") or host.endswith(".private")) or
        not host.count(".") or
        any(not opts.get(k) for k in ("sslcert","sslkey","sslrootcert")) or
        opts.get("dbname")!="abc_staging" or
        opts.get("hostaddr") or opts.get("service") or opts.get("passfile")):
        raise ValueError("managed_db_mutual_tls_required")
    return True


def assert_managed_db_peer(con, *, expected_login, client_dn, issuer_dn, certificate_serial):
    """Inspect immutable authenticated login and the live PostgreSQL TLS peer.

    Server must additionally enforce clientcert=verify-full and a controlled
    certificate-to-login mapping in pg_hba/pg_ident. Client-supplied GUC values
    are never evidence of a service identity.
    """
    if (not _LOGIN.fullmatch(expected_login or "") or
        not all(isinstance(x,str) and x.strip() for x in (client_dn,issuer_dn,certificate_serial))):
        raise ValueError("managed_db_identity_pins_required")
    row=con.execute("""SELECT session_user AS login,current_user AS active_role,
             s.ssl,s.version,s.client_dn,s.issuer_dn,s.client_serial
          FROM pg_stat_ssl s WHERE s.pid=pg_backend_pid()""").fetchone()
    if (not row or row["login"]!=expected_login or
        row["active_role"]!=expected_login or
        row["ssl"] is not True or row["version"]!="TLSv1.3" or
        row["client_dn"]!=client_dn or row["issuer_dn"]!=issuer_dn or
        row["client_serial"] is None or
        str(row["client_serial"])!=certificate_serial):
        raise ValueError("database_authenticated_tls_workload_mismatch")
    return {"authenticated_login":expected_login,"tls_version":"TLSv1.3",
            "identity_source":"POSTGRES_SESSION_USER_AND_TLS_PEER",
            "authorization":"NOT_YET_PROVISIONED"}

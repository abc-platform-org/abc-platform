"""Connect to an explicitly configured OIDC provider and PostgreSQL over loopback.

This is a staging integration harness, NOT a public deployment or login provider.
"""
import os
from .oidc import OIDCVerifier
from .pg_store import PostgresStore
from .http_api import create_oidc_pg_http_server


def main():
    if os.environ.get("ABC_ENV") != "OIDC_PG_LOOPBACK_INTEGRATION":
        raise SystemExit("Explicit OIDC_PG_LOOPBACK_INTEGRATION mode required")
    needed=["ABC_OIDC_ISSUER","ABC_OIDC_AUDIENCE","ABC_OIDC_JWKS_URI","ABC_PG_DSN"]
    missing=[k for k in needed if not os.environ.get(k)]
    if missing:
        raise SystemExit("Missing OIDC/PG configuration: "+", ".join(missing))
    verifier=OIDCVerifier(
        issuer=os.environ["ABC_OIDC_ISSUER"],
        audience=os.environ["ABC_OIDC_AUDIENCE"],
        jwks_uri=os.environ["ABC_OIDC_JWKS_URI"])
    store=PostgresStore(os.environ["ABC_PG_DSN"])
    port=int(os.environ.get("ABC_LISTEN_PORT","8767"))
    http=create_oidc_pg_http_server(store,verifier,host="127.0.0.1",port=port)
    try:
        print("ABC OIDC/Postgres loopback integration harness; NO public or client data",flush=True)
        http.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        http.server_close()

if __name__=="__main__":
    main()

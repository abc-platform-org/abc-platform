"""Launch a *single engine* as an independent local-only mTLS service process.

Real hosted deployment awaits independently approved private network, managed
certificate authority, workload issuer and service secret lifecycle.
"""
import os
import signal
from .isolated_engine_service import ENGINES
from .private_engine_transport import private_engine_server
from .service_mesh_identity import BoundEngineIdentity


def configure_private_engine_service(env=None):
    env=os.environ if env is None else env
    local=(env.get("ABC_ENV")=="LOCAL_INTEGRATION_ONLY"
           and env.get("ABC_NETWORK_BOUNDARY")=="LOOPBACK_ONLY")
    managed_private=(env.get("ABC_ENV")=="STAGING_PRIVATE"
           and env.get("ABC_NETWORK_BOUNDARY")=="RENDER_PRIVATE_SERVICE"
           and env.get("ABC_RENDER_SERVICE_KIND")=="PRIVATE"
           and env.get("ABC_STAGING_PURPOSE")=="SYNTHETIC_NO_CLIENT_DATA")
    if (not (local or managed_private)
        or env.get("ABC_ENGINE_SYNTHETIC_ONLY")!="true"):
        raise ValueError("private_synthetic_mtls_only")
    engine=env.get("ABC_ENGINE_ID")
    caller=env.get("ABC_CALLER_ENGINE_ID")
    consumer=env.get("ABC_ENGINE_CONSUMER_ID")
    if engine not in ENGINES or caller not in (*ENGINES,"ENG-03") or caller==engine:
        raise ValueError("distinct_engine_mtls_roles_required")
    if not isinstance(consumer,str) or not 3<=len(consumer)<=96:
        raise ValueError("consumer_binding_required")
    try: port=int(env.get("ABC_ENGINE_PORT","0"))
    except (ValueError,TypeError):raise ValueError("invalid_engine_port") from None
    if not 1024<=port<=65535:
        raise ValueError("nonprivileged_private_port_required")
    required=("ABC_TLS_CERT_FILE","ABC_TLS_KEY_FILE","ABC_TLS_CA_FILE",
              "ABC_WORKLOAD_ISSUER","ABC_WORKLOAD_JWKS_URL")
    if any(not env.get(k) for k in required):
        raise ValueError("externally_managed_tls_and_issuer_required")
    verifier=BoundEngineIdentity(issuer=env["ABC_WORKLOAD_ISSUER"],
       audience="abc-engine:"+engine,jwks_uri=env["ABC_WORKLOAD_JWKS_URL"])
    return private_engine_server(
       host="0.0.0.0" if managed_private else "127.0.0.1",
       managed_private=managed_private,port=port,target_engine=engine,
       caller_engine=caller,consumer_id=consumer,
       certfile=env["ABC_TLS_CERT_FILE"],keyfile=env["ABC_TLS_KEY_FILE"],
       ca_file=env["ABC_TLS_CA_FILE"],verifier=verifier)


def main():
    server=configure_private_engine_service()
    def shutdown(*_):server.shutdown()
    signal.signal(signal.SIGTERM,shutdown)
    try:server.serve_forever(poll_interval=0.2)
    finally:server.server_close()


if __name__=="__main__":
    main()

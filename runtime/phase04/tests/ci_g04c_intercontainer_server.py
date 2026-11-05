"""Disposable CI-only server: actual ABC engine dispatch over TLS1.3 mTLS.

Runs inside a dedicated Docker container on a Docker --internal network.
Uses only an ephemeral CI CA and an offline public JWT verification key.
It is NOT managed PKI, hosted private networking, or production authority.
"""
import os
from pathlib import Path
from types import SimpleNamespace

from cryptography.hazmat.primitives import serialization

from abc_foundation.private_engine_transport import private_engine_server
from abc_foundation.service_mesh_identity import BoundEngineIdentity


class OfflineTestJWKS:
    def __init__(self, key):
        self.key = key

    def get_signing_key_from_jwt(self, unused_token):
        return SimpleNamespace(key=self.key)


def main():
    expected = {
        "ABC_ENV": "LOCAL_INTEGRATION_ONLY",
        "ABC_NETWORK_BOUNDARY": "CI_DOCKER_INTERNAL",
        "ABC_ENGINE_SYNTHETIC_ONLY": "true",
        "ABC_CI_MTLS_TEST_ONLY": "true",
    }
    if any(os.environ.get(key) != value for key, value in expected.items()):
        raise SystemExit("ci_disposable_private_mesh_required")
    engine = os.environ["ABC_ENGINE_ID"]
    caller = os.environ["ABC_CALLER_ENGINE_ID"]
    if (engine, caller) not in (
        ("ENG-04", "ENG-03"),
        ("ENG-05", "ENG-04"),
        ("ENG-06", "ENG-05"),
    ):
        raise SystemExit("noncanonical_test_engine_link")
    key = serialization.load_pem_public_key(
        Path("/run/issuer/public.pem").read_bytes()
    )
    issuer = "https://issuer.abc-ci.example"
    verifier = BoundEngineIdentity(
        issuer=issuer,
        audience="abc-engine:" + engine,
        jwks_uri=issuer + "/.well-known/jwks.json",
        jwks_client=OfflineTestJWKS(key),
    )
    server = private_engine_server(
        host="0.0.0.0",
        port=int(os.environ["ABC_ENGINE_PORT"]),
        target_engine=engine,
        caller_engine=caller,
        consumer_id="ci-pipeline-worker",
        certfile="/run/engine/cert.pem",
        keyfile="/run/engine/key.pem",
        ca_file="/run/trust/ca.pem",
        verifier=verifier,
        managed_private=True,
    )
    try:
        print("ABC_CI_MTLS_READY:" + engine, flush=True)
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

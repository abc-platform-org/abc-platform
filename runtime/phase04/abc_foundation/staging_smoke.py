"""Synthetic-only staging private-network smoke probe. Never accepts a bearer token.

Run from an approved Render private-network shell, not a public CI runner.
This is an early rollout guard; it does not validate real identity or clients.
"""
import json
import os
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def check_private_url(value):
    if not isinstance(value, str):
        raise ValueError("private_service_url_required")
    parsed=urlsplit(value)
    host=parsed.hostname
    if (parsed.scheme != "http" or not host or "." in host or ":" in host
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ("","/") or host in ("localhost","127.0.0.1")
            or not host.startswith("abc-p04-private-api-") or parsed.port not in (None,10000)):
        raise ValueError("only_private_Render_internal_hostport_allowed")
    return value.rstrip("/")


def smoke(private_url, transport=urlopen):
    base=check_private_url(private_url)
    status_body={}
    for route, method, expected in (("/healthz","GET",200),("/v1/consultations","POST",401)):
        req=Request(base+route,method=method)
        try:
            with transport(req, timeout=5) as resp:
                code=resp.status
                body=resp.read(4096)
        except HTTPError as error:
            code=error.code
            body=error.read(4096)
        if code != expected:
            raise RuntimeError("unexpected_smoke_response_"+route)
        try:
            payload=json.loads(body)
        except (ValueError,UnicodeError):
            raise RuntimeError("invalid_smoke_json_"+route) from None
        if route=="/healthz" and payload.get("capability")!="OIDC_PG_LOOPBACK":
            raise RuntimeError("wrong_staging_runtime_capability")
        if route=="/v1/consultations" and payload.get("error")!="unauthenticated":
            raise RuntimeError("unauthenticated_request_not_blocked")
        status_body[route]=code
    return status_body


def main():
    if os.getenv("ABC_ENV") != "STAGING_PRIVATE" or os.getenv("ABC_STAGING_PURPOSE")!="SYNTHETIC_NO_CLIENT_DATA":
        raise SystemExit("no_staging_synthetic_approval")
    url=os.getenv("ABC_PRIVATE_API_INTERNAL_URL")
    smoke(url)
    print("PASS: private internal staging health and no-token denial; NO live data tested")


if __name__=="__main__":
    main()

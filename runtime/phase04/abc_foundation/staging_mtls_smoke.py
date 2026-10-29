"""Operator-run synthetic-only HTTPS mutual-TLS smoke for private API.

Never accepts bearer tokens or client/customer records. Requires a real
externally provisioned client cert, key and pinned CA, and must run INSIDE the
approved private network. Not a production-release authorization.
"""
import json
import os
import re
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request,HTTPSHandler,build_opener

from .service_mesh_identity import require_mtls_context

_HOST=re.compile(r"^abc-p04-private-api-synthetic(?:-[a-z0-9]{4,20})?$")


def check_mtls_api_url(value):
    if not isinstance(value,str):
        raise ValueError("approved_private_https_endpoint_required")
    parsed=urlsplit(value)
    if (parsed.scheme!="https" or not parsed.hostname
        or not _HOST.fullmatch(parsed.hostname)
        or parsed.username or parsed.password
        or parsed.path not in ("","/")
        or parsed.query or parsed.fragment or parsed.port!=10000):
        raise ValueError("private_api_mtls_hostname_and_port_required")
    return value.rstrip("/")


def run_mtls_smoke(url,*,client_cert,client_key,root_ca,transport=None):
    base=check_mtls_api_url(url)
    context=require_mtls_context(certificate=client_cert,key=client_key,
                                 ca_file=root_ca,server=False)
    opener=build_opener(HTTPSHandler(context=context))
    def execute(req):
        return opener.open(req,timeout=5) if transport is None else transport(req,5)
    outcomes={}
    for route,method,expected in (
        ("/healthz","GET",200),("/v1/consultations","POST",401)
    ):
        request=Request(base+route,method=method)
        try:
            with execute(request) as resp:
                status=resp.status
                body=resp.read(4096)
        except HTTPError as err:
            status=err.code
            body=err.read(4096)
        if status!=expected:
            raise RuntimeError("private_api_mtls_unexpected_status_"+route)
        try:
            result=json.loads(body)
        except (ValueError,TypeError,UnicodeError):
            raise RuntimeError("private_api_mtls_unreadable_response") from None
        if route=="/healthz" and (result.get("status")!="ok"
                                  or result.get("capability")!="OIDC_PG_LOOPBACK"):
            raise RuntimeError("private_api_mtls_unexpected_capability")
        if route=="/v1/consultations" and result.get("error")!="unauthenticated":
            raise RuntimeError("private_api_mtls_auth_bypass")
        outcomes[route]=status
    return {"evidence":"REAL_PRIVATE_API_MTLS_PROBE_NOT_RELEASE",
            "release_approved":False,"status":outcomes}


def main():
    if (os.getenv("ABC_ENV")!="STAGING_PRIVATE" or
        os.getenv("ABC_STAGING_PURPOSE")!="SYNTHETIC_NO_CLIENT_DATA" or
        os.getenv("ABC_NETWORK_BOUNDARY")!="RENDER_PRIVATE_SERVICE"):
        raise SystemExit("approved_private_synthetic_staging_required")
    names=("ABC_PRIVATE_API_MTLS_URL","ABC_PROBE_CLIENT_CERT_FILE",
           "ABC_PROBE_CLIENT_KEY_FILE","ABC_PROBE_ROOT_CA_FILE")
    if any(not os.getenv(x) for x in names):
        raise SystemExit("externally_managed_probe_tls_required")
    result=run_mtls_smoke(os.environ["ABC_PRIVATE_API_MTLS_URL"],
         client_cert=os.environ["ABC_PROBE_CLIENT_CERT_FILE"],
         client_key=os.environ["ABC_PROBE_CLIENT_KEY_FILE"],
         root_ca=os.environ["ABC_PROBE_ROOT_CA_FILE"])
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()

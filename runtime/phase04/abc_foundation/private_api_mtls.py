"""Mutual TLS 1.3 admission for the PRIVATE staging HTTP API.

The issuer/CA is provisioned and rotated by an external operator. A successful
TLS handshake alone is not a bearer principal: the verified client certificate
URI SAN is additionally pinned to an approved GATEWAY principal only.
Legacy per-engine HTTP caller identities and the new canonical engine mesh
are separate trust surfaces: never alias either into this gateway allowlist.
End-user OIDC verification and PostgreSQL RLS remain independent requirements.
"""
import re
from http.server import ThreadingHTTPServer

from .service_mesh_identity import require_mtls_context

_GATEWAY_URI=re.compile(
    r"^spiffe://abc\.internal/gateway/[A-Za-z0-9-]{3,96}$"
)


def _require_gateway_callers(allowed):
    """Fail closed even if a caller bypasses the environment parser.

    Legacy /engXX/name and canonical /staging/eng-XX service identities
    belong to other trust domains and cannot authenticate to this HTTP API.
    """
    if (not isinstance(allowed,frozenset) or
        not 1<=len(allowed)<=16 or
        any(type(uri) is not str or _GATEWAY_URI.fullmatch(uri) is None
            for uri in allowed)):
        raise ValueError("api_gateway_only_client_identity_required")
    return allowed


def parse_allowed_private_callers(value):
    if not isinstance(value,str) or not value or len(value)>4096:
        raise ValueError("api_client_certificate_uri_pins_required")
    parts=value.split(",")
    if (len(parts)>16 or not all(x and x==x.strip() and _GATEWAY_URI.fullmatch(x)
                               for x in parts) or len(set(parts))!=len(parts)):
        raise ValueError("api_client_certificate_uri_pins_invalid")
    return _require_gateway_callers(frozenset(parts))


def verify_private_api_client_certificate(cert,allowed):
    # Python's getpeercert() only reports this after successful CA verification.
    # Never accept a CN fallback or multiple identities in one certificate.
    if not isinstance(cert,dict):
        raise ValueError("api_client_certificate_unverifiable")
    _require_gateway_callers(allowed)
    names=cert.get("subjectAltName",())
    if (not isinstance(names,(tuple,list)) or
        len([value for kind,value in names if kind=="URI"])!=1 or
        not all(kind!="URI" or value in allowed for kind,value in names)):
        raise ValueError("api_client_uri_not_approved")
    uris=[value for kind,value in names if kind=="URI"]
    if uris[0] not in allowed:
        raise ValueError("api_client_uri_not_approved")
    return uris[0]


class BoundMTLSHTTPServer(ThreadingHTTPServer):
    daemon_threads=True

    def __init__(self,address,handler,*,context,allowed_client_uris):
        self.allowed_client_uris=_require_gateway_callers(allowed_client_uris)
        super().__init__(address,handler,bind_and_activate=False)
        try:
            self.server_bind()
            self.socket=context.wrap_socket(self.socket,server_side=True)
            self.server_activate()
        except BaseException:
            self.server_close()
            raise

    def get_request(self):
        sock,address=super().get_request()
        try:
            sock.settimeout(5)
            verify_private_api_client_certificate(
                sock.getpeercert(),self.allowed_client_uris)
            return sock,address
        except BaseException:
            sock.close()
            raise


def create_private_api_server(address,handler,env):
    if env.get("ABC_API_TRANSPORT")!="MTLS_TLS13":
        raise ValueError("api_mutual_tls13_required")
    required=("ABC_API_TLS_CERT_FILE","ABC_API_TLS_KEY_FILE",
              "ABC_API_TLS_CA_FILE","ABC_API_ALLOWED_CLIENT_URIS")
    if any(not env.get(name) for name in required):
        raise ValueError("api_externally_managed_tls_material_required")
    callers=parse_allowed_private_callers(env["ABC_API_ALLOWED_CLIENT_URIS"])
    tls=require_mtls_context(certificate=env["ABC_API_TLS_CERT_FILE"],
          key=env["ABC_API_TLS_KEY_FILE"],ca_file=env["ABC_API_TLS_CA_FILE"],
          server=True)
    return BoundMTLSHTTPServer(address,handler,context=tls,
                               allowed_client_uris=callers)

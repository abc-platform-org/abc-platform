"""Managed-workload compatible verification boundary for internal engine calls.

Credentials/certificates are injected from an EXTERNAL credential provider.
This module does NOT create a CA, sign tokens, enroll machines or deploy a
real mesh. Bound RS256 JWT and mTLS certificate must BOTH verify.
"""
import hashlib
import re
import ssl
import uuid
from datetime import datetime,timezone
from urllib.parse import urlparse
from cryptography import x509
from cryptography.x509.oid import ExtensionOID
import jwt
from jwt import PyJWKClient
from .store import DomainError

_ENGINES=frozenset(f"ENG-{i:02d}" for i in range(1,20))
_SUB=re.compile(r"^spiffe://abc\.internal/(eng(?:0[1-9]|1[0-9]))/([a-zA-Z0-9-]{3,96})$")
class BoundEngineIdentity:
    def __init__(self,*,issuer,audience,jwks_uri,jwks_client=None,clock=None):
        iss=urlparse(issuer); src=urlparse(jwks_uri)
        if (iss.scheme!="https" or not iss.hostname or src.scheme!="https"
            or src.hostname!=iss.hostname or iss.username or iss.password
            or iss.query or iss.fragment or src.username or src.password
            or src.query or src.fragment or
            not isinstance(audience,str) or not audience.startswith("abc-engine:")):
            raise ValueError("pinned_managed_issuer_and_dedicated_audience_required")
        self.issuer=issuer;self.audience=audience
        self.jwks=jwks_client or PyJWKClient(jwks_uri,cache_keys=False,
             cache_jwk_set=True,lifespan=60,timeout=3)
        self.clock=clock or (lambda:datetime.now(timezone.utc))

    def verify(self,token,peer_der,*,expected_engine,expected_consumer):
        if (expected_engine not in _ENGINES or not isinstance(peer_der,bytes)
            or len(peer_der)>16384 or not peer_der
            or not isinstance(token,str) or len(token)>8192 or token.count(".")!=2):
            raise DomainError(401,"workload_mutual_identity_required")
        try:
            header=jwt.get_unverified_header(token)
            if header.get("alg")!="RS256" or header.get("crit") or not isinstance(header.get("kid"),str):
                raise ValueError("algorithm")
            cert=x509.load_der_x509_certificate(peer_der)
            uris=cert.extensions.get_extension_for_oid(
                ExtensionOID.SUBJECT_ALTERNATIVE_NAME).value.get_values_for_type(x509.UniformResourceIdentifier)
            expected_uri=f"spiffe://abc.internal/{expected_engine.lower().replace('-','')}/{expected_consumer}"
            if uris!=[expected_uri] or _SUB.fullmatch(expected_uri) is None:
                raise ValueError("unexpected_certificate_identity")
            now=self.clock()
            if now.tzinfo is None:raise ValueError("untrusted_clock")
            utc=now.astimezone(timezone.utc)
            if utc<cert.not_valid_before_utc or utc>=cert.not_valid_after_utc:
                raise ValueError("certificate_not_current")
            key=self.jwks.get_signing_key_from_jwt(token)
            claims=jwt.decode(token,key.key,algorithms=["RS256"],
                  audience=self.audience,issuer=self.issuer,leeway=5,
                  options={"require":["iss","aud","iat","nbf","exp","jti","sub",
                                      "engine_id","consumer_id","token_use","cnf"]})
            now_sec=int(utc.timestamp())
            iat,nbf,exp=(claims.get(k) for k in ("iat","nbf","exp"))
            if (any(type(k) is not int for k in (iat,nbf,exp)) or
                iat>now_sec+5 or nbf>now_sec+5 or exp<=now_sec-5
                or exp-iat>120 or exp<=iat or
                claims.get("engine_id")!=expected_engine or
                claims.get("consumer_id")!=expected_consumer or
                claims.get("sub")!=expected_uri or
                claims.get("token_use")!="service" or
                not isinstance(claims.get("cnf"),dict) or
                claims["cnf"].get("x5t#S256")!=
                   __import__("base64").urlsafe_b64encode(
                     hashlib.sha256(peer_der).digest()).rstrip(b"=").decode("ascii") or
                str(uuid.UUID(claims.get("jti","")))!=claims["jti"]):
                raise ValueError("token_not_bound_to_cert_or_identity")
            return {"verified":True,"engine_id":expected_engine,
                    "consumer_id":expected_consumer,"subject":expected_uri,
                    "issuer":self.issuer,"token_id":claims["jti"],
                    "cert_sha256":hashlib.sha256(peer_der).hexdigest()}
        except (jwt.PyJWTError,ValueError,KeyError,TypeError,OverflowError,
                x509.ExtensionNotFound) as exc:
            raise DomainError(401,"mutual_workload_authentication_failed") from exc


def require_mtls_context(*,certificate,key,ca_file,server):
    if not all(isinstance(x,str) and x for x in (certificate,key,ca_file)):
        raise ValueError("externally_provisioned_tls_material_required")
    ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER if server else ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version=ssl.TLSVersion.TLSv1_3
    ctx.verify_mode=ssl.CERT_REQUIRED
    ctx.check_hostname=not server
    ctx.load_verify_locations(cafile=ca_file)
    ctx.load_cert_chain(certfile=certificate,keyfile=key)
    return ctx

"""Strict bearer service-to-service identity verifier for private ENG01 ingress.

External managed workload issuer/JWKS is required at cloud release. This code
verifies token possession but never treats token-claimed tenant/role/permission
as authorization: admin-managed PostgreSQL grants decide that separately.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid
from urllib.parse import urlparse

import jwt
from jwt import PyJWKClient

from .oidc import IdentityError


@dataclass(frozen=True)
class WorkloadPrincipal:
    issuer: str
    subject: str
    engine_id: str
    token_id: str


class WorkloadVerifier:
    """Pinned asymmetric JWKS, no client roles or mint-token endpoint."""
    def __init__(self, *, issuer, audience, jwks_uri, jwks_client=None, clock=None):
        iss=urlparse(issuer)
        keys=urlparse(jwks_uri)
        if not isinstance(audience,str) or audience!="abc-eng01-internal":
            raise ValueError("dedicated_engine_audience_required")
        if (iss.scheme!="https" or not iss.hostname or iss.username or iss.password
              or iss.query or iss.fragment or keys.scheme!="https"
              or keys.hostname!=iss.hostname or keys.username or keys.password
              or keys.query or keys.fragment):
            raise ValueError("pinned_https_service_issuer_and_jwks_required")
        self.issuer,self.audience=issuer,audience
        self.clock=clock or (lambda:datetime.now(timezone.utc))
        self.keys=jwks_client or PyJWKClient(jwks_uri,cache_keys=False,
             cache_jwk_set=True,lifespan=120,timeout=3,cooldown_duration=30)

    def verify(self, authorization):
        if not isinstance(authorization,str) or not authorization.startswith("Bearer "):
            raise IdentityError("workload_bearer_required")
        token=authorization[7:]
        if len(token)>8192 or token.count(".")!=2:
            raise IdentityError("invalid_workload_token")
        try:
            header=jwt.get_unverified_header(token)
            if (header.get("alg")!="RS256" or not isinstance(header.get("kid"),str)
                or not 1<=len(header["kid"])<=128 or header.get("crit")):
                raise IdentityError("invalid_workload_algorithm")
            key=self.keys.get_signing_key_from_jwt(token)
            claims=jwt.decode(token,key.key,algorithms=["RS256"],
                issuer=self.issuer,audience=self.audience,leeway=10,
                options={"require":["iss","aud","sub","iat","nbf","exp","jti",
                                    "token_use","engine_id"]})
        except IdentityError:
            raise
        except (jwt.PyJWTError,KeyError,TypeError,ValueError,OverflowError,OSError) as exc:
            raise IdentityError("workload_token_rejected") from exc
        now=int(self.clock().timestamp())
        iat,exp,nbf=(claims.get(x) for x in ("iat","exp","nbf"))
        if (any(type(x) is not int for x in (iat,exp,nbf))
            or iat>now+10 or nbf>now+10 or exp<=now-10
            or exp-iat>120 or exp<=iat):
            raise IdentityError("invalid_workload_lifetime")
        if (claims.get("token_use")!="service"
            or claims.get("engine_id")!="ENG-02"
            or claims.get("sub")!="svc:abc-eng02"):
            raise IdentityError("workload_engine_identity_mismatch")
        try:
            tid=str(uuid.UUID(claims["jti"]))
        except (ValueError,TypeError,AttributeError):
            raise IdentityError("invalid_workload_token_id") from None
        if tid!=claims["jti"]:
            raise IdentityError("invalid_workload_token_id")
        return WorkloadPrincipal(self.issuer,claims["sub"],"ENG-02",tid)


class ENG01InternalIngress:
    """Only boundary that converts TWO signed bearers to a typed write.

    The ENG01 writer still verifies DB-side human membership and admin engine
    grants in the same SQL transaction as answer/outbox.
    """
    def __init__(self, *, user_verifier, service_verifier, writer):
        if any(x is None for x in (user_verifier,service_verifier,writer)):
            raise ValueError("verifiers_and_transactional_writer_required")
        self.user_verifier=user_verifier
        self.service_verifier=service_verifier
        self.writer=writer

    def record_synthetic_answer(self, *, user_authorization,
                                service_authorization, command):
        try:
            human=self.user_verifier.verify(user_authorization)
            workload=self.service_verifier.verify(service_authorization)
        except IdentityError as exc:
            from .store import DomainError
            raise DomainError(401,"verified_dual_identity_required") from exc
        # Neither principal nor tenant may be supplied in the HTTP JSON body.
        return self.writer.record_synthetic_answer(human,workload,command)

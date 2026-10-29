"""Strict asymmetric OpenID Connect access-token verification (no login/session issuance).

Claims identify a principal; ALL ABC role, tenant and branch permissions must come
from the server-side membership registry, not user-controlled HTTP headers or claims.
Never build JWKS URL from a token or from an untrusted issuer claim.
"""
from dataclasses import dataclass
from urllib.parse import urlparse

import jwt
from jwt import PyJWKClient


class IdentityError(Exception):
    pass


@dataclass(frozen=True)
class Principal:
    subject: str
    issuer: str


class OIDCVerifier:
    def __init__(self, *, issuer, audience, jwks_uri, jwks_client=None):
        if not all(isinstance(x, str) and x for x in (issuer, audience, jwks_uri)):
            raise ValueError("explicit OIDC issuer, audience and JWKS URI required")
        iss, keys = urlparse(issuer), urlparse(jwks_uri)
        if (iss.scheme != "https" or not iss.netloc or iss.username or iss.password or iss.query
                or keys.scheme != "https" or not keys.netloc or keys.username or keys.password
                or keys.fragment or keys.query or keys.hostname != iss.hostname):
            raise ValueError("HTTPS issuer and same-host pinned JWKS required")
        if issuer.rstrip("/") != issuer and not issuer.endswith("/"):
            raise ValueError("invalid issuer")
        self.issuer, self.audience = issuer, audience
        # No per-signing-key indefinite cache: respect key rotation via short JWKS TTL.
        self.keys = jwks_client or PyJWKClient(
            jwks_uri, cache_keys=False, cache_jwk_set=True, lifespan=120,
            timeout=3, cooldown_duration=30)

    def verify(self, authorization):
        if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
            raise IdentityError("authentication_required")
        token = authorization[7:]
        if len(token) > 8192 or token.count(".") != 2 or not token.strip():
            raise IdentityError("invalid_token")
        try:
            header = jwt.get_unverified_header(token)
            if (header.get("alg") != "RS256" or not isinstance(header.get("kid"), str)
                    or not 1 <= len(header["kid"]) <= 128 or header.get("crit")):
                raise IdentityError("unsupported_token")
            key = self.keys.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token, key.key, algorithms=["RS256"], issuer=self.issuer,
                audience=self.audience, leeway=15,
                options={"require": ["exp", "iat", "nbf", "iss", "aud", "sub"],
                         "verify_signature": True, "verify_exp": True, "verify_nbf": True,
                         "verify_iat": True, "verify_iss": True, "verify_aud": True},
            )
        except IdentityError:
            raise
        except (jwt.PyJWTError, ValueError, TypeError, KeyError, OverflowError, OSError) as exc:
            raise IdentityError("invalid_or_expired_token") from exc
        subject = claims.get("sub")
        if not isinstance(subject, str) or not 1 <= len(subject) <= 128:
            raise IdentityError("invalid_subject")
        # Claim roles, tenant_id and branch_ids are intentionally ignored.
        return Principal(subject=subject, issuer=self.issuer)

"""Local integration verifier. Never an identity provider or production authorization."""
import base64
import hashlib
import hmac
import json
import time


class AuthError(Exception):
    pass


def _decode(value):
    if not isinstance(value, str) or not value or len(value) > 8192:
        raise AuthError("invalid_token")
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        return raw
    except (ValueError, base64.binascii.Error):
        raise AuthError("invalid_token") from None


def verify_bearer(header, secret, now=None):
    """HS256 only; confined to a loopback integration harness by server.py."""
    if not isinstance(header, str) or not header.startswith("Bearer "):
        raise AuthError("authentication_required")
    token = header[7:]
    parts = token.split(".")
    if len(parts) != 3:
        raise AuthError("invalid_token")
    signed = (parts[0] + "." + parts[1]).encode("ascii", errors="strict")
    expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, _decode(parts[2])):
        raise AuthError("invalid_signature")
    try:
        head = json.loads(_decode(parts[0]))
        payload = json.loads(_decode(parts[1]))
    except (UnicodeError, ValueError, TypeError):
        raise AuthError("invalid_claims") from None
    if not isinstance(head, dict) or head.get("alg") != "HS256" or head.get("typ") != "JWT":
        raise AuthError("unsupported_token")
    if not isinstance(payload, dict):
        raise AuthError("invalid_claims")
    t = time.time() if now is None else now
    # These are local-fixture trust anchors, NOT a replacement for managed OIDC.
    if payload.get("iss") != "abc-local-integration" or payload.get("aud") != "abc-foundation":
        raise AuthError("invalid_issuer_or_audience")
    for k in ("exp", "iat", "nbf"):
        if type(payload.get(k)) not in (int, float):
            raise AuthError("invalid_claims")
    if not (payload["iat"] <= t + 30 and payload["nbf"] <= t and t < payload["exp"] <= t + 3600):
        raise AuthError("token_expired_or_invalid")
    if not all(isinstance(payload.get(k), str) and 0 < len(payload[k]) <= 128 for k in ("sub", "tenant_id")):
        raise AuthError("invalid_identity")
    roles, branches = payload.get("roles"), payload.get("branch_ids")
    if not isinstance(roles, list) or "SPECIALIST" not in roles or len(roles) > 8 or not all(isinstance(x, str) for x in roles):
        raise AuthError("specialist_required")
    if not isinstance(branches, list) or not branches or len(branches) > 100 or not all(isinstance(x, str) and 0 < len(x) <= 128 for x in branches):
        raise AuthError("invalid_branch_scope")
    return {"sub": payload["sub"], "tenant_id": payload["tenant_id"], "roles": tuple(roles), "branch_ids": tuple(branches)}


def mint_test_token(secret, sub, tenant, branches, *, roles=None, now=None):
    """Used only by offline unit tests; never exposed as an HTTP route."""
    t = int(time.time() if now is None else now)
    header = {"alg": "HS256", "typ": "JWT"}
    body = {"iss": "abc-local-integration", "aud": "abc-foundation", "sub": sub,
            "tenant_id": tenant, "branch_ids": branches, "roles": roles or ["SPECIALIST"],
            "iat": t - 1, "nbf": t - 1, "exp": t + 600}
    enc = lambda d: base64.urlsafe_b64encode(json.dumps(d, separators=(",", ":"), sort_keys=True).encode()).rstrip(b"=").decode()
    message = enc(header) + "." + enc(body)
    sig = base64.urlsafe_b64encode(hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
    return message + "." + sig

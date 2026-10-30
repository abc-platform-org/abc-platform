"""Fail-closed HTTP adapter exposing two exact v1 routes plus internal checkpoint POC."""
import json
import re
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .auth import AuthError, verify_bearer
from .oidc import IdentityError
from .store import DomainError

SESSION_RE = re.compile(r"^/v1/consultations/([a-f0-9-]{36})$")
COMMAND_RE = re.compile(r"^/_foundation/v0/consultations/([a-f0-9-]{36})/(pause|resume)$")
MEDIA_RE = re.compile(r"^/v1/consultations/([a-f0-9-]{36})/media$")
MAX_BODY = 4096


def handler_factory(store, signing_secret, identity_verifier=None):
    class Handler(BaseHTTPRequestHandler):
        server_version = "ABC-Foundation-Local/0.1"
        sys_version = ""

        def log_message(self, fmt, *args):
            # Do not log authorization headers, request payload, or client identifiers.
            return

        def _json(self, status, payload):
            raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _actor(self):
            try:
                if identity_verifier is not None:
                    return identity_verifier.verify(self.headers.get("Authorization"))
                return verify_bearer(self.headers.get("Authorization"), signing_secret)
            except (AuthError, IdentityError, UnicodeError, ValueError):
                raise DomainError(401, "unauthenticated") from None

        def _body(self):
            if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
                raise DomainError(415, "json_required")
            cl = self.headers.get("Content-Length")
            if cl is None or not cl.isascii() or not cl.isdigit() or not 0 < int(cl) <= MAX_BODY:
                raise DomainError(400, "invalid_body_length")
            try:
                data = json.loads(self.rfile.read(int(cl)))
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise DomainError(400, "malformed_json") from None
            if not isinstance(data, dict):
                raise DomainError(400, "json_object_required")
            return data

        def _expected(self):
            v = self.headers.get("X-Expected-State-Version")
            if v is None or not v.isascii() or not v.isdigit():
                raise DomainError(400, "expected_version_required")
            return int(v)

        def _attempt(self, action):
            try:
                return action()
            except DomainError as e:
                return self._json(e.status, {"error": e.code, "request_id": str(uuid.uuid4())})
            except Exception:
                # No raw exception or SQL / stack trace is ever returned to the caller.
                return self._json(500, {"error": "internal_failure", "request_id": str(uuid.uuid4())})

        def do_GET(self):
            def action():
                if self.path == "/healthz":
                    return self._json(200, {"status": "ok", "capability": "OIDC_PG_LOOPBACK" if identity_verifier else "LOCAL_INTEGRATION_ONLY"})
                actor = self._actor()
                match = SESSION_RE.fullmatch(self.path)
                if not match:
                    raise DomainError(404, "not_found")
                return self._json(200, store.get(actor, match.group(1)))
            self._attempt(action)

        def do_POST(self):
            def action():
                actor = self._actor()
                if self.path == "/v1/consultations":
                    body = self._body()
                    obj = store.create(actor, body, self.headers.get("Idempotency-Key"))
                    return self._json(200, obj)
                match = COMMAND_RE.fullmatch(self.path)
                if match:
                    body = self._body()
                    if body:
                        raise DomainError(400, "unexpected_command_body")
                    result = store.checkpoint_command(
                        actor, match.group(1), match.group(2),
                        self._expected(), self.headers.get("Idempotency-Key"))
                    return self._json(200, result)
                # This is a deny-first PRECAPTURE CHECK only. No request body
                # or image bytes are read, retained, or sent to a model.
                media = MEDIA_RE.fullmatch(self.path)
                if media:
                    preflight = getattr(store, "authorize_capture_preflight", None)
                    if not callable(preflight):
                        raise DomainError(403, "pre_capture_authority_unavailable")
                    result = preflight(actor, media.group(1), self._expected())
                    if (not isinstance(result, dict)
                            or result.get("consent_checked") is not True
                            or result.get("capture_authorized") is not False
                            or result.get("customer_media_accepted") is not False):
                        raise DomainError(403, "pre_capture_authority_untrusted")
                    raise DomainError(501, "capability_not_implemented")
                # No unverified consent, media, business, or model adapters.
                if self.path.startswith("/v1/"):
                    raise DomainError(501, "capability_not_implemented")
                raise DomainError(404, "not_found")
            self._attempt(action)

    return Handler


def create_http_server(store, secret, host="127.0.0.1", port=0):
    if host not in ("127.0.0.1", "::1"):
        raise ValueError("LOCAL_INTEGRATION_ONLY: non-loopback listen refused")
    if not isinstance(secret, str) or len(secret.encode("utf-8")) < 32:
        raise ValueError("min 32-byte local test signing secret required")
    return ThreadingHTTPServer((host, port), handler_factory(store, secret))



def create_oidc_pg_http_server(store, identity_verifier, host="127.0.0.1", port=0):
    """Real asymmetric OIDC verifier + PostgreSQL memberships, but loopback-only.

    This intentionally is NOT a public ingress. Production reverse proxy/TLS,
    abuse controls, auditing, trusted network and real IdP credentials are pending.
    """
    if host not in ("127.0.0.1", "::1"):
        raise ValueError("OIDC_PG_LOOPBACK: no public bind permitted")
    if identity_verifier is None:
        raise ValueError("verified OIDC configuration required")
    return ThreadingHTTPServer((host, port),
                               handler_factory(store, None, identity_verifier))

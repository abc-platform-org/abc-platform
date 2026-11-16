"""Loopback-only AI Studio integration with a disposable synthetic session store."""

import os
import secrets
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from abc_foundation.auth import mint_test_token
from abc_foundation.http_api import SESSION_RE, handler_factory
from abc_foundation.store import DomainError, Store

PREVIEW = Path(__file__).resolve().parent
STUDIO_DESIGN = PREVIEW.parents[2] / "prototypes" / "abc-ai-studio-v2"
BRANCH = "studio-synthetic-branch"
TENANT = "studio-synthetic-tenant"
SPECIALIST = "studio-synthetic-specialist"
CREATE_PATH = "/v1/consultations"
STATIC_FILES = {
    "/": (PREVIEW / "index.html", "text/html; charset=utf-8"),
    "/session.js": (PREVIEW / "session.js", "text/javascript; charset=utf-8"),
    "/session.css": (PREVIEW / "session.css", "text/css; charset=utf-8"),
    **{
        f"/studio/{file}": (STUDIO_DESIGN / file, content_type)
        for file, content_type in (
            ("index.html", "text/html; charset=utf-8"),
            ("app.js", "text/javascript; charset=utf-8"),
            ("style.css", "text/css; charset=utf-8"),
        )
    },
}


def create_studio_server(database, port=0):
    if os.environ.get("ABC_ENV") != "LOCAL_INTEGRATION_ONLY":
        raise ValueError("studio_preview_requires_local_integration")
    secret = secrets.token_urlsafe(48)
    api_handler = handler_factory(Store(database), secret)

    class StudioHandler(api_handler):
        def _trusted_host(self):
            return self.headers.get_all("Host") == [f"127.0.0.1:{self.server.server_port}"]

        def _actor(self):
            # Only this loopback preview can supply the fixed synthetic identity.
            if self.headers.get_all("X-ABC-Studio-Preview") != ["1"] or "Authorization" in self.headers:
                raise DomainError(401, "unauthenticated")
            origin = self.headers.get_all("Origin", [])
            expected = [f"http://127.0.0.1:{self.server.server_port}"]
            if (origin or self.command == "POST") and origin != expected:
                raise DomainError(403, "origin_forbidden")
            self.headers["Authorization"] = "Bearer " + mint_test_token(secret, SPECIALIST, TENANT, [BRANCH])
            return super()._actor()

        def _body(self):
            body = super()._body()
            if body != {"scope": "IN_SALON_SHARED_SCREEN"}:
                raise DomainError(400, "synthetic_session_request_required")
            return {**body, "branch_id": BRANCH}

        def do_GET(self):
            if not self._trusted_host():
                return self._json(403, {"error": "host_forbidden"})
            if SESSION_RE.fullmatch(self.path):
                return super().do_GET()
            asset = STATIC_FILES.get(self.path)
            if asset is None:
                return self._json(404, {"error": "not_found"})
            filename, content_type = asset
            data = filename.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "SAMEORIGIN")
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if not self._trusted_host():
                return self._json(403, {"error": "host_forbidden"})
            if self.path != CREATE_PATH:
                return self._json(404, {"error": "not_found"})
            return super().do_POST()

    return ThreadingHTTPServer(("127.0.0.1", port), StudioHandler)


def main():
    with TemporaryDirectory(prefix="abc-studio-") as directory:
        database = Path(directory) / "studio.sqlite"
        with create_studio_server(database, int(os.environ.get("ABC_STUDIO_PORT", "8770"))) as server:
            print(f"ABC synthetic AI Studio: http://127.0.0.1:{server.server_port}/", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()

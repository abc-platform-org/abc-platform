"""Local-only network ingress proof for dual-auth ENG01↔ENG02 answer commands.

No public/private cloud listener exists. Production/staging requires separately
approved private ingress, TLS/mTLS and managed IdP deployment. This server
binds only loopback and refuses real client mode.
"""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from urllib.parse import urlsplit

from .store import DomainError

PATH="/_internal/eng01/v0/eng02/answers"
MAX_BODY=16384


def _unique_pairs(pairs):
    result={}
    for k,v in pairs:
        if k in result:
            raise ValueError("duplicate_json_key")
        result[k]=v
    return result


def _reject_constant(value):
    raise ValueError("nonfinite_json_denied")


def make_synthetic_server(ingress, *, environ=None):
    env=os.environ if environ is None else environ
    if (env.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY" or
        env.get("ABC_ENABLE_SYNTHETIC_S2S")!="yes"):
        raise ValueError("local_synthetic_service_only")
    if ingress is None or not callable(getattr(ingress,"record_synthetic_answer",None)):
        raise ValueError("verified_dual_ingress_required")

    class Handler(BaseHTTPRequestHandler):
        protocol_version="HTTP/1.1"
        def log_message(self,*args):
            # Never log credentials, request payload or raw query strings.
            return

        def _send(self,status,payload):
            data=json.dumps(payload,separators=(",",":")).encode()
            self.send_response(status)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",str(len(data)))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Connection","close")
            self.end_headers()
            self.wfile.write(data)
            self.close_connection=True

        def do_POST(self):
            if self.path!=PATH:
                return self._send(404,{"error":"not_found"})
            if self.headers.get("Origin") or self.headers.get("Cookie"):
                return self._send(403,{"error":"browser_traffic_not_allowed"})
            if self.headers.get("Content-Type")!="application/json":
                return self._send(415,{"error":"json_required"})
            if len(self.headers.get_all("Authorization") or [])!=1 or len(self.headers.get_all("X-ABC-Service-Authorization") or [])!=1:
                return self._send(401,{"error":"dual_bearer_required"})
            try:
                raw_length=self.headers.get("Content-Length")
                if raw_length is None or not raw_length.isascii() or not raw_length.isdigit():
                    return self._send(411,{"error":"content_length_required"})
                n=int(raw_length)
                if n<2 or n>MAX_BODY:
                    return self._send(413,{"error":"payload_length_rejected"})
                raw=self.rfile.read(n)
                if len(raw)!=n: return self._send(400,{"error":"short_payload"})
                command=json.loads(raw.decode("utf-8"),object_pairs_hook=_unique_pairs,
                                   parse_constant=_reject_constant)
                result=ingress.record_synthetic_answer(
                    user_authorization=self.headers["Authorization"],
                    service_authorization=self.headers["X-ABC-Service-Authorization"],
                    command=command)
                return self._send(200,result)
            except (UnicodeDecodeError,ValueError,json.JSONDecodeError):
                return self._send(400,{"error":"invalid_json_command"})
            except DomainError as error:
                status=error.status if error.status in (400,401,403,404,409,422,501) else 500
                return self._send(status,{"error":error.code if status!=500 else "internal_error"})
            except Exception:
                # Server never reflects raw database, token or stack-trace detail.
                return self._send(500,{"error":"internal_error"})

        def do_GET(self):
            return self._send(405,{"error":"method_not_allowed"})

    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    assert server.server_address[0]=="127.0.0.1"
    return server

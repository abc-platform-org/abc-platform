"""Optional PRIVATE mTLS network port for separately hosted synthetic engines.

Server listens on loopback only in local integration. For production a managed
identity/CA, per-engine network identity, private mesh and release review are
required. Fail closed if a client certificate or bound signed JWT is missing.
"""
import json
import re
import socket
import socketserver
import struct
from .isolated_engine_service import ENGINES,dispatch
from .service_mesh_identity import require_mtls_context
from .store import DomainError

LIMIT=262144


def _read_frame(sock):
    header=b""
    while len(header)<4:
        data=sock.recv(4-len(header))
        if not data:raise ValueError("missing_length")
        header+=data
    count=struct.unpack("!I",header)[0]
    if not 1<=count<=LIMIT:raise ValueError("oversized_frame")
    chunks=[]; remaining=count
    while remaining:
        chunk=sock.recv(min(remaining,16384))
        if not chunk:raise ValueError("short_frame")
        chunks.append(chunk);remaining-=len(chunk)
    return json.loads(b"".join(chunks))


def _write_frame(sock,item):
    content=json.dumps(item,sort_keys=True,separators=(",",":")).encode()
    if len(content)>LIMIT:raise ValueError("oversized_reply")
    sock.sendall(struct.pack("!I",len(content))+content)


class _Server(socketserver.ThreadingMixIn,socketserver.TCPServer):
    allow_reuse_address=True
    daemon_threads=True
    def get_request(self):
        sock,address=super().get_request()
        try:
            sock.settimeout(4)
            secure=self.context.wrap_socket(sock,server_side=True)
            return secure,address
        except BaseException:
            sock.close()
            raise


class _Handler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            request=_read_frame(self.request)
            if not isinstance(request,dict) or set(request)!={"token","message"}:
                raise DomainError(401,"invalid_mutual_engine_envelope")
            identity=self.server.verifier.verify(
                request["token"],self.request.getpeercert(binary_form=True),
                expected_engine=self.server.caller,
                expected_consumer=self.server.consumer)
            message=request["message"]
            if not isinstance(message,dict) or message.get("consumer_id")!=identity["consumer_id"]:
                raise DomainError(403,"cross_consumer_message")
            response=dispatch(message,self.server.target)
            _write_frame(self.request,response)
        except (DomainError,ValueError,TypeError,KeyError):
            try:_write_frame(self.request,{"error":"engine_request_rejected","release_approved":False})
            except (OSError,ValueError):pass


def private_engine_server(*,host,port,target_engine,caller_engine,consumer_id,
                          certfile,keyfile,ca_file,verifier,managed_private=False):
    # The wildcard listener is ONLY for an externally verified private-only
    # hosting service; mTLS remains mandatory at the application protocol.
    if (not (host=="127.0.0.1" or (managed_private is True and host=="0.0.0.0"))
        or target_engine not in ENGINES or not 0<=port<=65535):
        raise ValueError("local_integration_private_only")
    if caller_engine==target_engine or verifier is None or not isinstance(consumer_id,str):
        raise ValueError("distinct_authenticated_caller_required")
    context=require_mtls_context(certificate=certfile,key=keyfile,ca_file=ca_file,server=True)
    server=_Server((host,port),_Handler)
    server.context=context
    server.verifier=verifier
    server.caller=caller_engine
    server.target=target_engine
    server.consumer=consumer_id
    return server


def send_private_engine_message(*,host,port,server_name,certfile,keyfile,ca_file,
                                token,message,managed_private=False):
    # Render private DNS is a single label with a provider-generated suffix.
    # The allowed host is pinned to the exact requested engine identity and
    # must also match the server's TLS certificate SAN.
    engine=message.get("engine_id") if isinstance(message,dict) else None
    slug=engine.lower().replace("-","") if engine in ENGINES else ""
    stem=f"abc-{slug}-private-synthetic"
    private_host=(isinstance(host,str) and server_name==host
        and bool(slug) and (
             bool(re.fullmatch(re.escape(stem)+r"(?:-[a-z0-9]{4,20})?",host))
             or host==stem+".internal"
        ))
    if (not 1<=port<=65535 or
        not ((host=="127.0.0.1" and server_name=="localhost")
             or (managed_private is True and private_host))):
        raise ValueError("private_mtls_endpoint_required")
    context=require_mtls_context(certificate=certfile,key=keyfile,ca_file=ca_file,server=False)
    with socket.create_connection((host,port),timeout=4) as sock:
        with context.wrap_socket(sock,server_hostname=server_name) as secure:
            secure.settimeout(4)
            _write_frame(secure,{"token":token,"message":message})
            return _read_frame(secure)

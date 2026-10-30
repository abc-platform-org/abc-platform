"""ENG04/05/06 draft v2 network port: true loopback TLS1.3/mTLS only.

No real cloud deployment, no paid visual inference and no v1 downgrade.
Unlike the legacy synthetic v1 mesh, the request path is: authenticated
TLS peer -> pinned signed JWT -> independent session scope -> atomic PG
replay claim -> validated v2 engine. Service startup requires externally
injected authorities, and runtime is prohibited outside local CI.
"""
import os
import socketserver
from .private_engine_transport import _read_frame,_write_frame,_Server
from .service_mesh_identity import require_mtls_context
from .engine_v2_contracts import FILES
from .store import DomainError


class _V2Handler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            frame=_read_frame(self.request)
            if (not isinstance(frame,dict) or
                set(frame)!={"token","message"} or
                not isinstance(frame["message"],dict) or
                frame["message"].get("engine_id")!=self.server.target_engine):
                raise DomainError(403,"wrong_v2_target_or_envelope")
            result=self.server.ingress.submit(
                message=frame["message"],token=frame["token"],
                verified_peer_certificate_der=self.request.getpeercert(binary_form=True))
            _write_frame(self.request,result)
        except (DomainError,ValueError,TypeError,KeyError,OSError):
            try:
                _write_frame(self.request,{
                    "error":"v2_authenticated_request_rejected",
                    "release_approved":False,"execution_authorized":False})
            except (OSError,ValueError):
                pass


def create_local_v2_mtls_server(*,target_engine,port,certfile,keyfile,
                                ca_file,ingress):
    if (os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY"
        or target_engine not in FILES
        or type(port) is not int or not 0<=port<=65535
        or ingress is None
        or not callable(getattr(ingress,"submit",None))):
        raise ValueError("unapproved_v2_mtls_engine_environment")
    tls=require_mtls_context(certificate=certfile,key=keyfile,ca_file=ca_file,
                             server=True)
    listener=_Server(("127.0.0.1",port),_V2Handler)
    listener.context=tls
    listener.target_engine=target_engine
    listener.ingress=ingress
    return listener

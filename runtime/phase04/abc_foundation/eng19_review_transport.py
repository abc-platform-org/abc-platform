"""Actual local TLS1.3 producer -> consumer socket for review receipts only.

Never executes domain engines; NEVER may listen on public interfaces.
HTTP, remote, cloud and real-customer environments are prohibited.
"""
import os
import socket
import socketserver
from .private_engine_transport import _Server,_read_frame,_write_frame
from .service_mesh_identity import require_mtls_context
from .eng19_review_consumer import AuthenticatedReviewConsumer
from .store import DomainError


class _ReviewHandler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            frame=_read_frame(self.request)
            if not isinstance(frame,dict) or set(frame)!={"token","message"}:
                raise DomainError(403,"review_transport_envelope_invalid")
            result=self.server.consumer.accept(
                message=frame["message"],token=frame["token"],
                verified_peer_certificate_der=self.request.getpeercert(binary_form=True))
            _write_frame(self.request,result)
        except (DomainError,KeyError,TypeError,ValueError,OSError):
            try:
                _write_frame(self.request,{"status":"REJECTED",
                    "error":"authenticated_handoff_rejected",
                    "durable_review_receipt":False,
                    "consumer_execution_authorized":False,
                    "customer_release_approved":False})
            except (OSError,ValueError):
                pass


def start_local_review_consumer(*,consumer,certfile,keyfile,ca_file,port=0):
    if (os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY"
        or not isinstance(consumer,AuthenticatedReviewConsumer)
        or type(port) is not int or not 0<=port<=65535):
        raise ValueError("review_consumer_local_only")
    tls=require_mtls_context(certificate=certfile,key=keyfile,
                             ca_file=ca_file,server=True)
    server=_Server(("127.0.0.1",port),_ReviewHandler)
    server.context=tls
    server.consumer=consumer
    return server


def send_local_review_handoff(*,port,token,message,
                              client_cert,client_key,server_ca):
    if (os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY"
        or type(port) is not int or not 1<=port<=65535):
        raise ValueError("review_producer_local_only")
    ssl_context=require_mtls_context(certificate=client_cert,key=client_key,
                                    ca_file=server_ca,server=False)
    with socket.create_connection(("127.0.0.1",port),timeout=4) as sock:
        with ssl_context.wrap_socket(sock,server_hostname="localhost") as tls:
            tls.settimeout(4)
            _write_frame(tls,{"token":token,"message":message})
            return _read_frame(tls)

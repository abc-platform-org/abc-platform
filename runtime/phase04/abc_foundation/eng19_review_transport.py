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
            if not isinstance(frame,dict) or set(frame) not in (
                {"token","message"},{"token","message","source_artifact"}):
                raise DomainError(403,"review_transport_envelope_invalid")
            result=self.server.consumer.accept(
                message=frame["message"],token=frame["token"],
                verified_peer_certificate_der=self.request.getpeercert(binary_form=True),
                source_artifact=frame.get("source_artifact"))
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
                              client_cert,client_key,server_ca,source_artifact=None):
    if (os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY"
        or type(port) is not int or not 1<=port<=65535):
        raise ValueError("review_producer_local_only")
    ssl_context=require_mtls_context(certificate=client_cert,key=client_key,
                                    ca_file=server_ca,server=False)
    with socket.create_connection(("127.0.0.1",port),timeout=4) as sock:
        with ssl_context.wrap_socket(sock,server_hostname="localhost") as tls:
            tls.settimeout(4)
            frame={"token":token,"message":message}
            if source_artifact is not None:
                frame["source_artifact"]=source_artifact
            _write_frame(tls,frame)
            return _read_frame(tls)


def deliver_review_with_bounded_retry(*,token_provider,max_attempts=2,
                                      transport=None,**transport_args):
    """Transport-only retry with a fresh one-time JWT and identical handoff ID.

    Retries never reinterpret a server rejection as a network outage. A
    receipt is not an engine result. The inbox enforces exact content match
    after the first successful commit, including when its reply is lost.
    """
    if (os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY"
        or not callable(token_provider)
        or type(max_attempts) is not int or not 1<=max_attempts<=3
        or "token" in transport_args or "message" not in transport_args):
        raise ValueError("bounded_local_delivery_only")
    call=transport or send_local_review_handoff
    if not callable(call):
        raise ValueError("review_transport_required")
    issued=set()
    for attempt in range(max_attempts):
        signed=token_provider()
        if type(signed) is not str or not signed or signed in issued:
            raise DomainError(403,"review_retry_requires_fresh_signed_jwt")
        issued.add(signed)
        try:
            response=call(token=signed,**transport_args)
        except OSError as exc:
            if attempt+1==max_attempts:
                raise DomainError(503,"review_transport_unavailable") from exc
            continue
        if not isinstance(response,dict) or response.get("status") not in (
             "RECORDED_REVIEW_ONLY","ALREADY_RECORDED_REVIEW_ONLY"):
            raise DomainError(403,"review_server_rejected_no_unsafe_retry")
        if (response.get("durable_review_receipt") is not True
            or response.get("consumer_execution_authorized") is not False
            or response.get("customer_release_approved") is not False):
            raise DomainError(403,"untrusted_review_receipt")
        return response
    raise DomainError(503,"review_transport_unavailable")

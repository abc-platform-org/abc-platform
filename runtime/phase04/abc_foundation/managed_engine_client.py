"""Authenticated mTLS remote-call adapter for an independently hosted engine.

Real identities and certs come from approved external brokers. No token minting,
no fallback to plaintext, no Docker/Render deployment in this module.
"""
import uuid
from .isolated_engine_service import VERSION,ENGINES
from .private_engine_transport import send_private_engine_message
from .store import DomainError


class ManagedMTLSEngineClient:
    def __init__(self,*,endpoints,client_cert,client_key,trust_ca,
                 workload_token_provider):
        if not isinstance(endpoints,dict) or set(endpoints)-set(ENGINES):
            raise ValueError("approved_engine_endpoints_required")
        if not callable(workload_token_provider):
            raise ValueError("managed_workload_token_provider_required")
        self.endpoints=endpoints
        self.client_cert=client_cert;self.client_key=client_key
        self.trust_ca=trust_ca
        self.token_provider=workload_token_provider

    def call(self,engine_id,*,consumer_id,session_id,payload):
        if engine_id not in ENGINES or engine_id not in self.endpoints:
            raise DomainError(501,"engine_private_endpoint_not_approved")
        target=self.endpoints[engine_id]
        if (not isinstance(target,dict) or
            set(target)!={"host","port","server_name"}):
            raise ValueError("invalid_private_endpoint_manifest")
        token=self.token_provider(engine_id,consumer_id)
        if not isinstance(token,str) or not token:
            raise DomainError(401,"managed_token_unavailable")
        msg={"request_id":str(uuid.uuid4()),"engine_id":engine_id,
             "contract_version":VERSION,"consumer_id":consumer_id,
             "session_id":session_id,"payload":payload}
        result=send_private_engine_message(
             host=target["host"],port=target["port"],
             server_name=target["server_name"],
             certfile=self.client_cert,keyfile=self.client_key,
             ca_file=self.trust_ca,token=token,message=msg)
        if (not isinstance(result,dict) or result.get("engine_id")!=engine_id
            or result.get("request_id")!=msg["request_id"]
            or result.get("consumer_id")!=consumer_id
            or result.get("session_id")!=session_id
            or result.get("contract_version")!=VERSION
            or result.get("release_approved") is not False
            or not isinstance(result.get("result"),dict)):
            raise DomainError(502,"untrusted_remote_engine_result")
        return result["result"]

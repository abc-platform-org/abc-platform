"""OS process isolated engine launcher for synthetic ENG04/05/06.

No shell, no inherited parent DB credentials, no API keys or network transport.
Production will replace this adapter with separate authenticated mTLS services.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from .isolated_engine_service import VERSION,ENGINES
from .store import DomainError


class IsolatedEngineRunner:
    def __init__(self,*,timeout_seconds=8):
        if type(timeout_seconds) is not int or not 1<=timeout_seconds<=15:
            raise ValueError("bounded_engine_timeout_required")
        self.timeout=timeout_seconds
        self.module_root=str(Path(__file__).resolve().parents[1])

    def call(self,engine_id,*,consumer_id,session_id,payload):
        if engine_id not in ENGINES:
            raise DomainError(501,"engine_not_allowed")
        command={"request_id":str(uuid.uuid4()),"engine_id":engine_id,
                 "contract_version":VERSION,"consumer_id":consumer_id,
                 "session_id":session_id,"payload":payload}
        raw=json.dumps(command,ensure_ascii=True,allow_nan=False,
                       separators=(",",":")).encode("utf-8")
        if len(raw)>262144:
            raise DomainError(413,"engine_request_too_large")
        # Strict child environment: no database credentials or inherited
        # service access tokens; the child has no permission to access PG.
        environment={"PYTHONPATH":self.module_root,
                     "PYTHONNOUSERSITE":"1",
                     "ABC_ENGINE_SYNTHETIC_ONLY":"true"}
        try:
            result=subprocess.run([sys.executable,"-m",
                      "abc_foundation.isolated_engine_service",engine_id],
                      input=raw,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                      timeout=self.timeout,check=False,env=environment)
        except subprocess.TimeoutExpired as exc:
            raise DomainError(504,"engine_process_deadline_exceeded") from exc
        if len(result.stdout)>262144:
            raise DomainError(502,"engine_output_oversized")
        try:
            response=json.loads(result.stdout)
        except (ValueError,UnicodeDecodeError,TypeError):
            raise DomainError(502,"engine_malformed_response") from None
        if result.returncode!=0 or not isinstance(response,dict):
            raise DomainError(422,"engine_process_rejected")
        expected={"request_id":command["request_id"],"engine_id":engine_id,
                  "contract_version":VERSION,"consumer_id":consumer_id,
                  "session_id":session_id,"release_approved":False}
        if any(response.get(k)!=v for k,v in expected.items()) or not isinstance(response.get("result"),dict):
            raise DomainError(502,"engine_response_attestation_mismatch")
        return response["result"]

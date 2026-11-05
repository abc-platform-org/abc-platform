"""ENG01 -> v2 private engine admission, controlled offline integration only.

Composes real mTLS-bound signed JWT verification, server-verified session
authority and database-backed atomic jti replay claim. It is not an HTTP
listener, not a credential issuer and not deployed to customer environments.
"""
import os
import re
from datetime import datetime,timezone
from .engine_v2_contracts import validate_port,FILES
from .engine_v2_runtime import execute
from .store import DomainError


class ScopedV2Ingress:
    def __init__(self,*,identity_verifier,scope_authority,replay_ledger,
                 caller_engine,consumer_id,transactional_admission=None):
        # Opt-in atomic PostgreSQL G05 scope/consent/replay check; legacy
        # v2 CI fixtures remain unchanged, never a fallback from G05.
        if not callable(getattr(identity_verifier,"verify",None)):
            raise ValueError("external_identity_scope_replay_authority_required")
        if transactional_admission is None:
            for obj,method in ((scope_authority,"verify"),(replay_ledger,"claim")):
                if not callable(getattr(obj,method,None)):
                    raise ValueError("external_identity_scope_replay_authority_required")
        elif not callable(getattr(transactional_admission,"admit_and_execute",None)):
            raise ValueError("g05_atomic_admission_authority_required")
        if (caller_engine not in ("ENG-01","ENG-03","ENG-04","ENG-05")
            or not isinstance(consumer_id,str) or not 3<=len(consumer_id)<=96):
            raise ValueError("approved_private_caller_binding_required")
        self.identity=identity_verifier
        self.scope=scope_authority
        self.replay=replay_ledger
        self.caller=caller_engine
        self.consumer=consumer_id
        self.transactional_admission=transactional_admission

    def submit(self,*,message,token,verified_peer_certificate_der,
               knowledge_policy_gate=None,evidence_gate=None):
        if os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
            raise DomainError(403,"v2_live_dispatch_requires_separate_review")
        if not isinstance(message,dict) or message.get("engine_id") not in FILES:
            raise DomainError(400,"invalid_v2_target")
        target=message["engine_id"]
        validate_port(message,engine=target)
        if (not isinstance(verified_peer_certificate_der,bytes)
            or not verified_peer_certificate_der or
            not isinstance(token,str)):
            raise DomainError(401,"mTLS_verified_peer_and_signed_token_required")
        # The TLS layer MUST provide peer DER only after a verified handshake.
        # Identity verifier MUST also validate the exact URI SAN and JWT cnf.
        identity=self.identity.verify(token,verified_peer_certificate_der,
              expected_engine=self.caller,expected_consumer=self.consumer)
        if (not isinstance(identity,dict) or identity.get("verified") is not True
            or identity.get("engine_id")!=self.caller
            or identity.get("consumer_id")!=self.consumer
            or message["consumer_id"]!=self.consumer
            or not isinstance(identity.get("issuer"),str)
            or identity.get("audience")!="abc-engine:"+target
            or not isinstance(identity.get("token_id"),str)
            or not isinstance(identity.get("cert_sha256"),str)
            or re.fullmatch(r"[0-9a-f]{64}",identity["cert_sha256"]) is None
            or not isinstance(identity.get("expires_at"),datetime)
            or identity["expires_at"].tzinfo is None):
            raise DomainError(401,"untrusted_workload_proof")
        if self.transactional_admission is not None:
            # Response is returned only after the protected DB transaction
            # commits; identity, consent, scope, and JTI are checked in one
            # fail-closed execution window, without a legacy v1 fallback.
            return self.transactional_admission.admit_and_execute(
                message=message,identity=identity,caller_engine=self.caller,
                execute_fn=lambda: execute(
                    message,engine=target,
                    knowledge_policy_gate=knowledge_policy_gate,
                    evidence_gate=evidence_gate))
        authorized=self.scope.verify(
            tenant_id=message["tenant_id"],branch_id=message["branch_id"],
            session_id=message["session_id"],
            state_version=message["state_version"],
            consumer_id=self.consumer,caller_engine=self.caller,
            target_engine=target,
            certificate_sha256=identity["cert_sha256"])
        if authorized is not True:
            raise DomainError(403,"v2_session_policy_scope_denied")
        # A verified JWT may only be used ONCE across ALL replicas, ever
        # until an externally governed post-expiration archive/GC.
        receipt=self.replay.claim(tenant_id=message["tenant_id"],
            issuer=identity["issuer"],audience=identity["audience"],
            jti=identity["token_id"],expires_at=identity["expires_at"])
        if (not isinstance(receipt,dict)
            or receipt.get("admitted") is not True
            or receipt.get("token_reusable") is not False):
            raise DomainError(403,"unverified_atomic_replay_receipt")
        # No hidden v1 fallback, no real images, no treatment authorization.
        return execute(message,engine=target,
                       knowledge_policy_gate=knowledge_policy_gate,
                       evidence_gate=evidence_gate)

"""Review-only durable 19-engine inbound receipt: NO engine execution.

Not an authorization issuer. External independently trusted authorities must
verify mTLS/JWT, exact session scope, current purpose consent, ENG14 policy.
Postgres independently fences consent revocation, session CAS and duplication.
"""
import hashlib
import json
import os
import re
import uuid
from datetime import datetime
from .distributed_replay import PostgresReplayLedger
from .engine19_handoff_preflight import preflight_candidate_handoff
from .store import DomainError

_SCOPE=("tenant_id","branch_id","session_id","state_version","correlation_id")


def _canonical_sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,
        separators=(",",":"),allow_nan=False,ensure_ascii=True).encode()).hexdigest()


class PostgresReviewInbox:
    def __init__(self,store):
        if not callable(getattr(store,"_connect",None)):
            raise ValueError("isolated_postgres_store_required")
        self.store=store

    def record(self,message,source_artifact=None,consumer_id=None):
        """Idempotent durable review receipt, NOT an engine ACK or processing."""
        if os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
            raise DomainError(403,"review_inbox_live_environment_blocked")
        preflight_candidate_handoff(message)
        if source_artifact is not None:
            from .eng05_review_worker import canonical_bytes
            if (not isinstance(source_artifact,dict)
                or message["from_engine"]!="ENG-04"
                or message["to_engine"]!="ENG-05"
                or not isinstance(consumer_id,str) or not 3<=len(consumer_id)<=64):
                raise DomainError(403,"source_artifact_scope_denied")
            source_bytes=canonical_bytes(source_artifact)
            if hashlib.sha256(source_bytes).hexdigest()!=message["artifact_sha256"]:
                raise DomainError(403,"source_artifact_digest_mismatch")
        args=(uuid.UUID(message["handoff_id"]),
              message["tenant_id"],message["branch_id"],
              uuid.UUID(message["session_id"]),message["state_version"],
              uuid.UUID(message["correlation_id"]),message["from_engine"],
              message["to_engine"],message["artifact_kind"],_canonical_sha(message))
        try:
            with self.store._connect() as con:
                con.execute("SELECT set_config('abc.tenant',%s,true)",
                            (message["tenant_id"],))
                con.execute("SELECT set_config('abc.branch',%s,true)",
                            (message["branch_id"],))
                if source_artifact is None:
                    row=con.execute(
                        """SELECT abc.eng19_record_review_handoff(
                          %s,%s,%s,%s,%s,%s,%s,%s,%s,%s) AS status""",args).fetchone()
                else:
                    # A single DB-owned function atomically validates the
                    # review receipt, immutable source payload and queued job.
                    # No partial receipt can survive a failed artifact check.
                    # Persisted ENG04 reports have the ENG03 source manifest
                    # signed into their immutable bytes. The dedicated SQL
                    # broker crosschecks those exact bytes against an ACKed
                    # ENG04 job. Legacy tenant-test review fixtures keep their
                    # frozen historical function; no live routing is opened.
                    verified_source=(source_artifact.get("source_engine")=="ENG-03"
                        and isinstance(source_artifact.get("source_manifest_sha256"),str))
                    function_name=("abc.eng19_submit_verified_eng04"
                        if verified_source else "abc.eng19_submit_synthetic")
                    query=("SELECT "+function_name+
                           "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) AS status")
                    row=con.execute(query,
                        (uuid.UUID(message["handoff_id"]),message["tenant_id"],
                         message["branch_id"],uuid.UUID(message["session_id"]),
                         message["state_version"],uuid.UUID(message["correlation_id"]),
                         message["artifact_sha256"],_canonical_sha(message),
                         source_bytes,consumer_id)).fetchone()
                if not row or row["status"] not in (
                    "RECORDED_REVIEW_ONLY","ALREADY_RECORDED_REVIEW_ONLY"):
                    raise DomainError(503,"review_receipt_not_committed")
                status=row["status"]
        except DomainError:
            raise
        except Exception as exc:
            # No SQL details, DSN, customer identifiers or token are returned.
            raise DomainError(403,"review_inbox_consistency_or_consent_denied") from exc
        return {"status":status,"handoff_id":message["handoff_id"],
                "to_engine":message["to_engine"],"durable_review_receipt":True,
                "consumer_execution_authorized":False,
                "professional_validation_verified":False,
                "customer_release_approved":False}


class AuthenticatedReviewConsumer:
    """Explicit verifier composition. All authorities separately injected."""
    def __init__(self,*,identity_verifier,session_authority,
                 consent_authority,eng14_authority,replay_ledger,inbox,
                 caller_engine,target_engine,consumer_id):
        objects=(identity_verifier,session_authority,consent_authority,eng14_authority)
        if not all(callable(getattr(x,"verify",None)) for x in objects):
            raise ValueError("independent_identity_scope_consent_eng14_required")
        if not isinstance(replay_ledger,PostgresReplayLedger):
            raise ValueError("durable_distributed_replay_required")
        if not isinstance(inbox,PostgresReviewInbox):
            raise ValueError("durable_review_inbox_required")
        if (not isinstance(caller_engine,str) or
            not isinstance(target_engine,str) or
            not isinstance(consumer_id,str) or not 3<=len(consumer_id)<=96
            or not re.fullmatch(r"ENG-(0[1-9]|1[0-9])",caller_engine)
            or not re.fullmatch(r"ENG-(0[1-9]|1[0-9])",target_engine)):
            raise ValueError("invalid_producer_consumer_pair")
        self.identity=identity_verifier
        self.session=session_authority
        self.consent=consent_authority
        self.policy=eng14_authority
        self.replay=replay_ledger
        self.inbox=inbox
        self.caller=caller_engine
        self.target=target_engine
        self.consumer=consumer_id

    def accept(self,*,message,token,verified_peer_certificate_der,source_artifact=None):
        if os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
            raise DomainError(403,"review_transport_live_execution_blocked")
        preflight_candidate_handoff(message)
        if message["from_engine"]!=self.caller or message["to_engine"]!=self.target:
            raise DomainError(403,"review_edge_identity_mismatch")
        if (type(token) is not str or not token or
            type(verified_peer_certificate_der) is not bytes
            or not verified_peer_certificate_der):
            raise DomainError(401,"signed_mtls_workload_required")
        proof=self.identity.verify(token,verified_peer_certificate_der,
                  expected_engine=self.caller,expected_consumer=self.consumer)
        if (not isinstance(proof,dict) or proof.get("verified") is not True or
            proof.get("engine_id")!=self.caller or
            proof.get("consumer_id")!=self.consumer or
            proof.get("audience")!="abc-engine:"+self.target or
            not re.fullmatch(r"[a-f0-9]{64}",str(proof.get("cert_sha256",""))) or
            type(proof.get("token_id")) is not str or
            type(proof.get("issuer")) is not str or
            not isinstance(proof.get("expires_at"),datetime) or
            proof["expires_at"].tzinfo is None):
            raise DomainError(401,"review_workload_proof_unverified")
        scope={k:message[k] for k in _SCOPE}
        claims={**scope,"from_engine":self.caller,"to_engine":self.target,
            "consumer_id":self.consumer,
            "certificate_sha256":proof["cert_sha256"],
            "artifact_kind":message["artifact_kind"],
            "artifact_sha256":message["artifact_sha256"],
            "policy_proof_ref":message["policy_proof_ref"]}
        if self.session.verify(**claims) is not True:
            raise DomainError(403,"review_session_authority_denied")
        if self.consent.verify(**claims,purposes=("AI_PROCESSING","INTERNAL_HANDOFF")) is not True:
            raise DomainError(403,"review_consent_missing_or_revoked")
        if self.policy.verify(**claims) is not True:
            raise DomainError(403,"review_eng14_policy_denied")
        receipt=self.replay.claim(
            tenant_id=message["tenant_id"],issuer=proof["issuer"],
            audience=proof["audience"],jti=proof["token_id"],
            expires_at=proof["expires_at"])
        if (not isinstance(receipt,dict) or
            receipt.get("admitted") is not True or
            receipt.get("token_reusable") is not False):
            raise DomainError(403,"review_atomic_replay_unverified")
        return self.inbox.record(message,source_artifact=source_artifact,consumer_id=self.consumer)

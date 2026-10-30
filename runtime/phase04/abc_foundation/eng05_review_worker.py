"""ENG05 bounded synthetic independent worker with durable PG lease fencing.

This is actual execution of the existing synthetic knowledge resolver under a
different physical PostgreSQL worker login, NOT a trained professional model.
No hosted mode, customer media, or automatic ENG06 dispatch.
"""
import hashlib
import json
import os
import uuid
from .eng05_knowledge import SyntheticKnowledgeEngine
from .eng02_consultation import SYNTHETIC_SERVICE
from .store import DomainError


def canonical_bytes(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),
           ensure_ascii=True,allow_nan=False).encode("utf-8")


class SyntheticEng05ReviewWorker:
    def __init__(self,*,store,consumer_id):
        if (not callable(getattr(store,"_connect",None))
            or type(consumer_id) is not str
            or not 3<=len(consumer_id)<=64):
            raise ValueError("dedicated_synthetic_pg_worker_required")
        self.store=store
        self.consumer=consumer_id

    @staticmethod
    def _local():
        if os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
            raise DomainError(403,"synthetic_worker_live_execution_denied")

    def claim(self,seconds=30):
        self._local()
        if type(seconds) is not int or not 1<=seconds<=120:
            raise DomainError(422,"invalid_review_lease")
        with self.store._connect() as con:
            row=con.execute("SELECT abc.eng19_claim_synthetic(%s,%s) AS job",
                            (self.consumer,seconds)).fetchone()
        return row["job"] if row else None

    def ack(self,claim,output,*,next_handoff_id):
        self._local()
        if not isinstance(claim,dict) or not isinstance(output,dict):
            raise DomainError(422,"invalid_worker_output")
        if (claim.get("consumer_id")!=self.consumer
            or claim.get("engine_id")!="ENG-05"
            or claim.get("engine_version")!="synthetic-ontology.1"):
            raise DomainError(403,"worker_or_engine_scope_mismatch")
        payload=canonical_bytes(output)
        try:
            with self.store._connect() as con:
                row=con.execute("SELECT abc.eng19_ack_synthetic(%s,%s,%s,%s) AS status",
                    (uuid.UUID(claim["handoff_id"]),uuid.UUID(claim["lease_token"]),
                     payload,uuid.UUID(next_handoff_id))).fetchone()
                if not row or row["status"]!="ACKED_REVIEW_ONLY":
                    raise DomainError(503,"worker_ack_not_committed")
        except DomainError:
            raise
        except Exception as exc:
            raise DomainError(403,"worker_ack_fenced_or_denied") from exc
        return {"status":"ACKED_REVIEW_ONLY",
                "handoff_id":claim["handoff_id"],
                "source_sha256":claim["source_sha256"],
                "result_sha256":hashlib.sha256(payload).hexdigest(),
                "engine_id":"ENG-05","engine_version":"synthetic-ontology.1",
                "next_engine":"ENG-06",
                "outbound_status":"BLOCKED_PENDING_AUTHORITY",
                "next_handoff_id":next_handoff_id,
                "downstream_dispatched":False,
                "customer_release_approved":False}

    def fail(self,claim,*,error_code="CI_PROCESSING_ERROR"):
        self._local()
        if not isinstance(claim,dict):
            raise DomainError(422,"invalid_worker_claim")
        try:
            with self.store._connect() as con:
                row=con.execute("SELECT abc.eng19_fail_synthetic(%s,%s,%s) AS status",
                    (uuid.UUID(claim["handoff_id"]),
                     uuid.UUID(claim["lease_token"]),error_code)).fetchone()
            if not row or row["status"] not in ("QUEUED","DLQ"):
                raise DomainError(503,"worker_failure_receipt_invalid")
            return row["status"]
        except DomainError:
            raise
        except Exception as exc:
            raise DomainError(403,"worker_failure_fenced") from exc

    def process_once(self):
        """Actual bounded resolver execution, atomic ACK/result/outbox commit."""
        claim=self.claim()
        if claim is None:
            return None
        try:
            source=claim["source"]
            encoded=canonical_bytes(source)
            if (hashlib.sha256(encoded).hexdigest()!=claim["source_sha256"]
                or source.get("engine_version")!="eng04.synthetic-evidence.1"
                or source.get("service_scope")!="SYNTHETIC_NON_MEDIA_ONLY"
                or source.get("session_id")!=claim["session_id"]):
                raise DomainError(403,"untrusted_synthetic_source")
            knowledge=SyntheticKnowledgeEngine().resolve(
                service_id=SYNTHETIC_SERVICE,fixture=None)
            # No professional source can be present in this limited worker.
            if (knowledge.get("ontology_version")!="synthetic-ontology.1"
                or knowledge.get("retrieval_sources")!=[]
                or "SOURCE_UNVERIFIED" not in knowledge.get("unknowns",[])):
                raise DomainError(403,"unapproved_professional_knowledge")
            next_id=str(uuid.uuid5(uuid.NAMESPACE_URL,
                      "abc-review-eng05-to-eng06:"+claim["handoff_id"]))
            return self.ack(claim,knowledge,next_handoff_id=next_id)
        except (DomainError,ValueError,TypeError,KeyError):
            self.fail(claim,error_code="CI_PROCESSING_DENIED")
            raise

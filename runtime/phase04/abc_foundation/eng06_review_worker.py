"""ENG06 isolated synthetic decision review worker (no autonomous release).

Only an administrator in disposable CI may seed abc.eng06_ci_jobs after an
ENG05 result exists. This module never reads the blocked ENG05 outbox as a
dispatcher, creates network listeners, or produces ENG07 messages. It verifies
the source chain and records only a BLOCKED_PROFESSIONAL_SOURCE decision.
"""
import hashlib
import os
import uuid

from .eng05_review_worker import canonical_bytes
from .eng06_decision import SyntheticDecisionEngine
from .store import DomainError


class SyntheticEng06ReviewWorker:
    ENGINE_ID="ENG-06"
    VERSION="eng06.synthetic.1"

    def __init__(self,*,store,consumer_id):
        if (not callable(getattr(store,"_connect",None))
                or type(consumer_id) is not str
                or not 3<=len(consumer_id)<=64):
            raise ValueError("dedicated_eng06_review_store_and_consumer_required")
        self.store=store
        self.consumer=consumer_id

    @staticmethod
    def _local():
        if os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
            raise DomainError(403,"eng06_review_live_execution_prohibited")

    def claim(self,seconds=30):
        self._local()
        if type(seconds) is not int or not 1<=seconds<=120:
            raise DomainError(422,"eng06_invalid_lease_seconds")
        try:
            with self.store._connect() as con:
                con.execute("SET LOCAL ROLE abc_eng06_review_worker")
                row=con.execute("SELECT abc.eng06_ci_claim(%s,%s) AS job",
                                (self.consumer,seconds)).fetchone()
            return row["job"] if row else None
        except DomainError:
            raise
        except Exception as exc:
            raise DomainError(403,"eng06_claim_identity_or_scope_denied") from exc

    def _validate_claim(self,claim):
        if (not isinstance(claim,dict)
                or claim.get("consumer_id")!=self.consumer
                or claim.get("engine_id")!=self.ENGINE_ID
                or claim.get("engine_version")!=self.VERSION
                or type(claim.get("analysis")) is not dict
                or type(claim.get("knowledge")) is not dict):
            raise DomainError(403,"eng06_untrusted_claim")
        analysis=claim["analysis"]
        knowledge=claim["knowledge"]
        if (hashlib.sha256(canonical_bytes(analysis)).hexdigest()
                 !=claim.get("analysis_sha256")
            or hashlib.sha256(canonical_bytes(knowledge)).hexdigest()
                 !=claim.get("knowledge_sha256")
            or analysis.get("session_id")!=claim.get("session_id")
            or analysis.get("service_scope")!="SYNTHETIC_NON_MEDIA_ONLY"
            or analysis.get("engine_version")!="eng04.synthetic-evidence.1"
            or knowledge.get("ontology_version")!="synthetic-ontology.1"
            or knowledge.get("retrieval_sources")!=[]
            or knowledge.get("grounded_facts")!=[]
            or "SOURCE_UNVERIFIED" not in knowledge.get("unknowns",[])):
            raise DomainError(403,"eng06_provenance_or_professional_source_denied")

    def decide_blocked(self,claim):
        self._local()
        self._validate_claim(claim)
        decision=SyntheticDecisionEngine().decide(
            analysis=claim["analysis"],knowledge=claim["knowledge"])
        if (decision.get("candidates")!=[]
            or decision.get("decision_engine_version")!=self.VERSION
            or decision.get("session_id")!=claim["session_id"]
            or len(decision.get("excluded_options",[]))!=2
            or any(x.get("reason")!="UNVERIFIED_KNOWLEDGE_SOURCE"
                   for x in decision["excluded_options"])):
            raise DomainError(403,"eng06_professional_source_required")
        return {
            "engine_id":self.ENGINE_ID,
            "engine_version":self.VERSION,
            "status":"BLOCKED_PROFESSIONAL_SOURCE",
            "analysis_sha256":claim["analysis_sha256"],
            "knowledge_sha256":claim["knowledge_sha256"],
            "decision":decision,
            "downstream_dispatch_authorized":False,
            "customer_release_approved":False
        }

    def ack(self,claim,output):
        self._local()
        if not isinstance(claim,dict) or not isinstance(output,dict):
            raise DomainError(422,"eng06_invalid_receipt")
        self._validate_claim(claim)
        payload=canonical_bytes(output)
        try:
            with self.store._connect() as con:
                con.execute("SET LOCAL ROLE abc_eng06_review_worker")
                row=con.execute(
                    "SELECT abc.eng06_ci_ack(%s,%s,%s,%s,%s) AS status",
                    (uuid.UUID(claim["upstream_handoff"]),
                     uuid.UUID(claim["lease_token"]),
                     claim["analysis_sha256"],claim["knowledge_sha256"],
                     payload)).fetchone()
            if not row or row["status"]!="ACKED_BLOCKED_REVIEW_ONLY":
                raise DomainError(503,"eng06_ack_not_committed")
        except DomainError:
            raise
        except Exception as exc:
            raise DomainError(403,"eng06_ack_fenced_or_denied") from exc
        return {
            "status":"ACKED_BLOCKED_REVIEW_ONLY",
            "engine_id":"ENG-06","engine_version":self.VERSION,
            "upstream_handoff":claim["upstream_handoff"],
            "output_sha256":hashlib.sha256(payload).hexdigest(),
            "next_engine":"ENG-07","downstream_dispatched":False,
            "customer_release_approved":False
        }

    def fail(self,claim,error_code="CI_PROCESSING_DENIED"):
        self._local()
        if not isinstance(claim,dict):
            raise DomainError(422,"eng06_invalid_claim")
        try:
            with self.store._connect() as con:
                con.execute("SET LOCAL ROLE abc_eng06_review_worker")
                row=con.execute(
                    "SELECT abc.eng06_ci_fail(%s,%s,%s) AS status",
                    (uuid.UUID(claim["upstream_handoff"]),
                     uuid.UUID(claim["lease_token"]),error_code)).fetchone()
            if not row or row["status"] not in ("QUEUED","DLQ"):
                raise DomainError(503,"eng06_failure_not_committed")
            return row["status"]
        except DomainError:
            raise
        except Exception as exc:
            raise DomainError(403,"eng06_failure_fenced") from exc

    def process_once(self):
        """One claim and a denied-professional-source result, no follow-on."""
        claim=self.claim()
        if claim is None:
            return None
        try:
            return self.ack(claim,self.decide_blocked(claim))
        except (DomainError,ValueError,KeyError,TypeError):
            self.fail(claim,error_code="CI_PROCESSING_DENIED")
            raise

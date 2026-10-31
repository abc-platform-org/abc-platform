"""ENG04 independent synthetic evidence-to-analysis Worker.

No image/model calls, no ENG05 auto-dispatch, no standalone live permission.
Only physically bound ENG04 login can execute the DB-owned source/lease broker.
"""
import hashlib
import json
import os
import uuid
from .eng04_analysis import SyntheticBeautyAnalysis
from .eng05_review_worker import canonical_bytes
from .eng19_review_producer import eng04_synthetic_analysis_candidate
from .store import DomainError

class SyntheticEng04ReviewWorker:
    ENGINE_ID="ENG-04"
    VERSION="eng04.synthetic-evidence.1"

    def __init__(self,*,store,consumer_id):
        if (not callable(getattr(store,"_connect",None))
            or not isinstance(consumer_id,str)
            or not 3<=len(consumer_id)<=64):
            raise ValueError("independent_eng04_workload_and_consumer_required")
        self.store=store
        self.consumer=consumer_id

    @staticmethod
    def _local():
        if os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
            raise DomainError(403,"eng04_external_execution_blocked")

    def _broker(self,query,args):
        self._local()
        try:
            with self.store._connect() as con:
                con.execute("SET LOCAL ROLE abc_eng04_worker")
                row=con.execute(query,args).fetchone()
                return next(iter(row.values())) if row else None
        except Exception as exc:
            raise DomainError(403,"eng04_db_identity_or_gate_denied") from exc

    def claim(self,seconds=30):
        if type(seconds) is not int or not 1<=seconds<=120:
            raise DomainError(422,"eng04_invalid_lease")
        return self._broker("SELECT abc.eng04_ci_claim(%s,%s) AS job",
                            (self.consumer,seconds))

    def _verify(self,claim):
        if (not isinstance(claim,dict)
            or claim.get("engine_id")!=self.ENGINE_ID
            or claim.get("artifact_kind")!="BEAUTY_ANALYSIS_REPORT"
            or claim.get("consumer_id")!=self.consumer
            or not isinstance(claim.get("sources"),list)
            or len(claim["sources"])!=4):
            raise DomainError(403,"eng04_untrusted_evidence_claim")
        items=claim["sources"]
        check=[]
        evidence=[]
        fields=set()
        ids=set()
        for src in items:
            if not isinstance(src,dict) or not isinstance(src.get("evidence"),dict):
                raise DomainError(403,"eng04_invalid_source")
            data=src["evidence"]
            ident=src.get("evidence_id")
            if (type(ident) is not str or ident!=data.get("evidence_id")
                or data.get("session_id")!=claim.get("session_id")
                or data.get("service_id")!="synthetic:hair-color"
                or not src.get("policy_decision_id")
                or not src.get("source_job_id")
                or not src.get("source_answer_id")
                or hashlib.sha256(canonical_bytes(data)).hexdigest()!=src.get("digest")
                or ident in ids or data.get("attribute_key") in fields):
                raise DomainError(403,"eng04_evidence_provenance_mismatch")
            ids.add(ident)
            fields.add(data["attribute_key"])
            check.append(ident+":"+src["digest"])
            evidence.append(data)
        if (fields!={"prior_treatment","sensitivity_flag","goal","maintenance"}
            or hashlib.sha256("|".join(sorted(check)).encode()).hexdigest()
                   !=claim.get("source_manifest_sha256")):
            raise DomainError(403,"eng04_incomplete_or_tampered_manifest")
        return evidence

    def analyse(self,claim):
        self._local()
        evidence=self._verify(claim)
        result=SyntheticBeautyAnalysis().analyse(
            session_id=claim["session_id"],evidence=evidence)
        if (result.get("engine_version")!=self.VERSION
            or result.get("service_scope")!="SYNTHETIC_NON_MEDIA_ONLY"
            or result.get("evidence_ids")!=sorted(x["evidence_id"] for x in evidence)):
            raise DomainError(403,"eng04_generated_report_invalid")
        # Bind the exact ENG03 source-manifest to the independently versioned
        # BEAUTY_ANALYSIS_REPORT. The upstream source is not trusted by name.
        result["source_manifest_sha256"]=claim["source_manifest_sha256"]
        result["source_engine"]="ENG-03"
        result["professional_validation_verified"]=False
        return result

    def ack(self,claim,report):
        self._local()
        self._verify(claim)
        if not isinstance(report,dict):
            raise DomainError(422,"eng04_report_required")
        # A worker caller may not replace evidence-grounded attributes or
        # invent professional assurance while retaining a valid manifest.
        expected=self.analyse(claim)
        fields=set(expected)
        if set(report)!=fields or any(
            report[key]!=expected[key] for key in fields if key!="created_at"
        ) or not isinstance(report.get("created_at"),str):
            raise DomainError(403,"eng04_unverified_report_mutation")
        result=self._broker(
            "SELECT abc.eng04_ci_ack(%s,%s,%s,%s) AS result",
            (uuid.UUID(claim["job_id"]),uuid.UUID(claim["lease_token"]),
             claim["source_manifest_sha256"],canonical_bytes(report)))
        if result!="ACKED_REVIEW_ONLY":
            raise DomainError(403,"eng04_ack_rejected")
        return {"status":result,"job_id":claim["job_id"],
                "artifact_kind":"BEAUTY_ANALYSIS_REPORT",
                "analysis_sha256":hashlib.sha256(canonical_bytes(report)).hexdigest(),
                "downstream_dispatched":False,
                "customer_release_approved":False}

    def fail(self,claim,code="CI_PROCESSING_DENIED"):
        self._local()
        try:
            result=self._broker(
                "SELECT abc.eng04_ci_fail(%s,%s,%s) AS result",
                (uuid.UUID(claim["job_id"]),uuid.UUID(claim["lease_token"]),code))
        except (KeyError,ValueError,TypeError) as exc:
            raise DomainError(403,"eng04_invalid_failure_receipt") from exc
        if result not in ("QUEUED","DLQ"):
            raise DomainError(403,"eng04_invalid_failure_state")
        return result

    def process_once(self):
        claim=self.claim()
        if claim is None:
            return None
        try:
            return self.ack(claim,self.analyse(claim))
        except (DomainError,ValueError,KeyError,TypeError):
            self.fail(claim)
            raise

    def review_candidate(self,job_id,*,correlation_id,handoff_id):
        """Read only durable, approved-to-review output; never send itself."""
        self._local()
        export=self._broker(
            "SELECT abc.eng04_ci_result_for_review(%s) AS result",
            (uuid.UUID(job_id),))
        if (not isinstance(export,dict)
            or export.get("consumer_id")!=self.consumer
            or export.get("status")!="BLOCKED_PENDING_AUTHORITY"
            or hashlib.sha256(canonical_bytes(export["analysis"])).hexdigest()
                    !=export.get("analysis_sha256")):
            raise DomainError(403,"eng04_untrusted_review_export")
        message=eng04_synthetic_analysis_candidate(
            analysis=export["analysis"],tenant_id=export["tenant_id"],
            branch_id=export["branch_id"],state_version=export["state_version"],
            correlation_id=correlation_id,handoff_id=handoff_id,
            policy_proof_ref="synthetic:eng14-policy-proof")
        return {"message":message,"source_artifact":export["analysis"],
                "source_manifest_sha256":export["source_manifest_sha256"],
                "dispatch_authorized":False,"customer_release_approved":False}

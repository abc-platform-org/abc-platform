"""Produce a review candidate from the existing bounded ENG04 synthetic result.

This constructs a content hash, not a real media binding or trusted signature.
No network send and no implicit stage execution occur here.
"""
import os
import uuid
from .eng04_analysis import SyntheticBeautyAnalysis
from .eng19_review_consumer import _canonical_sha
from .engine19_handoff_preflight import preflight_candidate_handoff
from .store import DomainError


def eng04_synthetic_analysis_candidate(*,analysis,tenant_id,branch_id,
        state_version,correlation_id,handoff_id,policy_proof_ref):
    if os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
        raise DomainError(403,"synthetic_producer_local_only")
    if (not isinstance(analysis,dict)
        or analysis.get("engine_version")!=SyntheticBeautyAnalysis.ENGINE_VERSION
        or analysis.get("service_scope")!="SYNTHETIC_NON_MEDIA_ONLY"
        or not isinstance(analysis.get("evidence_ids"),list)
        or not analysis["evidence_ids"]
        or type(state_version) is not int
        or not isinstance(policy_proof_ref,str)
        or not policy_proof_ref.startswith("synthetic:")):
        raise DomainError(422,"untrusted_synthetic_producer_input")
    try:
        session=str(uuid.UUID(analysis["session_id"]))
        if session!=analysis["session_id"]:
            raise ValueError()
    except (ValueError,TypeError,KeyError):
        raise DomainError(422,"invalid_source_session") from None
    message={
        "handoff_id":handoff_id,
        "contract_version":"abc.internal.capability.v3.review",
        "from_engine":"ENG-04","to_engine":"ENG-05",
        "tenant_id":tenant_id,"branch_id":branch_id,
        "session_id":session,"state_version":state_version,
        "correlation_id":correlation_id,
        "artifact_kind":"BEAUTY_ANALYSIS_REPORT",
        "artifact_sha256":_canonical_sha(analysis),
        "evidence_refs":["synthetic:evidence-"+item for item
                         in sorted(analysis["evidence_ids"])],
        "policy_proof_ref":policy_proof_ref,
        "status":"CANDIDATE_FOR_EXTERNAL_AUTHORIZATION",
        "execution_authorized":False,"customer_release_approved":False}
    preflight_candidate_handoff(message)
    return message

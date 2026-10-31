"""ENG05 first official technical-source intake: immutable review-only case.

A regulator-authored occupational-safety rule is not a reviewed client
hair-colour procedure, individual specialist credential, or legal reuse grant.
This module does not connect ENG05's runtime worker or release ENG06.
"""
from __future__ import annotations
import hashlib
import re
from .eng05_professional_sources import canonical,digest,SourceGovernanceError

CONTRACT="abc.eng05.first-professional-source-intake.v1.review"
EXPECTED_CASE="eng05-de-hair-color-worker-safety-trgs530-20230420"
EXPECTED_PDF_URL=("https://www.baua.de/DE/Angebote/"
 "Rechtstexte-und-Technische-Regeln/Regelwerk/TRGS/pdf/"
 "TRGS-530.pdf?__blob=publicationFile")
REQUIRED_APPROVALS=(
 "SOURCE_BYTES","CURRENT_VERSION","LEGAL_RIGHTS",
 "SPECIALIST_CREDENTIAL","INDEPENDENT_CLAIM_REVIEW",
 "SAFETY_CONFLICT_ADJUDICATION")
SHA=re.compile(r"^[0-9a-f]{64}$")


def _exact(value,keys,label):
    if not isinstance(value,dict) or set(value)!=set(keys):
        raise SourceGovernanceError(label+"_contract_shape_invalid")


def validate_first_source_case(case):
    _exact(case,("contract","candidate_id","title","primary_url",
     "verification_url","official_register_url","issuer",
     "publication_reference","edition_date","discovery_date",
     "jurisdiction","service_scope","professional_domain","applicability",
     "excluded_use","source_version_status","source_byte_access",
     "source_pdf_sha256","source_content_ingested","provenance_evidence",
     "review_prompts_not_professional_claims","rights_provenance",
     "independent_professional_review","independent_legal_review",
     "acceptance"),"first_source")
    if (case["contract"]!=CONTRACT
        or case["candidate_id"]!=EXPECTED_CASE
        or case["primary_url"]!=EXPECTED_PDF_URL
        or case["edition_date"]!="2023-04-20"
        or case["jurisdiction"]!="DE" or case["service_scope"]!="HAIR_COLOR"
        or case["professional_domain"]!="SALON_EMPLOYEE_OCCUPATIONAL_CHEMICAL_SAFETY"
        or case["source_pdf_sha256"] is not None
        or case["source_content_ingested"] is not False
        or "FAILED" not in case["source_byte_access"]):
        raise SourceGovernanceError("official_source_provenance_or_bytes_false_claim")
    if not case["verification_url"].startswith("https://www.bgw-online.de/"):
        raise SourceGovernanceError("secondary_provenance_not_official")
    if not case["official_register_url"].startswith("https://www.baua.de/"):
        raise SourceGovernanceError("version_register_not_official")
    if not isinstance(case["applicability"],list) or "worker_exposure" not in case["applicability"]:
        raise SourceGovernanceError("workplace_hazard_scope_missing")
    excluded=set(case["excluded_use"])
    for forbidden in ("individual_client_allergy_diagnosis",
                      "customer_treatment_decision",
                      "dye_mix_formula_or_ratio",
                      "eng06_professional_decision"):
        if forbidden not in excluded:
            raise SourceGovernanceError("unapproved_hair_colour_use_case")
    refs=case["provenance_evidence"]
    if not isinstance(refs,list) or len(refs)<4:
        raise SourceGovernanceError("insufficient_section_provenance")
    seen=set()
    for entry in refs:
        _exact(entry,("section","pdf_page","verification","status"),"section")
        if (entry["section"] in seen or type(entry["pdf_page"]) is not int
            or not 1<=entry["pdf_page"]<=15
            or entry["status"] not in ("VISUALLY_CHECKED","TEXT_REVIEWED")
            or not isinstance(entry["verification"],str)
            or len(entry["verification"])<24):
            raise SourceGovernanceError("section_review_not_traceable")
        seen.add(entry["section"])
    prompts=case["review_prompts_not_professional_claims"]
    if not isinstance(prompts,list) or len(prompts)<4 or len({
       p.get("id") for p in prompts if isinstance(p,dict)})!=len(prompts):
        raise SourceGovernanceError("reviewer_questions_missing")
    for prompt in prompts:
        _exact(prompt,("id","section","question","risk"),"review_prompt")
        if (not isinstance(prompt["question"],str)
            or len(prompt["question"])<25
            or prompt["section"] not in {r["section"].split(" ")[0] for r in refs}
               | {"1","3.2","3.6","4"}):
            raise SourceGovernanceError("review_prompt_not_grounded")
    rights=case["rights_provenance"]
    _exact(rights,("work_rights_jurisdiction","legal_publication_status",
       "commercial_reuse_cleared","machine_ingestion_rights_cleared",
       "redistribution_rights_cleared","quoted_material_copied",
       "rights_basis_evidence","rights_reviewer_attestation","status"),"rights")
    if (rights["work_rights_jurisdiction"]!="DE"
        or rights["status"]!="LEGAL_REVIEW_REQUIRED"
        or rights["commercial_reuse_cleared"] is not False
        or rights["machine_ingestion_rights_cleared"] is not False
        or rights["redistribution_rights_cleared"] is not False
        or rights["quoted_material_copied"] is not False
        or rights["rights_basis_evidence"] is not None
        or rights["rights_reviewer_attestation"] is not None):
        raise SourceGovernanceError("reuse_legal_authority_not_supplied")
    reviewer=case["independent_professional_review"]
    _exact(reviewer,("issuer_discovery_reference","germany_trade_law_reference",
        "reviewer_identity","verifying_competent_authority",
        "credential_evidence_sha256","independent_pinned_signing_root_sha256",
        "individual_license_verified","specialist_signed_claims",
        "safety_critical_requires_distinct_reviewers","verification_state"),"specialist")
    if (reviewer["reviewer_identity"] is not None
        or reviewer["verifying_competent_authority"] is not None
        or reviewer["credential_evidence_sha256"] is not None
        or reviewer["independent_pinned_signing_root_sha256"] is not None
        or reviewer["individual_license_verified"] is not False
        or reviewer["specialist_signed_claims"]!=[]
        or reviewer["safety_critical_requires_distinct_reviewers"]!=2
        or reviewer["verification_state"]!="AWAITING_ACTUAL_SPECIALIST_AND_ISSUER"):
        raise SourceGovernanceError("specialist_certification_false_claim")
    legal=case["independent_legal_review"]
    _exact(legal,("rights_counsel_identity","license_or_exemption_evidence_sha256",
        "jurisdiction_specific_opinion","status"),"legal")
    if (legal["rights_counsel_identity"] is not None
        or legal["license_or_exemption_evidence_sha256"] is not None
        or legal["jurisdiction_specific_opinion"] is not None
        or legal["status"]!="AWAITING_LEGAL_RIGHTS_OPINION"):
        raise SourceGovernanceError("legal_rights_clearance_false_claim")
    acceptance=case["acceptance"]
    _exact(acceptance,("externally_provenanced_document_sha256",
        "source_evidence_gate","rights_gate","specialist_gate",
        "jurisdiction_gate","clinical_diagnosis_gate",
        "professional_claim_release_authorized","eng05_review_worker_connected",
        "eng05_to_eng06_dispatch_authorized","customer_release_approved",
        "overall_status"),"acceptance")
    if (acceptance["externally_provenanced_document_sha256"] is not None
        or acceptance["source_evidence_gate"]!="BLOCKED_BYTES_NOT_VERIFIED"
        or acceptance["rights_gate"]!="BLOCKED_RIGHTS_UNCLEARED"
        or acceptance["specialist_gate"]!="BLOCKED_CREDENTIAL_AND_SIGNATURES_ABSENT"
        or acceptance["professional_claim_release_authorized"] is not False
        or acceptance["eng05_review_worker_connected"] is not False
        or acceptance["eng05_to_eng06_dispatch_authorized"] is not False
        or acceptance["customer_release_approved"] is not False
        or acceptance["overall_status"]!="CANDIDATE_ONLY_NOT_PROFESSIONALLY_APPROVED"):
        raise SourceGovernanceError("first_source_acceptance_promotion_forbidden")
    return {"case_sha256":digest(case),
      "candidate_id":EXPECTED_CASE,"official_document":True,
      "original_pdf_bytes_verified":False,"legal_commercial_rights_cleared":False,
      "specialist_credential_verified":False,"professionally_released_facts":[],
      "next_approvals":list(REQUIRED_APPROVALS),
      "eng05_runtime_ingestion_enabled":False,
      "eng05_to_eng06_dispatch_authorized":False,
      "customer_release_approved":False}


def local_pdf_evidence_hash(blob):
    """Compute SHA only from *actual* bytes; this never grants publication rights."""
    if not isinstance(blob,(bytes,bytearray)) or not 128<=len(blob)<=10_000_000:
        raise SourceGovernanceError("actual_pdf_bytes_required")
    if not bytes(blob).startswith(b"%PDF-"):
        raise SourceGovernanceError("not_an_actual_pdf_document")
    return {"source_document_sha256":hashlib.sha256(blob).hexdigest(),
       "document_bytes_received_locally":True,
       "legal_use_authorized":False,
       "specialist_approved":False,
       "runtime_ingestion_authorized":False}


def create_external_review_requests(case):
    """Prepare deterministic, non-authoritative human workflow envelopes."""
    v=validate_first_source_case(case)
    case_sha=v["case_sha256"]
    return [{
       "case_id":case["candidate_id"],
       "case_sha256":case_sha,
       "approval_domain":domain,
       "evidence_required":{
         "SOURCE_BYTES":"Actual official PDF bytes and independently computed SHA-256",
         "CURRENT_VERSION":"Current BAuA active register edition, amendment and date check",
         "LEGAL_RIGHTS":"Written, jurisdiction-specific reuse/ingestion/licensing legal opinion or grant",
         "SPECIALIST_CREDENTIAL":"Competent-authority verified individual qualification, expiry, revocation and independently pinned issuer",
         "INDEPENDENT_CLAIM_REVIEW":"Signed qualified independent expert review, exact sections, scope, contraindications and limitations",
         "SAFETY_CONFLICT_ADJUDICATION":"Independent second safety-critical reviewer, conflicting source review and documented resolution",
       }[domain],
       "approval_status":"EXTERNAL_EVIDENCE_MISSING",
       "accepted_signatures":0,
       "grants_professional_facts":False,
       "eng06_dispatch_authorized":False,
    } for domain in REQUIRED_APPROVALS]

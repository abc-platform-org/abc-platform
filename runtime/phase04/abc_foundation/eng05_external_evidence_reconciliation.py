"""ENG05: reconcile independently observed official sources; no authority.

This validator explicitly keeps PUBLIC REGISTER evidence separate from actual
PDF bytes, reuse/ingestion rights, independently verified specialist identities
and legal/professional signoffs. An authoritative web page is never a signed
credential from a named practitioner or a source-document checksum.
"""
from __future__ import annotations
import re
from datetime import date
from .eng05_professional_sources import SourceGovernanceError,digest

CONTRACT="abc.eng05.trgs530.external-evidence-reconciliation.v1.review"
CASE_ID="eng05-de-hair-color-worker-safety-trgs530-20230420"
EXPECTED_APPROVALS={
 "SOURCE_BYTES":"BLOCKED_ORIGINAL_PDF_SHA256_MISSING",
 "CURRENT_VERSION":"REGISTER_OBSERVED_HUMAN_SIGNATURE_REQUIRED",
 "LEGAL_RIGHTS":"BLOCKED_WRITTEN_RIGHTS_REVIEW_REQUIRED",
 "SPECIALIST_CREDENTIAL":"BLOCKED_NO_SPECIFIC_PERSON_VERIFIED",
 "INDEPENDENT_CLAIM_REVIEW":"BLOCKED_NO_QUALIFIED_SIGNATURE",
 "SAFETY_CONFLICT_ADJUDICATION":"BLOCKED_NO_INDEPENDENT_ADJUDICATION"
}
EXPECTED_BAUA_REGISTER="https://www.baua.de/DE/Angebote/Regelwerk/TRGS/TRGS"
EXPECTED_BAUA_PDF="https://www.baua.de/DE/Angebote/Regelwerk/TRGS/pdf/TRGS-530.pdf?__blob=publicationFile"


def _exact(value,keys,error):
    if not isinstance(value,dict) or set(value)!=set(keys):
        raise SourceGovernanceError(error+"_shape_invalid")


def verify_reconciliation(packet):
    _exact(packet,("contract","case_id","checked_on_utc","jurisdiction","scope",
       "official_current_edition","primary_pdf","legal_rights",
       "professional_credential","contact_channels","approval_ledger",
       "signature_evidence","professionally_released_facts",
       "professional_runtime_authorized","eng05_to_eng06_dispatch_authorized",
       "customer_release_approved","external_messages_sent"),"reconciliation")
    if (packet["contract"]!=CONTRACT or packet["case_id"]!=CASE_ID
        or packet["jurisdiction"]!="DE"
        or packet["scope"]!="SALON_EMPLOYEE_OCCUPATIONAL_CHEMICAL_SAFETY"
        or not isinstance(packet["checked_on_utc"],str)
        or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",packet["checked_on_utc"])):
        raise SourceGovernanceError("source_case_or_date_invalid")
    try:
        date.fromisoformat(packet["checked_on_utc"])
    except ValueError as exc:
        raise SourceGovernanceError("reconciliation_date_invalid") from exc
    reg=packet["official_current_edition"]
    _exact(reg,("evidence_state","publication_edition","source",
       "source_url","register_listing","new_amendment_in_inspected_register",
       "independent_human_version_signoff","note"),"register")
    if (reg["evidence_state"]!="PUBLIC_REGISTER_OBSERVED_NOT_EXTERNALLY_SIGNED"
        or reg["publication_edition"]!="2023-04-20"
        or reg["source"]!="BAUA_OFFICIAL_TRGS_REGISTER"
        or reg["source_url"]!=EXPECTED_BAUA_REGISTER
        or reg["new_amendment_in_inspected_register"] is not False
        or reg["independent_human_version_signoff"] is not False
        or not isinstance(reg["note"],str) or len(reg["note"])<50):
        raise SourceGovernanceError("official_register_not_independent_acceptance")
    pdf=packet["primary_pdf"]
    _exact(pdf,("source_url","official_mime_declared","published_page_count",
       "observed_title","web_extracted_text_accessible",
       "verified_raw_file_bytes","execution_download_attempts",
       "document_sha256","response_headers_sha256",
       "independent_checksum_publication_found","document_reuse_permitted"),
       "pdf")
    if (pdf["source_url"]!=EXPECTED_BAUA_PDF
        or pdf["official_mime_declared"]!="application/pdf"
        or pdf["published_page_count"]!=15
        or pdf["verified_raw_file_bytes"] is not False
        or pdf["document_sha256"] is not None
        or pdf["response_headers_sha256"] is not None
        or pdf["independent_checksum_publication_found"] is not False
        or pdf["document_reuse_permitted"] is not False):
        raise SourceGovernanceError("pdf_bytes_or_reuse_false_claim")
    attempts=pdf["execution_download_attempts"]
    if not isinstance(attempts,list) or len(attempts)<2:
        raise SourceGovernanceError("pdf_failed_attempts_not_traceable")
    methods=set()
    for a in attempts:
        _exact(a,("method","result","content_sha256"),"pdf_attempt")
        if (not isinstance(a["method"],str) or a["method"] in methods
            or a["content_sha256"] is not None
            or a["result"] not in ("NETWORK_DNS_UNAVAILABLE","DOWNLOAD_FAILED",
                                    "HTTP_403_ON_DIRECT_RENDER")):
            raise SourceGovernanceError("unverified_pdf_attempt")
        methods.add(a["method"])
    rights=packet["legal_rights"]
    _exact(rights,("state","statutory_candidates","publisher_terms",
       "questions_for_counsel","written_professional_legal_opinion_received",
       "rights_holder_explicit_permission_received","approved_use_modes"),"legal")
    if (rights["state"]!="LEGAL_OPINION_AND_PERMISSION_REQUIRED"
        or rights["written_professional_legal_opinion_received"] is not False
        or rights["rights_holder_explicit_permission_received"] is not False
        or rights["approved_use_modes"]!=[]
        or not isinstance(rights["statutory_candidates"],list)
        or len(rights["statutory_candidates"])!=3
        or not isinstance(rights["questions_for_counsel"],list)
        or len(rights["questions_for_counsel"])<4):
        raise SourceGovernanceError("missing_legal_rights_opinion")
    terms=rights["publisher_terms"]
    _exact(terms,("url","disclosed_constraint","actual_scope_of_copyright_exception",
                  "request_permission_from_publisher"),"publisher_terms")
    if (terms["url"]!="https://www.baua.de/DE/Services/Impressum"
        or terms["actual_scope_of_copyright_exception"]!="NOT_DETERMINED"
        or terms["request_permission_from_publisher"] is not True):
        raise SourceGovernanceError("commercial_usage_rights_unresolved")
    reviewer=packet["professional_credential"]
    _exact(reviewer,("state","verified_personnel_count",
       "qualifying_domains","competent_authority_discovery",
       "independent_signer_pinned","accepted_signatures",
       "safety_critical_reviewers_required",
       "human_conflict_resolution_completed"),"credential")
    if (reviewer["state"]!="NO_IDENTIFIED_OR_VERIFIED_REVIEWER"
        or reviewer["verified_personnel_count"]!=0
        or reviewer["independent_signer_pinned"] is not False
        or reviewer["accepted_signatures"]!=0
        or reviewer["safety_critical_reviewers_required"]!=2
        or reviewer["human_conflict_resolution_completed"] is not False
        or not isinstance(reviewer["qualifying_domains"],list)
        or len(reviewer["qualifying_domains"])<2):
        raise SourceGovernanceError("fake_qualified_reviewer")
    contacts=packet["contact_channels"]
    if not isinstance(contacts,list) or len(contacts)!=3:
        raise SourceGovernanceError("incomplete_external_routing")
    for contact in contacts:
        _exact(contact,("party","purpose","email","source_url","message_status"),
               "contact")
        if (contact["message_status"] not in
           ("DRAFT_NOT_SENT","AWAITING_REVIEWER_AND_JURISDICTION",
            "AWAITING_IDENTIFIED_PROFESSIONAL")):
            raise SourceGovernanceError("unverifiable_outreach_claim")
    if (packet["approval_ledger"]!=EXPECTED_APPROVALS
        or packet["signature_evidence"]!=[]
        or packet["professionally_released_facts"]!=[]
        or packet["professional_runtime_authorized"] is not False
        or packet["eng05_to_eng06_dispatch_authorized"] is not False
        or packet["customer_release_approved"] is not False
        or packet["external_messages_sent"] is not False):
        raise SourceGovernanceError("unapproved_professional_or_eng06_release")
    return {
      "case_id":CASE_ID,"reconciliation_sha256":digest(packet),
      "official_registry_current_edition_observed":"2023-04-20",
      "raw_document_sha256_verified":False,
      "legal_rights_cleared":False,"qualified_specialists_verified":0,
      "pending_approval_domains":list(EXPECTED_APPROVALS),
      "professional_runtime_authorized":False,
      "eng05_to_eng06_dispatch_authorized":False,
      "customer_release_approved":False
    }

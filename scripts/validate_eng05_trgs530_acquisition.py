"""No live source authority can be conferred by raw PDF acquisition."""
import json
from pathlib import Path
P=Path(__file__).resolve().parents[1]
RUN=(P/"scripts/attest_eng05_trgs530_source.py").read_text()
WORKFLOW=(P/".github/workflows/eng05-trgs530-source-attestation.yml").read_text()
SOURCE=json.loads((P/"governance/abc_eng05_trgs530_first_professional_source_intake.v1.review.json").read_text())
REGISTER=json.loads((P/"governance/abc_eng05_trgs530_current_registry_and_rights_check.v1.review.json").read_text())

def validate():
    for phrase in ("BAUA_CURRENT","BAUA_LEGACY","BGW_OFFICIAL",
       "sha256_actual_pdf_bytes","pdftotext","pdfinfo",
       "expected_15_pages_missing","untrusted_source",
       "PDF_BYTES_HASHED_AND_EDITION_CHECKED","BLOCKED_SOURCE_BYTES_UNAVAILABLE",
       '"legal_reuse_clearance":False','"real_specialist_signatures":0',
       '"eng05_to_eng06_dispatch_authorized":False'):
        if phrase=="untrusted_source":
            assert "not_exact_official_https_origin" in RUN
        else: assert phrase in RUN,phrase
    assert "permissions:" in WORKFLOW and "contents: read" in WORKFLOW
    assert "actions/upload-artifact@v4" in WORKFLOW
    assert "eng05-trgs530-source-attestation.json" in WORKFLOW
    EVIDENCE=json.loads((P/"governance/abc_eng05_trgs530_bgw_raw_pdf_provenance_2026-10-31.v1.review.json").read_text())
    assert EVIDENCE["sha256_of_actual_bgw_pdf_bytes"] in RUN
    assert EVIDENCE["downloaded_bytes"]==741429
    assert EVIDENCE["pdf_pages"]==15
    assert EVIDENCE["cross_host_pdf_byte_identity_proven"] is False
    assert EVIDENCE["rights_assessment"]=="NOT_INDEPENDENTLY_APPROVED"
    assert EVIDENCE["professional_source_release_authorized"] is False
    assert EVIDENCE["eng05_to_eng06_dispatch_authorized"] is False
    assert SOURCE["source_pdf_sha256"] is None
    assert SOURCE["source_content_ingested"] is False
    assert REGISTER["original_pdf"]["sha256"] is None
    assert REGISTER["competent_authority_person_verification"]["individual_license_evidence"] is None
    assert REGISTER["disposition"]["professional_ingestion_allowed"] is False
    assert REGISTER["disposition"]["eng05_to_eng06_dispatch_allowed"] is False
    return {"official_register_edition_observed":"April 2023",
        "raw_source_pdf_sha256_claimed":False,
        "independent_legal_opinion_received":False,
        "actual_credential_verified":False,
        "eng05_to_eng06_enabled":False}
if __name__=="__main__":
    print(json.dumps(validate(),sort_keys=True))

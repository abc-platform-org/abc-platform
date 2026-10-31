"""Fail-closed ENG05 first real source intake: NO professional release."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CASE=json.loads((ROOT/"governance/abc_eng05_trgs530_first_professional_source_intake.v1.review.json").read_text())
MOD=(ROOT/"runtime/phase04/abc_foundation/eng05_first_source_acceptance.py").read_text()
SQL=(ROOT/"runtime/phase04/migrations/0028_eng05_external_document_acceptance_cases.sql").read_text()
WORKER=(ROOT/"runtime/phase04/abc_foundation/eng05_review_worker.py").read_text()
PLAN=(ROOT/"runtime/phase04/abc_foundation/staging_migrate.py").read_text()

def check():
    assert SQL.rstrip().endswith("COMMIT;") and SQL.count("\nCOMMIT;")==1
    assert "0028_eng05_external_document_acceptance_cases.sql" in PLAN
    assert "CREATE TABLE abc.eng05_external_document_acceptance_cases" in SQL
    assert "CREATE TABLE abc.eng05_external_approval_requests" in SQL
    assert "FORCE ROW LEVEL SECURITY" in SQL
    assert "BEFORE UPDATE OR DELETE" in SQL
    for forbidden in (
       "CHECK(source_document_sha256 IS NULL)",
       "CHECK(redistribution_rights_cleared=false)",
       "CHECK(machine_ingestion_rights_cleared=false)",
       "CHECK(individual_specialist_license_verified=false)",
       "CHECK(specialist_signed_claims_count=0)",
       "CHECK(human_professional_release_authorized=false)",
       "CHECK(eng05_runtime_ingestion_enabled=false)",
       "CHECK(eng06_dispatch_authorized=false)",
       "CHECK(approval_status='EXTERNAL_EVIDENCE_MISSING')",
       "CHECK(external_signature_verified=false)",
       "CHECK(authorizes_professional_facts=false)",
       "CHECK(authorizes_eng06=false)"):
        assert forbidden in SQL,forbidden
    assert "GRANT SELECT" not in SQL and "GRANT EXECUTE" not in SQL
    assert "UPDATE abc.eng19_synthetic_outbox" not in SQL
    assert "eng05_first_source_acceptance" not in WORKER
    assert "SOURCE_UNVERIFIED" in WORKER
    assert CASE["source_pdf_sha256"] is None
    assert CASE["source_content_ingested"] is False
    assert CASE["rights_provenance"]["machine_ingestion_rights_cleared"] is False
    assert CASE["independent_professional_review"]["individual_license_verified"] is False
    assert CASE["acceptance"]["eng05_to_eng06_dispatch_authorized"] is False
    assert CASE["acceptance"]["customer_release_approved"] is False
    assert "actual_pdf_bytes_required" in MOD
    assert "SPECIALIST_CREDENTIAL" in MOD and "LEGAL_RIGHTS" in MOD
    return {"document":"TRGS 530 Friseurhandwerk 2023-04-20",
        "official_source_reference_found":True,
        "actual_pdf_sha256_verified":False,
        "legal_commercial_rights_cleared":False,
        "independent_specialists_verified":0,
        "external_approval_domains":6,
        "eng05_runtime_ingestion":False,
        "eng05_to_eng06_released":False}

if __name__=="__main__":
    print(json.dumps(check(),sort_keys=True))

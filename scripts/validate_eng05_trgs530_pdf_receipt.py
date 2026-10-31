"""ENG05 published PDF SHA receipt: exact SHA, immutable provenance, no release."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
R=json.loads((ROOT/"governance/abc_eng05_trgs530_bgw_pdf_byte_receipt_2026-10-31.v1.review.json").read_text())
C=json.loads((ROOT/"governance/abc_eng05_trgs530_first_professional_source_intake.v1.review.json").read_text())
SQL=(ROOT/"runtime/phase04/migrations/0029_eng05_official_pdf_byte_receipts.sql").read_text()
PLAN=(ROOT/"runtime/phase04/abc_foundation/staging_migrate.py").read_text()
TEST=(ROOT/"runtime/phase04/tests/test_eng05_official_pdf_byte_receipt.py").read_text()
WORKER=(ROOT/"runtime/phase04/abc_foundation/eng05_review_worker.py").read_text()
EXPECTED="356fc7d7ef4d4dc56ae687c72dfbf00d156b65ae494553f15f0060d7b46b5628"

def check():
    assert R["raw_pdf_bytes_sha256"]==EXPECTED
    assert R["raw_pdf_byte_count"]==741429 and R["pdf_page_count"]==15
    assert R["provenance"]["workflow_run_id"]==41233336210
    assert R["provenance"]["exact_code_commit_sha"]=="f7cb9609661ba829cc70b909f8d18d89cb4f5872"
    assert R["provenance"]["source_pdf_committed_to_repository"] is False
    assert R["evidence_caveats"]["raw_bytes_verified"] is True
    assert R["evidence_caveats"]["independently_publisher_signed_file_hash_verified"] is False
    assert R["evidence_caveats"]["licensing_and_commercial_ingestion_rights_cleared"] is False
    assert R["evidence_caveats"]["independently_qualified_specialist_reviewers"]==0
    assert R["acceptance"]["knowledge_admission"]=="BLOCKED_PENDING_AUTHORITY"
    assert R["acceptance"]["eng05_to_eng06_dispatch_authorized"] is False
    assert R["acceptance"]["customer_release_approved"] is False
    assert C["source_pdf_sha256"] is None and C["source_content_ingested"] is False
    assert C["acceptance"]["eng05_to_eng06_dispatch_authorized"] is False
    assert "0029_eng05_official_pdf_byte_receipts.sql" in PLAN
    assert SQL.rstrip().endswith("COMMIT;") and SQL.count("\nCOMMIT;")==1
    for control in (
       "CREATE TABLE abc.eng05_official_pdf_byte_receipts",
       "FORCE ROW LEVEL SECURITY",
       "BEFORE UPDATE OR DELETE",
       "CHECK(publisher_signed_checksum_verified=false)",
       "CHECK(source_commercial_rights_verified=false)",
       "CHECK(specialist_review_verified=false)",
       "CHECK(runtime_knowledge_ingestion_authorized=false)",
       "CHECK(eng06_dispatch_authorized=false)"):
        assert control in SQL,control
    assert "GRANT SELECT" not in SQL and "GRANT EXECUTE" not in SQL
    assert "eng05_official_pdf_byte_receipts" not in WORKER
    assert "test_durable_authentic_hash_receipt_and_immutable_provenance" in TEST
    return {"source":"BGW TRGS530 Fassung 20.04.2023",
        "source_bytes":741429,"pages":15,
        "source_sha256":EXPECTED,
        "verified_in_github_actions_run":41233336210,
        "publisher_signed_checksum":False,
        "legal_rights":False,"specialist_credentials":0,
        "ENG05_ingestion":False,"ENG06_release":False}

if __name__=="__main__":
    print(json.dumps(check(),sort_keys=True))

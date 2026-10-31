"""ENG05 W1 first-source offline byte evidence does not grant authority."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MIG=(ROOT/"runtime/phase04/migrations/0029_eng05_trgs530_byte_observations.sql").read_text()
MODULE=(ROOT/"runtime/phase04/abc_foundation/eng05_trgs530_byte_observation.py").read_text()
WORKER=(ROOT/"runtime/phase04/abc_foundation/eng05_review_worker.py").read_text()
PLAN=(ROOT/"runtime/phase04/abc_foundation/staging_migrate.py").read_text()
CASE=json.loads((ROOT/"governance/abc_eng05_trgs530_first_professional_source_intake.v1.review.json").read_text())

def check():
    assert MIG.rstrip().endswith("COMMIT;") and MIG.count("\nCOMMIT;")==1
    assert "0029_eng05_trgs530_byte_observations.sql" in PLAN
    assert "CREATE TABLE abc.eng05_trgs530_byte_observations(" in MIG
    for x in ("ENABLE ROW LEVEL SECURITY","FORCE ROW LEVEL SECURITY",
      "BEFORE UPDATE OR DELETE",
      "CHECK(original_document_archived=false)",
      "CHECK(byte_origin_independently_attested=false)",
      "CHECK(publisher_checksum_verified=false)",
      "CHECK(legal_clearance_granted=false)",
      "CHECK(text_ingestion_rights_verified=false)",
      "CHECK(specialist_signature_accepted=false)",
      "CHECK(eng05_runtime_ingestion_authorized=false)",
      "CHECK(eng06_dispatch_authorized=false)",
      "CHECK(observation_metadata_sha256=encode(sha256(observation_metadata_bytes),'hex'))"):
        assert x in MIG,x
    assert "GRANT SELECT" not in MIG and "GRANT EXECUTE" not in MIG
    assert "eng05_trgs530_byte_observation" not in WORKER
    assert "eng06_dispatch" not in MODULE or '"eng05_to_eng06_dispatch_authorized":False' in MODULE
    assert "not_an_actual_pdf_document" not in MODULE
    assert "pdf_magic_invalid" in MODULE and "pdf_final_eof_marker_missing" in MODULE
    assert "byte_origin_independently_attested" in MODULE
    assert CASE["source_pdf_sha256"] is None
    assert CASE["rights_provenance"]["machine_ingestion_rights_cleared"] is False
    assert CASE["acceptance"]["eng05_to_eng06_dispatch_authorized"] is False
    return {"case":"TRGS530-2023","migration":29,"byte_observation_possible":True,
       "full_pdf_raw_bytes_retrieved_in_execution":False,
       "verified_pdf_sha256":None,"real_specialist_signoff":False,
       "legal_rights_approved":False,"eng05_operational_ingestion":False,
       "eng06_dispatch":False}
if __name__=="__main__":
    print(json.dumps(check(),sort_keys=True))

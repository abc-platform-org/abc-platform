"""ENG05 source governance contractual and no-release build gate."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SQL=(ROOT/"runtime/phase04/migrations/0026_eng05_professional_evidence_governance.sql").read_text()
MODULE=(ROOT/"runtime/phase04/abc_foundation/eng05_professional_sources.py").read_text()
WORKER=(ROOT/"runtime/phase04/abc_foundation/eng05_review_worker.py").read_text()
PLAN=(ROOT/"runtime/phase04/abc_foundation/staging_migrate.py").read_text()
SOURCE=json.loads((ROOT/"governance/abc_eng05_professional_source.v1.review.schema.json").read_text())
REVIEW=json.loads((ROOT/"governance/abc_eng05_specialist_attestation.v1.review.schema.json").read_text())

def check():
    assert SQL.rstrip().endswith("COMMIT;") and SQL.count("\nCOMMIT;")==1
    assert "0026_eng05_professional_evidence_governance.sql" in PLAN
    for table in ("eng05_professional_source_candidates",
                  "eng05_professional_review_attestations",
                  "eng05_professional_conflict_dossiers"):
        assert "CREATE TABLE abc."+table in SQL
        assert table in SQL.split("FOREACH t IN ARRAY ARRAY[",1)[1]
    for mandatory in (
        "FORCE ROW LEVEL SECURITY",
        "BEFORE UPDATE OR DELETE",
        "UNVERIFIED_EXTERNAL_AUTHORITY",
        "AWAITING_EXTERNAL_CREDENTIAL_ISSUER",
        "CHECK(professional_release_authorized=false)",
        "CHECK(eng06_dispatch_authorized=false)",
        "CHECK(authority_released=false)",
        "CHECK(eng06_release_authorized=false)",
        "CHECK(source_sha256=encode(sha256(source_bytes),'hex'))",
        "abc_eng05_worker",
    ):
        assert mandatory in SQL,mandatory
    assert "GRANT SELECT" not in SQL and "GRANT INSERT" not in SQL
    assert "UPDATE abc.eng19_synthetic_outbox" not in SQL
    assert "CREATE OR REPLACE FUNCTION abc.eng19_ack_synthetic" not in SQL
    assert "eng05_professional_sources" not in WORKER
    assert "SOURCE_UNVERIFIED" in WORKER
    assert "REVIEWED_NON_EXECUTABLE" in MODULE
    assert "professionally_released_facts" in MODULE
    assert '"eng05_to_eng06_dispatch_authorized":False' in MODULE
    assert '"customer_release_approved":False' in MODULE
    assert "Ed25519PublicKey" in MODULE
    assert "reviewer_not_independent" in MODULE
    assert "SPECIALIST_APPROVAL_REQUIRED" in MODULE
    assert "SAFETY_CRITICAL_CONFLICT" in MODULE
    assert SOURCE["additionalProperties"] is False
    assert REVIEW["additionalProperties"] is False
    assert SOURCE["properties"]["contract"]["const"]=="abc.eng05.professional-source.v1.review"
    assert REVIEW["properties"]["contract"]["const"]=="abc.eng05.specialist-review.v1.review"
    assert REVIEW["properties"]["signature_alg"]["const"]=="Ed25519"
    assert REVIEW["properties"]["conflict_of_interest"]["const"] is False
    return {"engine":"ENG-05","knowledge_contract":"professional-source.v1.review",
      "specialist_attestation":"Ed25519 signed independent review",
      "source_categories":5,"governance_tables":3,
      "professional_sources_verified":0,"eng05_to_eng06_enabled":False,
      "customer_release":False}

if __name__=="__main__":
    print(json.dumps(check(),sort_keys=True))

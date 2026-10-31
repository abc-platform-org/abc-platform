"""Require ENG05 TRGS 530 public evidence to remain non-operational."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=json.loads((ROOT/"governance/abc_eng05_trgs530_external_evidence_reconciliation.v1.review.json").read_text())
MODULE=(ROOT/"runtime/phase04/abc_foundation/eng05_external_evidence_reconciliation.py").read_text()
SQL=(ROOT/"runtime/phase04/migrations/0029_eng05_external_evidence_reconciliation.sql").read_text()
PLAN=(ROOT/"runtime/phase04/abc_foundation/staging_migrate.py").read_text()
WORKER=(ROOT/"runtime/phase04/abc_foundation/eng05_review_worker.py").read_text()

def check():
    assert SQL.rstrip().endswith("COMMIT;") and SQL.count("\nCOMMIT;")==1
    assert "0029_eng05_external_evidence_reconciliation.sql" in PLAN
    assert "CREATE TABLE abc.eng05_external_evidence_reconciliations" in SQL
    for token in (
       "ENABLE ROW LEVEL SECURITY","FORCE ROW LEVEL SECURITY",
       "BEFORE UPDATE OR DELETE",
       "CHECK(official_pdf_digest IS NULL)",
       "CHECK(commercial_legal_rights_granted=false)",
       "CHECK(independent_professional_identity_verified=false)",
       "CHECK(independent_specialist_signed_reviews=0)",
       "CHECK(eng05_production_knowledge_authorized=false)",
       "CHECK(eng06_dispatch_authorized=false)",
       "CHECK(evidence_approval_state='AWAITING_EXTERNAL_EVIDENCE')",
       "provenance_sha256=encode(sha256(provenance_packet),'hex')"
    ):
        assert token in SQL,token
    assert "GRANT SELECT" not in SQL and "GRANT EXECUTE" not in SQL
    assert "UPDATE abc.eng19_synthetic_outbox" not in SQL
    assert "eng05_external_evidence_reconciliation" not in WORKER
    assert "SOURCE_UNVERIFIED" in WORKER
    assert SOURCE["official_current_edition"]["publication_edition"]=="2023-04-20"
    assert SOURCE["official_current_edition"]["independent_human_version_signoff"] is False
    assert SOURCE["primary_pdf"]["verified_raw_file_bytes"] is False
    assert SOURCE["primary_pdf"]["document_sha256"] is None
    assert SOURCE["legal_rights"]["written_professional_legal_opinion_received"] is False
    assert SOURCE["professional_credential"]["verified_personnel_count"]==0
    assert SOURCE["external_messages_sent"] is False
    assert SOURCE["professionally_released_facts"]==[]
    assert SOURCE["eng05_to_eng06_dispatch_authorized"] is False
    for f in ("verify_reconciliation","pdf_bytes_or_reuse_false_claim",
              "commercial_usage_rights_unresolved",
              "fake_qualified_reviewer","unapproved_professional_or_eng06_release"):
        assert f in MODULE,f
    return {"scope":"GERMAN_TRGS530_PUBLIC_EVIDENCE_RECONCILIATION",
      "public_version":"2023-04-20","source_pdf_sha256_verified":False,
      "rights_clearance":False,"independent_practitioners_verified":0,
      "outreach_drafts_saved":True,"messages_sent":False,
      "eng05_live_knowledge":False,"eng05_to_eng06_released":False}

if __name__=="__main__":
    print(json.dumps(check(),sort_keys=True))

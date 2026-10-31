"""Fail closed on attempts to turn ENG05 source discovery into professional authority."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SQL=(ROOT/"runtime/phase04/migrations/0027_eng05_external_authority_discovery.sql").read_text()
MODULE=(ROOT/"runtime/phase04/abc_foundation/eng05_external_authority.py").read_text()
WORKER=(ROOT/"runtime/phase04/abc_foundation/eng05_review_worker.py").read_text()
PLAN=(ROOT/"runtime/phase04/abc_foundation/staging_migrate.py").read_text()
CAT=json.loads((ROOT/"governance/abc_eng05_hair_color_eu_official_references.v1.review.json").read_text())
SCHEMA=json.loads((ROOT/"governance/abc_eng05_external_issuer_manifest.v1.review.schema.json").read_text())

def check():
    assert SQL.rstrip().endswith("COMMIT;") and SQL.count("\nCOMMIT;")==1
    assert "0027_eng05_external_authority_discovery.sql" in PLAN
    for n in ("eng05_official_reference_discovery","eng05_external_issuer_review_packets"):
        assert "CREATE TABLE abc."+n in SQL
        assert n in SQL.split("FOREACH t IN ARRAY ARRAY[",1)[1]
    for flag in ("CHECK(documentation_state='REFERENCE_ONLY')",
       "CHECK(source_bytes_verified=false)",
       "CHECK(republication_rights_verified=false)",
       "CHECK(specialist_approved=false)",
       "CHECK(external_authority_verified=false)",
       "CHECK(professional_signoff_accepted=false)",
       "CHECK(eng06_release_authorized=false)",
       "FORCE ROW LEVEL SECURITY","BEFORE UPDATE OR DELETE",
       "CHECK(reference_sha256=encode(sha256(reference_bytes),'hex'))",
       "CHECK(issuer_manifest_sha256=encode(sha256(issuer_manifest_bytes),'hex'))"):
        assert flag in SQL,flag
    assert "GRANT EXECUTE" not in SQL and "GRANT SELECT" not in SQL
    assert "UPDATE abc.eng19_synthetic_outbox" not in SQL
    assert "adjudicate" in MODULE
    assert "from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey" in MODULE
    assert "independently_pinned_root_sha256" in MODULE
    assert "issuer_signature_invalid" in MODULE
    assert "expected_issuer_id" in MODULE
    assert "out_of_band_issuer_identity_mismatch" in MODULE
    assert "issuer_roster_rollback_denied" in MODULE
    assert "unknown_credential_revocation_id" in MODULE
    assert '"eng05_to_eng06_dispatch_authorized":False' in MODULE
    assert "eng05_external_authority" not in WORKER
    assert len(CAT["references"])==3
    assert all(x["status"]=="REFERENCE_ONLY" and not x["expert_verified"]
       and x["raw_document_sha256"] is None
       and not x["license_to_copy_verified"] for x in CAT["references"])
    assert CAT["external_credential_issuer_connected"] is False
    assert CAT["professional_rights_cleared"] is False
    assert CAT["eng05_to_eng06_dispatch_authorized"] is False
    assert SCHEMA["additionalProperties"] is False
    assert SCHEMA["properties"]["contract"]["const"]=="abc.eng05.external-credential-issuer.v1.review"
    return {"scope":"EU_HAIR_COLOR_OFFICIAL_DISCOVERY_ONLY","references":3,
     "external_issuer_provisioned":False,"licensed_professional_sources":0,
     "legal_republication_grants":0,"eng05_to_eng06_dispatched":False,
     "customer_release":False}

if __name__=="__main__":
    print(json.dumps(check(),sort_keys=True))

-- 0029: legally distinct external-evidence reconciliation; NEVER a professional release.
-- A verified official registry is not an accepted PDF-byte hash, rights grant,
-- individual practitioner certificate, professional review or ENG06 authorization.
BEGIN;
CREATE TABLE abc.eng05_external_evidence_reconciliations (
 evidence_id uuid PRIMARY KEY,
 case_id text NOT NULL REFERENCES abc.eng05_external_document_acceptance_cases(case_id),
 checked_date date NOT NULL,
 provenance_packet bytea NOT NULL CHECK(octet_length(provenance_packet) BETWEEN 1024 AND 32768),
 provenance_sha256 text NOT NULL CHECK(
   provenance_sha256=encode(sha256(provenance_packet),'hex')),
 public_register_state text NOT NULL
   CHECK(public_register_state='CURRENT_EDITION_PUBLICLY_OBSERVED_ONLY'),
 official_pdf_digest text NULL CHECK(official_pdf_digest IS NULL),
 commercial_legal_rights_granted boolean NOT NULL DEFAULT false
   CHECK(commercial_legal_rights_granted=false),
 independent_professional_identity_verified boolean NOT NULL DEFAULT false
   CHECK(independent_professional_identity_verified=false),
 independent_specialist_signed_reviews integer NOT NULL DEFAULT 0
   CHECK(independent_specialist_signed_reviews=0),
 evidence_approval_state text NOT NULL DEFAULT 'AWAITING_EXTERNAL_EVIDENCE'
   CHECK(evidence_approval_state='AWAITING_EXTERNAL_EVIDENCE'),
 eng05_production_knowledge_authorized boolean NOT NULL DEFAULT false
   CHECK(eng05_production_knowledge_authorized=false),
 eng06_dispatch_authorized boolean NOT NULL DEFAULT false
   CHECK(eng06_dispatch_authorized=false),
 inserted_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(case_id,provenance_sha256)
);
ALTER TABLE abc.eng05_external_evidence_reconciliations ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.eng05_external_evidence_reconciliations FORCE ROW LEVEL SECURITY;
REVOKE ALL ON abc.eng05_external_evidence_reconciliations
 FROM PUBLIC,abc_app,abc_worker,abc_answer_worker,abc_orchestrator,
 abc_eng03_worker,abc_pipeline_worker,abc_eng04_worker,
 abc_eng05_worker,abc_eng06_review_worker;
CREATE TRIGGER eng05_evidence_reconciliation_immutable
 BEFORE UPDATE OR DELETE ON abc.eng05_external_evidence_reconciliations
 FOR EACH ROW EXECUTE FUNCTION abc.eng05_professional_append_only();
DO $owner$
BEGIN
 IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='abc_staging_migrator') THEN
  CREATE POLICY eng05_staging_external_reconciliation
   ON abc.eng05_external_evidence_reconciliations
   FOR ALL TO abc_staging_migrator USING(true) WITH CHECK(true);
 END IF;
END;$owner$;
COMMIT;

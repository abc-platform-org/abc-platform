-- 0029: AUTHENTIC raw-source PDF SHA256 receipt for ENG05 review-only case.
-- Receipt was observed from the BGW publisher URL by Github Actions run
-- 41233336210 (f7cb9609661ba829cc70b909f8d18d89cb4f5872).
-- This is independently recorded byte provenance, NOT copyright permission,
-- specialist attestation, issuer-signature or professional knowledge approval.
BEGIN;
CREATE TABLE abc.eng05_official_pdf_byte_receipts (
 receipt_id uuid PRIMARY KEY,
 case_id text NOT NULL REFERENCES abc.eng05_external_document_acceptance_cases(case_id),
 source_edition text NOT NULL CHECK(source_edition='TRGS530_FASSUNG_20_04_2023'),
 source_publisher text NOT NULL CHECK(source_publisher='BGW'),
 retrieved_source_url text NOT NULL CHECK(retrieved_source_url=
   'https://www.bgw-online.de/resource/blob/20628/29cbf999ca5c2d91e741fa6964c6c619/trgs530-gefahrstoffe-friseurhandwerk-data.pdf'),
 source_pdf_sha256 text NOT NULL CHECK(source_pdf_sha256 ~ '^[0-9a-f]{64}$'),
 source_size_bytes bigint NOT NULL CHECK(source_size_bytes BETWEEN 32000 AND 6000000),
 pdf_page_count smallint NOT NULL CHECK(pdf_page_count=15),
 verification_run_id bigint NOT NULL CHECK(verification_run_id > 0),
 verification_commit_sha text NOT NULL CHECK(verification_commit_sha ~ '^[0-9a-f]{40}$'),
 receipt_metadata_bytes bytea NOT NULL CHECK(octet_length(receipt_metadata_bytes) BETWEEN 512 AND 16384),
 receipt_metadata_sha256 text NOT NULL CHECK(
    receipt_metadata_sha256=encode(sha256(receipt_metadata_bytes),'hex')),
 publisher_signed_checksum_verified boolean NOT NULL DEFAULT false
   CHECK(publisher_signed_checksum_verified=false),
 source_commercial_rights_verified boolean NOT NULL DEFAULT false
   CHECK(source_commercial_rights_verified=false),
 specialist_review_verified boolean NOT NULL DEFAULT false
   CHECK(specialist_review_verified=false),
 runtime_knowledge_ingestion_authorized boolean NOT NULL DEFAULT false
   CHECK(runtime_knowledge_ingestion_authorized=false),
 eng06_dispatch_authorized boolean NOT NULL DEFAULT false
   CHECK(eng06_dispatch_authorized=false),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(case_id,source_pdf_sha256,verification_run_id)
);
ALTER TABLE abc.eng05_official_pdf_byte_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.eng05_official_pdf_byte_receipts FORCE ROW LEVEL SECURITY;
REVOKE ALL ON abc.eng05_official_pdf_byte_receipts FROM PUBLIC,abc_app,
  abc_worker,abc_answer_worker,abc_orchestrator,abc_eng03_worker,
  abc_pipeline_worker,abc_eng04_worker,abc_eng05_worker,abc_eng06_review_worker;
CREATE TRIGGER eng05_official_pdf_snapshot_immutable
  BEFORE UPDATE OR DELETE ON abc.eng05_official_pdf_byte_receipts
  FOR EACH ROW EXECUTE FUNCTION abc.eng05_professional_append_only();
DO $acl$
BEGIN
 IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='abc_staging_migrator') THEN
   CREATE POLICY eng05_migrator_pdf_receipts
     ON abc.eng05_official_pdf_byte_receipts
     FOR ALL TO abc_staging_migrator USING(true) WITH CHECK(true);
 END IF;
END;$acl$;
COMMIT;

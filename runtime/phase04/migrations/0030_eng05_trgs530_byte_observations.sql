-- 0030: append-only offline hash observations of actual externally supplied
-- TRGS530 bytes. No original PDF stored, no professional clearance or release.
-- An observed SHA never authenticates the claimed publisher or rights.
BEGIN;
CREATE TABLE abc.eng05_trgs530_byte_observations(
 observation_id uuid PRIMARY KEY,
 case_id text NOT NULL REFERENCES abc.eng05_external_document_acceptance_cases(case_id),
 claimed_source_url text NOT NULL CHECK (
   claimed_source_url IN (
    'https://www.baua.de/DE/Angebote/Rechtstexte-und-Technische-Regeln/Regelwerk/TRGS/pdf/TRGS-530.pdf?__blob=publicationFile',
    'https://www.baua.de/DE/Angebote/Regelwerk/TRGS/pdf/TRGS-530.pdf?__blob=publicationFile',
    'https://www.bgw-online.de/resource/blob/20628/29cbf999ca5c2d91e741fa6964c6c619/trgs530-gefahrstoffe-friseurhandwerk-data.pdf'
   )),
 observed_document_sha256 text NOT NULL CHECK(observed_document_sha256 ~ '^[a-f0-9]{64}$'),
 observed_pdf_bytes integer NOT NULL CHECK(observed_pdf_bytes BETWEEN 1024 AND 12582912),
 observation_metadata_bytes bytea NOT NULL CHECK(octet_length(observation_metadata_bytes) BETWEEN 512 AND 8192),
 observation_metadata_sha256 text NOT NULL
   CHECK(observation_metadata_sha256=encode(sha256(observation_metadata_bytes),'hex')),
 status text NOT NULL DEFAULT 'HASH_OBSERVATION_PENDING_INDEPENDENT_PROVENANCE'
   CHECK(status='HASH_OBSERVATION_PENDING_INDEPENDENT_PROVENANCE'),
 original_document_archived boolean NOT NULL DEFAULT false
   CHECK(original_document_archived=false),
 byte_origin_independently_attested boolean NOT NULL DEFAULT false
   CHECK(byte_origin_independently_attested=false),
 publisher_checksum_verified boolean NOT NULL DEFAULT false
   CHECK(publisher_checksum_verified=false),
 professional_license_verified boolean NOT NULL DEFAULT false
   CHECK(professional_license_verified=false),
 text_ingestion_rights_verified boolean NOT NULL DEFAULT false
   CHECK(text_ingestion_rights_verified=false),
 legal_clearance_granted boolean NOT NULL DEFAULT false
   CHECK(legal_clearance_granted=false),
 specialist_signature_accepted boolean NOT NULL DEFAULT false
   CHECK(specialist_signature_accepted=false),
 eng05_runtime_ingestion_authorized boolean NOT NULL DEFAULT false
   CHECK(eng05_runtime_ingestion_authorized=false),
 eng06_dispatch_authorized boolean NOT NULL DEFAULT false
   CHECK(eng06_dispatch_authorized=false),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(case_id,claimed_source_url,observed_document_sha256)
);
ALTER TABLE abc.eng05_trgs530_byte_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.eng05_trgs530_byte_observations FORCE ROW LEVEL SECURITY;
REVOKE ALL ON abc.eng05_trgs530_byte_observations FROM PUBLIC,
 abc_app,abc_worker,abc_answer_worker,abc_orchestrator,abc_eng03_worker,
 abc_pipeline_worker,abc_eng04_worker,abc_eng05_worker,abc_eng06_review_worker;
CREATE TRIGGER eng05_trgs530_byte_observation_immutable
 BEFORE UPDATE OR DELETE ON abc.eng05_trgs530_byte_observations
 FOR EACH ROW EXECUTE FUNCTION abc.eng05_professional_append_only();
DO $policy$
BEGIN
 IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='abc_staging_migrator') THEN
  CREATE POLICY eng05_staging_byte_observation
   ON abc.eng05_trgs530_byte_observations FOR ALL TO abc_staging_migrator
   USING (true) WITH CHECK (true);
 END IF;
END;$policy$;
COMMIT;

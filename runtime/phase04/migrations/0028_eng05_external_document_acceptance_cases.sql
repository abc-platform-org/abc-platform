-- ENG05 W1 0028 — official technical rule ingestion candidate, never release.
-- This migration does not add a specialist, license, source bytes or ENG06 route.
BEGIN;
CREATE TABLE abc.eng05_external_document_acceptance_cases (
 case_id text PRIMARY KEY CHECK(length(case_id) BETWEEN 12 AND 120),
 jurisdiction text NOT NULL CHECK(jurisdiction='DE'),
 service_scope text NOT NULL CHECK(service_scope='HAIR_COLOR'),
 technical_domain text NOT NULL CHECK(technical_domain='SALON_EMPLOYEE_OCCUPATIONAL_CHEMICAL_SAFETY'),
 normative_reference text NOT NULL CHECK(normative_reference='TRGS 530'),
 official_edition text NOT NULL CHECK(official_edition='2023-04-20'),
 official_url text NOT NULL CHECK(official_url LIKE
  'https://www.baua.de/DE/Angebote/Rechtstexte-und-Technische-Regeln/Regelwerk/TRGS/pdf/TRGS-530.pdf%'),
 source_metadata_bytes bytea NOT NULL CHECK(octet_length(source_metadata_bytes) BETWEEN 512 AND 32768),
 source_metadata_sha256 text NOT NULL CHECK(
   source_metadata_sha256=encode(sha256(source_metadata_bytes),'hex')),
 source_document_sha256 text NULL CHECK(source_document_sha256 IS NULL),
 document_content_verified boolean NOT NULL DEFAULT false
   CHECK(document_content_verified=false),
 redistribution_rights_cleared boolean NOT NULL DEFAULT false
   CHECK(redistribution_rights_cleared=false),
 machine_ingestion_rights_cleared boolean NOT NULL DEFAULT false
   CHECK(machine_ingestion_rights_cleared=false),
 individual_specialist_license_verified boolean NOT NULL DEFAULT false
   CHECK(individual_specialist_license_verified=false),
 specialist_signed_claims_count integer NOT NULL DEFAULT 0
   CHECK(specialist_signed_claims_count=0),
 human_professional_release_authorized boolean NOT NULL DEFAULT false
   CHECK(human_professional_release_authorized=false),
 eng05_runtime_ingestion_enabled boolean NOT NULL DEFAULT false
   CHECK(eng05_runtime_ingestion_enabled=false),
 eng06_dispatch_authorized boolean NOT NULL DEFAULT false
   CHECK(eng06_dispatch_authorized=false),
 review_state text NOT NULL DEFAULT 'CANDIDATE_ONLY_NOT_PROFESSIONALLY_APPROVED'
   CHECK(review_state='CANDIDATE_ONLY_NOT_PROFESSIONALLY_APPROVED'),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE abc.eng05_external_approval_requests (
 request_id uuid PRIMARY KEY,
 case_id text NOT NULL REFERENCES abc.eng05_external_document_acceptance_cases(case_id),
 approval_domain text NOT NULL CHECK(approval_domain IN
   ('SOURCE_BYTES','CURRENT_VERSION','LEGAL_RIGHTS','SPECIALIST_CREDENTIAL',
    'INDEPENDENT_CLAIM_REVIEW','SAFETY_CONFLICT_ADJUDICATION')),
 request_metadata_bytes bytea NOT NULL
   CHECK(octet_length(request_metadata_bytes) BETWEEN 64 AND 8192),
 request_metadata_sha256 text NOT NULL CHECK(
   request_metadata_sha256=encode(sha256(request_metadata_bytes),'hex')),
 approval_status text NOT NULL DEFAULT 'EXTERNAL_EVIDENCE_MISSING'
   CHECK(approval_status='EXTERNAL_EVIDENCE_MISSING'),
 external_signature_verified boolean NOT NULL DEFAULT false
   CHECK(external_signature_verified=false),
 authorizes_professional_facts boolean NOT NULL DEFAULT false
   CHECK(authorizes_professional_facts=false),
 authorizes_eng06 boolean NOT NULL DEFAULT false
   CHECK(authorizes_eng06=false),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(case_id,approval_domain,request_metadata_sha256)
);
DO $protect$
DECLARE t text;
BEGIN
 FOREACH t IN ARRAY ARRAY[
   'eng05_external_document_acceptance_cases',
   'eng05_external_approval_requests'
 ] LOOP
  EXECUTE format('ALTER TABLE abc.%I ENABLE ROW LEVEL SECURITY',t);
  EXECUTE format('ALTER TABLE abc.%I FORCE ROW LEVEL SECURITY',t);
  EXECUTE format('REVOKE ALL ON abc.%I FROM PUBLIC,abc_app,abc_worker,abc_answer_worker,abc_orchestrator,abc_eng03_worker,abc_pipeline_worker,abc_eng04_worker,abc_eng05_worker,abc_eng06_review_worker',t);
  EXECUTE format('CREATE TRIGGER eng05_external_acceptance_immutable BEFORE UPDATE OR DELETE ON abc.%I FOR EACH ROW EXECUTE FUNCTION abc.eng05_professional_append_only()',t);
  IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='abc_staging_migrator') THEN
    EXECUTE format('CREATE POLICY eng05_staging_external_case_review ON abc.%I FOR ALL TO abc_staging_migrator USING(true) WITH CHECK(true)',t);
  END IF;
 END LOOP;
END;$protect$;
COMMIT;

-- 0026: professionally grounded source candidates are REVIEW-ONLY.
-- No externally attested professional signers have been provisioned.
-- No DML or promotion ability granted to any engine, API, worker or ENG06.
BEGIN;
CREATE TABLE abc.eng05_professional_source_candidates (
  candidate_id uuid PRIMARY KEY,
  source_id text NOT NULL CHECK(length(source_id) BETWEEN 6 AND 96),
  source_version text NOT NULL CHECK(source_version ~ '^[1-9][0-9]*\.[0-9]+\.[0-9]+$'),
  service_scope text NOT NULL CHECK(service_scope IN (
    'HAIRCUT','HAIR_COLOR','BEARD','SKIN_BEAUTY','MAKEUP',
    'NAILS','EXTENSIONS','BRIDAL')),
  source_sha256 text NOT NULL CHECK(source_sha256 ~ '^[0-9a-f]{64}$'),
  source_bytes bytea NOT NULL CHECK(octet_length(source_bytes) BETWEEN 128 AND 65536),
  source_type text NOT NULL CHECK(source_type IN (
    'PEER_REVIEWED_RESEARCH','MANUFACTURER_PROTOCOL',
    'PROFESSIONAL_GUIDELINE','LICENSED_TRAINING_MANUAL',
    'CI_SYNTHETIC_FIXTURE')),
  trust_state text NOT NULL DEFAULT 'UNVERIFIED_EXTERNAL_AUTHORITY'
    CHECK(trust_state='UNVERIFIED_EXTERNAL_AUTHORITY'),
  professional_release_authorized boolean NOT NULL DEFAULT false
    CHECK(professional_release_authorized=false),
  eng06_dispatch_authorized boolean NOT NULL DEFAULT false
    CHECK(eng06_dispatch_authorized=false),
  inserted_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE(source_id,source_version),
  CHECK(source_sha256=encode(sha256(source_bytes),'hex'))
);
CREATE TABLE abc.eng05_professional_review_attestations (
  review_id uuid PRIMARY KEY,
  candidate_id uuid NOT NULL REFERENCES abc.eng05_professional_source_candidates(candidate_id),
  reviewer_id text NOT NULL CHECK(length(reviewer_id) BETWEEN 3 AND 200),
  credential_id text NOT NULL CHECK(length(credential_id) BETWEEN 3 AND 200),
  reviewed_source_sha256 text NOT NULL CHECK(reviewed_source_sha256 ~ '^[0-9a-f]{64}$'),
  decision text NOT NULL CHECK(decision IN ('APPROVE','REJECT','REQUEST_REVISION')),
  detached_signature_sha256 text NOT NULL CHECK(detached_signature_sha256 ~ '^[0-9a-f]{64}$'),
  attestation bytes NOT NULL,
  verification_state text NOT NULL DEFAULT 'AWAITING_EXTERNAL_CREDENTIAL_ISSUER'
    CHECK(verification_state='AWAITING_EXTERNAL_CREDENTIAL_ISSUER'),
  authority_released boolean NOT NULL DEFAULT false CHECK(authority_released=false),
  inserted_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE(candidate_id,reviewer_id)
);
CREATE TABLE abc.eng05_professional_conflict_dossiers (
  dossier_id uuid PRIMARY KEY,
  source_set_sha256 text NOT NULL CHECK(source_set_sha256 ~ '^[0-9a-f]{64}$'),
  dossier_bytes bytea NOT NULL CHECK(octet_length(dossier_bytes) BETWEEN 64 AND 65536),
  dossier_sha256 text NOT NULL CHECK(dossier_sha256=encode(sha256(dossier_bytes),'hex')),
  status text NOT NULL CHECK(status IN (
    'BLOCKED_QUALIFICATION','BLOCKED_CONFLICT','REVIEWED_NON_EXECUTABLE')),
  eng06_release_authorized boolean NOT NULL DEFAULT false
    CHECK(eng06_release_authorized=false),
  recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
-- Historical source and approval snapshots must be append-only. Changes
-- require an explicitly new source_version/review/dossier; no retroactive
-- specialist forgery or post-signoff mutation is permitted.
CREATE FUNCTION abc.eng05_professional_append_only()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,abc
AS $guard$
BEGIN
  RAISE EXCEPTION 'ENG05 evidence/reviewer snapshot immutable'
    USING ERRCODE='42501';
END;$guard$;
DO $protection$
DECLARE t text;
BEGIN
 FOREACH t IN ARRAY ARRAY[
   'eng05_professional_source_candidates',
   'eng05_professional_review_attestations',
   'eng05_professional_conflict_dossiers'
 ] LOOP
  EXECUTE format('ALTER TABLE abc.%I ENABLE ROW LEVEL SECURITY',t);
  EXECUTE format('ALTER TABLE abc.%I FORCE ROW LEVEL SECURITY',t);
  EXECUTE format('REVOKE ALL ON abc.%I FROM PUBLIC,abc_app,abc_worker,abc_answer_worker,abc_orchestrator,abc_eng03_worker,abc_pipeline_worker,abc_eng04_worker,abc_eng05_worker,abc_eng06_review_worker',t);
  EXECUTE format('CREATE TRIGGER eng05_snapshot_immutable BEFORE UPDATE OR DELETE ON abc.%I FOR EACH ROW EXECUTE FUNCTION abc.eng05_professional_append_only()',t);
  IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='abc_staging_migrator') THEN
   EXECUTE format('CREATE POLICY eng05_migrator_review_only ON abc.%I FOR ALL TO abc_staging_migrator USING(true) WITH CHECK(true)',t);
  END IF;
 END LOOP;
END;$protection$;
REVOKE ALL ON FUNCTION abc.eng05_professional_append_only() FROM PUBLIC;
COMMIT;

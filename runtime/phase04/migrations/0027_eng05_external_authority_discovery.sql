-- 0027: ENG05 publicly identified references and external-issuer packets.
-- DISCOVERY_ONLY. No external authority connected, no rights-cleared bytes,
-- no accepted professional evidence or live ENG06 decision input.
BEGIN;
CREATE TABLE abc.eng05_official_reference_discovery (
 reference_id text PRIMARY KEY CHECK(length(reference_id) BETWEEN 6 AND 128),
 scope text NOT NULL CHECK(scope='HAIR_COLOR'),
 jurisdiction text NOT NULL CHECK(jurisdiction='EU'),
 publisher text NOT NULL CHECK(length(publisher) BETWEEN 3 AND 200),
 source_url text NOT NULL CHECK(source_url ~
    '^https://(single-market-economy[.]ec[.]europa[.]eu|echa[.]europa[.]eu|eur-lex[.]europa[.]eu)/'),
 reference_sha256 text NOT NULL CHECK(reference_sha256 ~ '^[0-9a-f]{64}$'),
 reference_bytes bytea NOT NULL CHECK(octet_length(reference_bytes) BETWEEN 128 AND 8192),
 documentation_state text NOT NULL DEFAULT 'REFERENCE_ONLY'
    CHECK(documentation_state='REFERENCE_ONLY'),
 source_bytes_verified boolean NOT NULL DEFAULT false
    CHECK(source_bytes_verified=false),
 republication_rights_verified boolean NOT NULL DEFAULT false
    CHECK(republication_rights_verified=false),
 specialist_approved boolean NOT NULL DEFAULT false
    CHECK(specialist_approved=false),
 engagement_authorized boolean NOT NULL DEFAULT false
    CHECK(engagement_authorized=false),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(source_url),
 CHECK(reference_sha256=encode(sha256(reference_bytes),'hex'))
);
CREATE TABLE abc.eng05_external_issuer_review_packets (
 packet_id uuid PRIMARY KEY,
 issuer_id text NOT NULL CHECK(length(issuer_id) BETWEEN 5 AND 200),
 issuer_manifest_sha256 text NOT NULL CHECK(issuer_manifest_sha256 ~ '^[0-9a-f]{64}$'),
 issuer_manifest_bytes bytea NOT NULL CHECK(octet_length(issuer_manifest_bytes) BETWEEN 128 AND 65536),
 submitted_signature bytea NOT NULL CHECK(octet_length(submitted_signature)=64),
 issuer_public_key_fingerprint text NOT NULL
   CHECK(issuer_public_key_fingerprint ~ '^[0-9a-f]{64}$'),
 external_authority_verified boolean NOT NULL DEFAULT false
   CHECK(external_authority_verified=false),
 professional_signoff_accepted boolean NOT NULL DEFAULT false
   CHECK(professional_signoff_accepted=false),
 eng06_release_authorized boolean NOT NULL DEFAULT false
   CHECK(eng06_release_authorized=false),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK(issuer_manifest_sha256=encode(sha256(issuer_manifest_bytes),'hex'))
);
DO $guard$
DECLARE t text;
BEGIN
 FOREACH t IN ARRAY ARRAY['eng05_official_reference_discovery',
                           'eng05_external_issuer_review_packets'] LOOP
  EXECUTE format('ALTER TABLE abc.%I ENABLE ROW LEVEL SECURITY',t);
  EXECUTE format('ALTER TABLE abc.%I FORCE ROW LEVEL SECURITY',t);
  EXECUTE format('REVOKE ALL ON abc.%I FROM PUBLIC,abc_app,abc_worker,abc_answer_worker,abc_orchestrator,abc_eng03_worker,abc_pipeline_worker,abc_eng04_worker,abc_eng05_worker,abc_eng06_review_worker',t);
  EXECUTE format('CREATE TRIGGER eng05_reference_snapshot_immutable BEFORE UPDATE OR DELETE ON abc.%I FOR EACH ROW EXECUTE FUNCTION abc.eng05_professional_append_only()',t);
  IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='abc_staging_migrator') THEN
    EXECUTE format('CREATE POLICY eng05_migrator_reference_review ON abc.%I FOR ALL TO abc_staging_migrator USING(true) WITH CHECK(true)',t);
  END IF;
 END LOOP;
END;$guard$;
COMMIT;

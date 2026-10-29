-- Phase 04 migration 0005: immutable consent evidence and auditable transitions.
-- Independent client evidence verification is NOT implemented in this migration.
BEGIN;
ALTER TABLE abc.consent_evidence
  ADD COLUMN IF NOT EXISTS valid_until timestamptz;

ALTER TABLE abc.consent_evidence
  ADD CONSTRAINT consent_active_requires_bounded_validity
  CHECK(status <> 'ACTIVE' OR (
      verified_at IS NOT NULL AND valid_until IS NOT NULL
      AND revoked_at IS NULL AND length(evidence_digest) >= 12
      AND length(retention_policy_id) > 0));

CREATE TABLE IF NOT EXISTS abc.consent_status_audit(
  audit_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  consent_id uuid NOT NULL REFERENCES abc.consent_evidence(consent_id),
  before_status text,
  after_status text NOT NULL,
  db_role text NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE OR REPLACE FUNCTION abc.guard_consent_lifecycle()
RETURNS trigger LANGUAGE plpgsql AS $abc_consent$
BEGIN
  IF TG_OP='INSERT' THEN
    IF NEW.status <> 'PENDING_VERIFICATION' OR NEW.verified_at IS NOT NULL
      OR NEW.revoked_at IS NOT NULL OR NEW.valid_until IS NOT NULL THEN
      RAISE EXCEPTION 'new consent must begin pending verification'
      USING ERRCODE='23514';
    END IF;
  ELSE
    IF (OLD.tenant_id,OLD.branch_id,OLD.session_id,OLD.client_id,
        OLD.purpose,OLD.evidence_digest,OLD.disclosure_version,
        OLD.retention_policy_id)
       IS DISTINCT FROM
       (NEW.tenant_id,NEW.branch_id,NEW.session_id,NEW.client_id,
        NEW.purpose,NEW.evidence_digest,NEW.disclosure_version,
        NEW.retention_policy_id) THEN
      RAISE EXCEPTION 'original consent evidence and scope immutable'
      USING ERRCODE='23514';
    END IF;
    IF OLD.status IN ('WITHDRAWN','EXPIRED') THEN
      RAISE EXCEPTION 'terminal consent must never be reactivated'
      USING ERRCODE='23514';
    END IF;
    IF NEW.status NOT IN ('ACTIVE','WITHDRAWN','EXPIRED')
       AND NEW.status IS DISTINCT FROM OLD.status THEN
      RAISE EXCEPTION 'invalid consent transition'
      USING ERRCODE='23514';
    END IF;
    IF NEW.status='ACTIVE' AND (OLD.status <> 'PENDING_VERIFICATION'
       OR NEW.verified_at IS NULL OR NEW.valid_until <= clock_timestamp()) THEN
      RAISE EXCEPTION 'activation requires verified and unexpired evidence'
      USING ERRCODE='23514';
    END IF;
    IF NEW.status='WITHDRAWN' AND NEW.revoked_at IS NULL THEN
      RAISE EXCEPTION 'withdrawal must be timestamped'
      USING ERRCODE='23514';
    END IF;
    IF NEW.status='ACTIVE' AND NEW.revoked_at IS NOT NULL THEN
      RAISE EXCEPTION 'revoked consent cannot be active'
      USING ERRCODE='23514';
    END IF;
    IF OLD.status='ACTIVE' AND NEW.status='ACTIVE'
       AND (OLD.valid_until,OLD.verified_at) IS DISTINCT FROM
           (NEW.valid_until,NEW.verified_at) THEN
      RAISE EXCEPTION 'active consent validity cannot be extended'
      USING ERRCODE='23514';
    END IF;
  END IF;
  RETURN NEW;
END
$abc_consent$;

DROP TRIGGER IF EXISTS trg_guard_consent ON abc.consent_evidence;
CREATE TRIGGER trg_guard_consent
  BEFORE INSERT OR UPDATE ON abc.consent_evidence
  FOR EACH ROW EXECUTE FUNCTION abc.guard_consent_lifecycle();

CREATE OR REPLACE FUNCTION abc.log_consent_transition()
RETURNS trigger LANGUAGE plpgsql AS $abc_consent_audit$
BEGIN
  IF TG_OP='INSERT' OR OLD.status IS DISTINCT FROM NEW.status THEN
    INSERT INTO abc.consent_status_audit(consent_id,before_status,after_status,db_role)
    VALUES(NEW.consent_id,CASE WHEN TG_OP='INSERT' THEN NULL ELSE OLD.status END,
           NEW.status,current_user);
  END IF;
  RETURN NULL;
END
$abc_consent_audit$;

DROP TRIGGER IF EXISTS trg_log_consent ON abc.consent_evidence;
CREATE TRIGGER trg_log_consent
  AFTER INSERT OR UPDATE ON abc.consent_evidence
  FOR EACH ROW EXECUTE FUNCTION abc.log_consent_transition();

ALTER TABLE abc.consent_status_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.consent_status_audit FORCE ROW LEVEL SECURITY;
REVOKE ALL ON abc.consent_status_audit FROM PUBLIC,abc_app,abc_worker;
COMMIT;

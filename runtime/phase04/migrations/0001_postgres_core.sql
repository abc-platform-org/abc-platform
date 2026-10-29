-- ABC-MEP-01.1 Phase 04 / 0001: reviewed bootstrap candidate, PostgreSQL 16+
-- Apply as privileged migration identity, NEVER from runtime HTTP handler.
-- Runtime role abc_app must be created first with NO SUPERUSER/BYPASSRLS/CREATEROLE.
BEGIN;
CREATE SCHEMA IF NOT EXISTS abc;
REVOKE ALL ON SCHEMA abc FROM PUBLIC;
GRANT USAGE ON SCHEMA abc TO abc_app;

CREATE TABLE IF NOT EXISTS abc.tenants (
  tenant_id text PRIMARY KEY CHECK(length(tenant_id) BETWEEN 1 AND 128)
);
CREATE TABLE IF NOT EXISTS abc.branches (
  tenant_id text NOT NULL REFERENCES abc.tenants(tenant_id),
  branch_id text NOT NULL CHECK(length(branch_id) BETWEEN 1 AND 128),
  PRIMARY KEY(tenant_id, branch_id)
);
CREATE TABLE IF NOT EXISTS abc.memberships (
  issuer text NOT NULL,
  subject text NOT NULL,
  tenant_id text NOT NULL,
  branch_id text NOT NULL,
  role text NOT NULL CHECK (role IN ('SPECIALIST','RECEPTION','SALON_MANAGER','ORG_OWNER','PLATFORM_OPERATOR')),
  active boolean NOT NULL DEFAULT false,
  verified_qualification boolean NOT NULL DEFAULT false,
  PRIMARY KEY (issuer, subject, tenant_id, branch_id, role),
  FOREIGN KEY(tenant_id, branch_id) REFERENCES abc.branches(tenant_id, branch_id)
);
CREATE INDEX IF NOT EXISTS memberships_identity ON abc.memberships(issuer,subject,active);

CREATE TABLE IF NOT EXISTS abc.sessions (
  session_id uuid PRIMARY KEY,
  tenant_id text NOT NULL,
  branch_id text NOT NULL,
  specialist_id text NOT NULL,
  client_id text,
  appointment_id text,
  service_id text,
  state text NOT NULL CHECK(state IN ('CREATED','PAUSED')),
  state_version integer NOT NULL CHECK(state_version >= 0),
  checkpoint text,
  created_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL,
  last_event_id uuid NOT NULL,
  FOREIGN KEY(tenant_id, branch_id) REFERENCES abc.branches(tenant_id,branch_id)
);
CREATE INDEX IF NOT EXISTS session_scope ON abc.sessions(tenant_id,branch_id,specialist_id);

CREATE TABLE IF NOT EXISTS abc.idempotency (
  tenant_id text NOT NULL REFERENCES abc.tenants(tenant_id),
  actor_id text NOT NULL,
  operation text NOT NULL,
  request_key text NOT NULL,
  fingerprint text NOT NULL,
  response_json jsonb NOT NULL,
  PRIMARY KEY(tenant_id,actor_id,operation,request_key)
);
CREATE TABLE IF NOT EXISTS abc.outbox (
  event_id uuid PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES abc.tenants(tenant_id),
  aggregate_id uuid NOT NULL REFERENCES abc.sessions(session_id),
  aggregate_version integer NOT NULL,
  event_json jsonb NOT NULL,
  created_at timestamptz NOT NULL,
  UNIQUE(aggregate_id,aggregate_version)
);
CREATE TABLE IF NOT EXISTS abc.consent_evidence (
  consent_id uuid PRIMARY KEY,
  tenant_id text NOT NULL,
  branch_id text NOT NULL,
  session_id uuid NOT NULL REFERENCES abc.sessions(session_id),
  client_id text NOT NULL,
  status text NOT NULL CHECK(status IN ('PENDING_VERIFICATION','ACTIVE','WITHDRAWN','EXPIRED')),
  purpose text[] NOT NULL CHECK(cardinality(purpose)>0),
  evidence_digest text NOT NULL,
  disclosure_version text NOT NULL,
  retention_policy_id text NOT NULL,
  verified_at timestamptz,
  revoked_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY(tenant_id,branch_id) REFERENCES abc.branches(tenant_id,branch_id),
  CHECK(status != 'ACTIVE' OR verified_at IS NOT NULL)
);
CREATE UNIQUE INDEX IF NOT EXISTS one_live_consent_per_session ON abc.consent_evidence(session_id)
WHERE status IN ('PENDING_VERIFICATION','ACTIVE');

-- Sensitive rows must also be restricted by DB, not just frontend code.
ALTER TABLE abc.memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.memberships FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS abc_membership_self ON abc.memberships;
CREATE POLICY abc_membership_self ON abc.memberships FOR SELECT TO abc_app
  USING (issuer = current_setting('abc.issuer',true)
    AND subject = current_setting('abc.subject',true)
    AND active = true);

ALTER TABLE abc.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.sessions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS abc_session_scope ON abc.sessions;
CREATE POLICY abc_session_scope ON abc.sessions FOR ALL TO abc_app
  USING (tenant_id = current_setting('abc.tenant',true)
    AND branch_id = current_setting('abc.branch',true)
    AND specialist_id = current_setting('abc.subject',true))
  WITH CHECK (tenant_id = current_setting('abc.tenant',true)
    AND branch_id = current_setting('abc.branch',true)
    AND specialist_id = current_setting('abc.subject',true));

ALTER TABLE abc.idempotency ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.idempotency FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS abc_idempotency_scope ON abc.idempotency;
CREATE POLICY abc_idempotency_scope ON abc.idempotency FOR ALL TO abc_app
  USING (tenant_id = current_setting('abc.tenant',true)
    AND actor_id = current_setting('abc.subject',true))
  WITH CHECK (tenant_id = current_setting('abc.tenant',true)
    AND actor_id = current_setting('abc.subject',true));

ALTER TABLE abc.outbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.outbox FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS abc_outbox_scope ON abc.outbox;
CREATE POLICY abc_outbox_scope ON abc.outbox FOR ALL TO abc_app
  USING (tenant_id = current_setting('abc.tenant',true))
  WITH CHECK(tenant_id = current_setting('abc.tenant',true));

ALTER TABLE abc.consent_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.consent_evidence FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS abc_consent_scope ON abc.consent_evidence;
CREATE POLICY abc_consent_scope ON abc.consent_evidence FOR SELECT TO abc_app
  USING (tenant_id = current_setting('abc.tenant',true)
    AND branch_id = current_setting('abc.branch',true));
-- No runtime write policy: evidence must be verified by a future segregated service.

REVOKE ALL ON ALL TABLES IN SCHEMA abc FROM PUBLIC;
GRANT SELECT ON abc.memberships TO abc_app;
GRANT SELECT ON abc.tenants,abc.branches TO abc_app;
GRANT SELECT,INSERT,UPDATE ON abc.sessions,abc.idempotency,abc.outbox TO abc_app;
GRANT SELECT ON abc.consent_evidence TO abc_app;
COMMIT;

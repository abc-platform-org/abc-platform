-- ENG01/ENG02 secure, synthetic-only cross-engine boundary / migration 0008.
-- abc_orchestrator is a distinct NO-BYPASSRLS DB identity; not abc_app or abc_worker.
-- Only privileged migrator/admin may provision/disable engine workload grants.
BEGIN;
GRANT USAGE ON SCHEMA abc TO abc_orchestrator;
GRANT SELECT ON abc.memberships TO abc_orchestrator;
DROP POLICY IF EXISTS abc_membership_orchestrator_self ON abc.memberships;
CREATE POLICY abc_membership_orchestrator_self ON abc.memberships
  FOR SELECT TO abc_orchestrator USING (
    issuer=current_setting('abc.issuer',true)
    AND subject=current_setting('abc.subject',true) AND active=true
    AND role='SPECIALIST');

GRANT SELECT ON abc.sessions TO abc_orchestrator;
GRANT UPDATE(state_version,updated_at,last_event_id) ON abc.sessions TO abc_orchestrator;
DROP POLICY IF EXISTS abc_session_orchestrator_select ON abc.sessions;
CREATE POLICY abc_session_orchestrator_select ON abc.sessions
  FOR SELECT TO abc_orchestrator USING (
    tenant_id=current_setting('abc.tenant',true)
    AND branch_id=current_setting('abc.branch',true)
    AND specialist_id=current_setting('abc.subject',true)
    AND EXISTS (SELECT 1 FROM abc.memberships m WHERE
      m.issuer=current_setting('abc.issuer',true)
      AND m.subject=current_setting('abc.subject',true)
      AND m.tenant_id=abc.sessions.tenant_id
      AND m.branch_id=abc.sessions.branch_id
      AND m.role='SPECIALIST' AND m.active=true));
DROP POLICY IF EXISTS abc_session_orchestrator_update ON abc.sessions;
CREATE POLICY abc_session_orchestrator_update ON abc.sessions
  FOR UPDATE TO abc_orchestrator
  USING (tenant_id=current_setting('abc.tenant',true)
    AND branch_id=current_setting('abc.branch',true)
    AND specialist_id=current_setting('abc.subject',true))
  WITH CHECK (tenant_id=current_setting('abc.tenant',true)
    AND branch_id=current_setting('abc.branch',true)
    AND specialist_id=current_setting('abc.subject',true));

-- This policy controls inserts only; the general worker may read the outbox but
-- cannot act as ENG02, and the HTTP app does not obtain the grant registry.
DROP POLICY IF EXISTS abc_outbox_orchestrator_insert ON abc.outbox;
CREATE POLICY abc_outbox_orchestrator_insert ON abc.outbox
  FOR INSERT TO abc_orchestrator WITH CHECK (
    tenant_id=current_setting('abc.tenant',true));
GRANT INSERT ON abc.outbox TO abc_orchestrator;

CREATE TABLE IF NOT EXISTS abc.engine_workload_grants (
    issuer text NOT NULL,
    service_subject text NOT NULL,
    engine_id text NOT NULL CHECK(engine_id='ENG-02'),
    tenant_id text NOT NULL,
    branch_id text NOT NULL,
    permission text NOT NULL CHECK(permission='ENG02_RECORD_ANSWER'),
    active boolean NOT NULL DEFAULT false,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(issuer,service_subject,engine_id,tenant_id,branch_id,permission),
    FOREIGN KEY(tenant_id,branch_id) REFERENCES abc.branches(tenant_id,branch_id)
);
ALTER TABLE abc.engine_workload_grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.engine_workload_grants FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS eng01_read_workload_grants ON abc.engine_workload_grants;
CREATE POLICY eng01_read_workload_grants ON abc.engine_workload_grants
    FOR SELECT TO abc_orchestrator
    USING (active AND tenant_id=current_setting('abc.tenant',true)
      AND branch_id=current_setting('abc.branch',true));
REVOKE ALL ON abc.engine_workload_grants FROM PUBLIC,abc_app,abc_worker;
GRANT SELECT ON abc.engine_workload_grants TO abc_orchestrator;

CREATE TABLE IF NOT EXISTS abc.eng02_answers (
    tenant_id text NOT NULL,
    branch_id text NOT NULL,
    session_id uuid NOT NULL REFERENCES abc.sessions(session_id),
    question_profile_version text NOT NULL,
    question_id text NOT NULL,
    value text NOT NULL,
    answer_source text NOT NULL CHECK(answer_source IN ('CLIENT','SPECIALIST')),
    actor_id text NOT NULL,
    answer_id uuid NOT NULL,
    aggregate_version integer NOT NULL CHECK(aggregate_version>0),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(tenant_id,session_id,question_profile_version,question_id),
    UNIQUE(session_id,aggregate_version),
    UNIQUE(answer_id),
    FOREIGN KEY(tenant_id,branch_id) REFERENCES abc.branches(tenant_id,branch_id)
);
ALTER TABLE abc.eng02_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.eng02_answers FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS eng02_scoped_answer_write ON abc.eng02_answers;
CREATE POLICY eng02_scoped_answer_write ON abc.eng02_answers TO abc_orchestrator
    USING (tenant_id=current_setting('abc.tenant',true)
      AND branch_id=current_setting('abc.branch',true)
      AND actor_id=current_setting('abc.subject',true))
    WITH CHECK (tenant_id=current_setting('abc.tenant',true)
      AND branch_id=current_setting('abc.branch',true)
      AND actor_id=current_setting('abc.subject',true));
REVOKE ALL ON abc.eng02_answers FROM PUBLIC,abc_app,abc_worker;
GRANT SELECT,INSERT ON abc.eng02_answers TO abc_orchestrator;

CREATE TABLE IF NOT EXISTS abc.eng02_command_receipts (
    command_id uuid NOT NULL,
    tenant_id text NOT NULL,
    branch_id text NOT NULL,
    session_id uuid NOT NULL REFERENCES abc.sessions(session_id),
    actor_id text NOT NULL,
    service_issuer text NOT NULL,
    service_subject text NOT NULL,
    request_digest char(64) NOT NULL,
    event_id uuid NOT NULL REFERENCES abc.outbox(event_id),
    response_json jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(tenant_id,command_id),
    FOREIGN KEY(tenant_id,branch_id) REFERENCES abc.branches(tenant_id,branch_id)
);
ALTER TABLE abc.eng02_command_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.eng02_command_receipts FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS eng02_scoped_receipt ON abc.eng02_command_receipts;
CREATE POLICY eng02_scoped_receipt ON abc.eng02_command_receipts TO abc_orchestrator
    USING (tenant_id=current_setting('abc.tenant',true)
       AND branch_id=current_setting('abc.branch',true)
       AND actor_id=current_setting('abc.subject',true))
    WITH CHECK (tenant_id=current_setting('abc.tenant',true)
       AND branch_id=current_setting('abc.branch',true)
       AND actor_id=current_setting('abc.subject',true));
REVOKE ALL ON abc.eng02_command_receipts FROM PUBLIC,abc_app,abc_worker;
GRANT SELECT,INSERT ON abc.eng02_command_receipts TO abc_orchestrator;
COMMIT;

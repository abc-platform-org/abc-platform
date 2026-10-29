-- ABC Phase 04 / 0002: internal checkpoint audit, no addition to frozen v1 events.
BEGIN;
CREATE TABLE IF NOT EXISTS abc.state_audit (
  audit_id uuid PRIMARY KEY,
  tenant_id text NOT NULL,
  branch_id text NOT NULL,
  session_id uuid NOT NULL REFERENCES abc.sessions(session_id),
  from_state text NOT NULL,
  to_state text NOT NULL,
  from_version integer NOT NULL,
  to_version integer NOT NULL,
  actor_id text NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY(tenant_id,branch_id) REFERENCES abc.branches(tenant_id,branch_id),
  UNIQUE(session_id,to_version)
);
ALTER TABLE abc.state_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.state_audit FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS abc_state_audit_scope ON abc.state_audit;
CREATE POLICY abc_state_audit_scope ON abc.state_audit FOR ALL TO abc_app
  USING (tenant_id=current_setting('abc.tenant',true)
    AND branch_id=current_setting('abc.branch',true)
    AND actor_id=current_setting('abc.subject',true))
  WITH CHECK(tenant_id=current_setting('abc.tenant',true)
    AND branch_id=current_setting('abc.branch',true)
    AND actor_id=current_setting('abc.subject',true));
REVOKE ALL ON abc.state_audit FROM PUBLIC;
GRANT SELECT,INSERT ON abc.state_audit TO abc_app;
COMMIT;

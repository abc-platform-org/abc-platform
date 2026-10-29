-- ENG01 internal typed command journal; does NOT change frozen v1 API/events.
BEGIN;
CREATE TABLE IF NOT EXISTS abc.eng01_command_receipts (
    command_id uuid NOT NULL,
    tenant_id text NOT NULL,
    branch_id text NOT NULL,
    actor_id text NOT NULL,
    session_id uuid NOT NULL REFERENCES abc.sessions(session_id),
    request_digest char(64) NOT NULL,
    correlation_id uuid NOT NULL,
    result_json jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (tenant_id,command_id),
    FOREIGN KEY (tenant_id,branch_id) REFERENCES abc.branches(tenant_id,branch_id)
);
CREATE INDEX IF NOT EXISTS eng01_receipt_session_scope ON abc.eng01_command_receipts(tenant_id,branch_id,session_id);
ALTER TABLE abc.eng01_command_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.eng01_command_receipts FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS eng01_command_scope ON abc.eng01_command_receipts;
CREATE POLICY eng01_command_scope ON abc.eng01_command_receipts TO abc_app
  USING (tenant_id=current_setting('abc.tenant',true)
     AND branch_id=current_setting('abc.branch',true)
     AND actor_id=current_setting('abc.subject',true))
  WITH CHECK (tenant_id=current_setting('abc.tenant',true)
     AND branch_id=current_setting('abc.branch',true)
     AND actor_id=current_setting('abc.subject',true));
REVOKE ALL ON abc.eng01_command_receipts FROM PUBLIC;
GRANT SELECT,INSERT ON abc.eng01_command_receipts TO abc_app;
-- Explicitly deny worker access; schema USAGE alone is insufficient for table access.
REVOKE ALL ON abc.eng01_command_receipts FROM abc_worker;
COMMIT;

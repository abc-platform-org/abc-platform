-- Phase 04 migration 0006: real idempotent internal event read-model sink.
-- Only SESSION_CREATED. No photos, client identities, billing or model output.
BEGIN;
CREATE TABLE IF NOT EXISTS abc.session_index_projection (
  consumer_id text NOT NULL,
  event_id uuid NOT NULL REFERENCES abc.outbox(event_id),
  tenant_id text NOT NULL,
  branch_id text NOT NULL,
  session_id uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (consumer_id,event_id),
  UNIQUE(consumer_id,session_id),
  FOREIGN KEY(consumer_id,tenant_id)
    REFERENCES abc.worker_subscriptions(consumer_id,tenant_id),
  FOREIGN KEY(tenant_id,branch_id) REFERENCES abc.branches(tenant_id,branch_id)
);
ALTER TABLE abc.session_index_projection ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.session_index_projection FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS abc_session_index_worker_write ON abc.session_index_projection;
CREATE POLICY abc_session_index_worker_write ON abc.session_index_projection
  FOR INSERT TO abc_worker WITH CHECK (
    EXISTS(SELECT 1 FROM abc.worker_subscriptions sub
           WHERE sub.consumer_id=abc.session_index_projection.consumer_id
             AND sub.tenant_id=abc.session_index_projection.tenant_id
             AND sub.active=true
             AND sub.event_type='SESSION_CREATED')
  );
REVOKE ALL ON abc.session_index_projection FROM PUBLIC,abc_app;
GRANT INSERT ON abc.session_index_projection TO abc_worker;
COMMIT;

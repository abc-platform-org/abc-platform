-- Phase04 migration 0003. Internal outbox dispatch only; no customer data.
-- abc_worker is a separate, trusted backend identity, NOT the HTTP role.
BEGIN;
CREATE TABLE IF NOT EXISTS abc.event_delivery (
  consumer_id text NOT NULL CHECK (length(consumer_id) BETWEEN 3 AND 64),
  event_id uuid NOT NULL REFERENCES abc.outbox(event_id),
  tenant_id text NOT NULL REFERENCES abc.tenants(tenant_id),
  state text NOT NULL DEFAULT 'PENDING' CHECK (state IN ('PENDING','LEASED','ACKED','DLQ')),
  attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  lease_token uuid,
  lease_until timestamptz,
  next_attempt_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  error_code text,
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (consumer_id,event_id),
  CHECK(state <> 'LEASED' OR (lease_token IS NOT NULL AND lease_until IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS event_delivery_ready
  ON abc.event_delivery(consumer_id,state,next_attempt_at,updated_at);

ALTER TABLE abc.event_delivery ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.event_delivery FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS abc_delivery_worker ON abc.event_delivery;
CREATE POLICY abc_delivery_worker ON abc.event_delivery FOR ALL TO abc_worker
  USING (true) WITH CHECK (true);

-- Outbox publisher may read the event envelope but cannot alter it.
DROP POLICY IF EXISTS abc_outbox_worker_read ON abc.outbox;
CREATE POLICY abc_outbox_worker_read ON abc.outbox
  FOR SELECT TO abc_worker USING (true);

GRANT USAGE ON SCHEMA abc TO abc_worker;
GRANT SELECT ON abc.outbox TO abc_worker;
GRANT SELECT,INSERT,UPDATE ON abc.event_delivery TO abc_worker;
-- Explicitly no access to sessions, consent evidence, membership or idempotency.
REVOKE ALL ON abc.sessions,abc.memberships,abc.consent_evidence,abc.idempotency
  FROM abc_worker;
COMMIT;

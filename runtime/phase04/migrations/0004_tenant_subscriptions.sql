-- Phase 04 migration 0004: admin-provisioned tenant-scoped subscriptions.
BEGIN;
CREATE TABLE IF NOT EXISTS abc.worker_subscriptions(
  consumer_id text PRIMARY KEY CHECK(length(consumer_id) BETWEEN 3 AND 64),
  tenant_id text NOT NULL REFERENCES abc.tenants(tenant_id),
  event_type text NOT NULL CHECK(event_type='SESSION_CREATED'),
  active boolean NOT NULL DEFAULT false,
  UNIQUE(consumer_id,tenant_id)
);
ALTER TABLE abc.worker_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.worker_subscriptions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS abc_worker_subscriptions_read ON abc.worker_subscriptions;
CREATE POLICY abc_worker_subscriptions_read ON abc.worker_subscriptions
  FOR SELECT TO abc_worker USING (active=true);
GRANT SELECT ON abc.worker_subscriptions TO abc_worker;
REVOKE INSERT,UPDATE,DELETE ON abc.worker_subscriptions FROM abc_worker;
ALTER TABLE abc.event_delivery
  ADD CONSTRAINT delivery_subscription_scope
  FOREIGN KEY(consumer_id,tenant_id)
  REFERENCES abc.worker_subscriptions(consumer_id,tenant_id);
COMMIT;

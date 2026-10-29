-- 0009: Dedicated ANSWER_RECORDED worker and synthetic ENG14 audit gate.
-- No changes to frozen Phase02 contracts, prior migration hashes or customer mode.
BEGIN;
ALTER TABLE abc.worker_subscriptions
    DROP CONSTRAINT worker_subscriptions_event_type_check;
ALTER TABLE abc.worker_subscriptions
    ADD CONSTRAINT worker_subscriptions_event_type_check
    CHECK(event_type IN ('SESSION_CREATED','ANSWER_RECORDED'));

GRANT USAGE ON SCHEMA abc TO abc_answer_worker;
GRANT SELECT ON abc.worker_subscriptions TO abc_answer_worker;
DROP POLICY IF EXISTS abc_answer_subscription_only ON abc.worker_subscriptions;
CREATE POLICY abc_answer_subscription_only ON abc.worker_subscriptions
  FOR SELECT TO abc_answer_worker USING (
    active=true AND event_type='ANSWER_RECORDED'
    AND consumer_id=current_setting('abc.consumer_id',true));

GRANT SELECT ON abc.outbox TO abc_answer_worker;
DROP POLICY IF EXISTS abc_answer_outbox_read ON abc.outbox;
CREATE POLICY abc_answer_outbox_read ON abc.outbox
  FOR SELECT TO abc_answer_worker USING (
    event_json->>'event_type'='ANSWER_RECORDED'
    AND EXISTS (SELECT 1 FROM abc.worker_subscriptions sub
      WHERE sub.tenant_id=abc.outbox.tenant_id
        AND sub.consumer_id=current_setting('abc.consumer_id',true)
        AND sub.active=true AND sub.event_type='ANSWER_RECORDED'));

GRANT SELECT,INSERT,UPDATE ON abc.event_delivery TO abc_answer_worker;
DROP POLICY IF EXISTS abc_answer_delivery_scope ON abc.event_delivery;
CREATE POLICY abc_answer_delivery_scope ON abc.event_delivery
  FOR ALL TO abc_answer_worker
  USING (consumer_id=current_setting('abc.consumer_id',true)
    AND EXISTS (SELECT 1 FROM abc.worker_subscriptions sub
      WHERE sub.consumer_id=abc.event_delivery.consumer_id
       AND sub.tenant_id=abc.event_delivery.tenant_id
       AND sub.active=true AND sub.event_type='ANSWER_RECORDED'))
  WITH CHECK (consumer_id=current_setting('abc.consumer_id',true)
    AND EXISTS (SELECT 1 FROM abc.worker_subscriptions sub
      WHERE sub.consumer_id=abc.event_delivery.consumer_id
       AND sub.tenant_id=abc.event_delivery.tenant_id
       AND sub.active=true AND sub.event_type='ANSWER_RECORDED'));

CREATE TABLE abc.answer_index_projection (
    consumer_id text NOT NULL,
    event_id uuid NOT NULL REFERENCES abc.outbox(event_id),
    tenant_id text NOT NULL,
    branch_id text NOT NULL,
    session_id uuid NOT NULL,
    aggregate_version integer NOT NULL CHECK (aggregate_version > 0),
    question_id text NOT NULL CHECK(length(question_id) BETWEEN 1 AND 128),
    answer_id uuid NOT NULL,
    occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (consumer_id,event_id),
    UNIQUE (consumer_id,session_id,aggregate_version),
    FOREIGN KEY (consumer_id,tenant_id)
      REFERENCES abc.worker_subscriptions(consumer_id,tenant_id),
    FOREIGN KEY (tenant_id,branch_id)
      REFERENCES abc.branches(tenant_id,branch_id)
);
ALTER TABLE abc.answer_index_projection ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.answer_index_projection FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS abc_answer_projection_write ON abc.answer_index_projection;
CREATE POLICY abc_answer_projection_write ON abc.answer_index_projection
  FOR INSERT TO abc_answer_worker WITH CHECK (
    consumer_id=current_setting('abc.consumer_id',true)
    AND EXISTS (SELECT 1 FROM abc.worker_subscriptions sub
      WHERE sub.consumer_id=abc.answer_index_projection.consumer_id
        AND sub.tenant_id=abc.answer_index_projection.tenant_id
        AND sub.active=true AND sub.event_type='ANSWER_RECORDED'));
REVOKE ALL ON abc.answer_index_projection FROM PUBLIC,abc_app,abc_worker,abc_orchestrator;
GRANT INSERT ON abc.answer_index_projection TO abc_answer_worker;
REVOKE ALL ON abc.engine_workload_grants,abc.eng02_answers,abc.eng02_command_receipts,
    abc.sessions,abc.memberships,abc.consent_evidence,abc.eng01_command_receipts
    FROM abc_answer_worker;

-- The ENG14 control plane evaluates a synthetic-only policy and persists its
-- versioned proof INSIDE the same write transaction as the answer/outbox.
CREATE TABLE abc.eng14_policy_audit (
    decision_id uuid PRIMARY KEY,
    command_id uuid NOT NULL,
    tenant_id text NOT NULL,
    branch_id text NOT NULL,
    session_id uuid NOT NULL REFERENCES abc.sessions(session_id),
    actor_id text NOT NULL,
    aggregate_version integer NOT NULL CHECK (aggregate_version>0),
    policy_version text NOT NULL CHECK(policy_version='eng14.synthetic.1'),
    scope text NOT NULL CHECK(scope='QUESTION'),
    decision text NOT NULL CHECK(decision='ALLOW'),
    input_digest char(64) NOT NULL,
    evaluated_at timestamptz NOT NULL,
    UNIQUE(tenant_id,command_id),
    UNIQUE(session_id,aggregate_version),
    FOREIGN KEY(tenant_id,branch_id) REFERENCES abc.branches(tenant_id,branch_id)
);
ALTER TABLE abc.eng14_policy_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.eng14_policy_audit FORCE ROW LEVEL SECURITY;
CREATE POLICY abc_eng14_authz_own ON abc.eng14_policy_audit
  FOR ALL TO abc_orchestrator
  USING (tenant_id=current_setting('abc.tenant',true)
    AND branch_id=current_setting('abc.branch',true)
    AND actor_id=current_setting('abc.subject',true))
  WITH CHECK (tenant_id=current_setting('abc.tenant',true)
    AND branch_id=current_setting('abc.branch',true)
    AND actor_id=current_setting('abc.subject',true));
REVOKE ALL ON abc.eng14_policy_audit FROM PUBLIC,abc_app,abc_worker,abc_answer_worker;
GRANT SELECT,INSERT ON abc.eng14_policy_audit TO abc_orchestrator;

ALTER TABLE abc.eng02_answers ADD COLUMN policy_decision_id uuid;
ALTER TABLE abc.eng02_answers ADD CONSTRAINT eng02_policy_reference
    FOREIGN KEY(policy_decision_id) REFERENCES abc.eng14_policy_audit(decision_id);

CREATE FUNCTION abc.enforce_eng14_answer_policy() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,abc
AS $policy$
BEGIN
  IF NEW.policy_decision_id IS NULL OR NOT EXISTS (
     SELECT 1 FROM abc.eng14_policy_audit decision
      WHERE decision.decision_id=NEW.policy_decision_id
        AND decision.tenant_id=NEW.tenant_id AND decision.branch_id=NEW.branch_id
        AND decision.session_id=NEW.session_id
        AND decision.actor_id=NEW.actor_id
        AND decision.aggregate_version=NEW.aggregate_version
        AND decision.decision='ALLOW' AND decision.scope='QUESTION'
        AND decision.policy_version='eng14.synthetic.1'
  ) THEN
      RAISE EXCEPTION 'ENG14 policy proof required before answer write'
        USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END
$policy$;
CREATE TRIGGER abc_eng14_answer_insert_gate
  BEFORE INSERT ON abc.eng02_answers
  FOR EACH ROW EXECUTE FUNCTION abc.enforce_eng14_answer_policy();
-- No historical rows are retroactively declared compliant by this migration.
COMMIT;

-- 0010: Durable metadata-only handoff from subscribed ENG02 answer event to ENG03.
-- ENG03 analysis is not executed here; work remains QUEUED_PENDING_ENGINE.
BEGIN;
CREATE TABLE abc.eng03_input_jobs (
  job_id uuid PRIMARY KEY,
  consumer_id text NOT NULL,
  source_event_id uuid NOT NULL,
  tenant_id text NOT NULL,
  branch_id text NOT NULL,
  session_id uuid NOT NULL,
  aggregate_version integer NOT NULL CHECK (aggregate_version>0),
  status text NOT NULL DEFAULT 'QUEUED_PENDING_ENGINE'
    CHECK(status='QUEUED_PENDING_ENGINE'),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE(consumer_id,source_event_id),
  UNIQUE(consumer_id,session_id,aggregate_version),
  FOREIGN KEY(consumer_id,source_event_id)
    REFERENCES abc.answer_index_projection(consumer_id,event_id),
  FOREIGN KEY(consumer_id,tenant_id)
    REFERENCES abc.worker_subscriptions(consumer_id,tenant_id),
  FOREIGN KEY(tenant_id,branch_id)
    REFERENCES abc.branches(tenant_id,branch_id)
);
ALTER TABLE abc.eng03_input_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.eng03_input_jobs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS abc_eng03_handoff_scope ON abc.eng03_input_jobs;
CREATE POLICY abc_eng03_handoff_scope ON abc.eng03_input_jobs
  FOR INSERT TO abc_answer_worker WITH CHECK (
    consumer_id=current_setting('abc.consumer_id',true)
    AND EXISTS(SELECT 1 FROM abc.worker_subscriptions s
      WHERE s.consumer_id=abc.eng03_input_jobs.consumer_id
        AND s.tenant_id=abc.eng03_input_jobs.tenant_id
        AND s.active AND s.event_type='ANSWER_RECORDED'));
REVOKE ALL ON abc.eng03_input_jobs FROM PUBLIC,abc_app,abc_worker,abc_orchestrator;
GRANT INSERT ON abc.eng03_input_jobs TO abc_answer_worker;
COMMIT;

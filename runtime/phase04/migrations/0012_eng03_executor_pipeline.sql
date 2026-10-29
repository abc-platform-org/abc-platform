-- 0012: ENG03 independent durable executor + bounded ENG04/05/06 handoff.
-- Only synthetic ANSWER_RECORDED sources; no real client data permitted.
BEGIN;
GRANT USAGE ON SCHEMA abc TO abc_eng03_worker,abc_pipeline_worker;

CREATE TABLE abc.eng03_worker_bindings (
  worker_role name NOT NULL CHECK(worker_role IN ('abc_eng03_worker','abc_pipeline_worker')),
  consumer_id text NOT NULL,
  tenant_id text NOT NULL,
  active boolean NOT NULL DEFAULT false,
  PRIMARY KEY(worker_role,consumer_id,tenant_id),
  FOREIGN KEY(consumer_id,tenant_id)
    REFERENCES abc.worker_subscriptions(consumer_id,tenant_id)
);
ALTER TABLE abc.eng03_worker_bindings ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.eng03_worker_bindings FORCE ROW LEVEL SECURITY;
CREATE POLICY eng03_binding_self ON abc.eng03_worker_bindings
  FOR SELECT TO abc_eng03_worker,abc_pipeline_worker
  USING (worker_role=current_user AND active);
REVOKE ALL ON abc.eng03_worker_bindings FROM PUBLIC,abc_app,abc_worker,
   abc_answer_worker,abc_orchestrator;
GRANT SELECT ON abc.eng03_worker_bindings TO abc_eng03_worker,abc_pipeline_worker;

ALTER TABLE abc.eng03_input_jobs DROP CONSTRAINT eng03_input_jobs_status_check;
ALTER TABLE abc.eng03_input_jobs ADD CONSTRAINT eng03_input_jobs_status_check
  CHECK(status IN ('QUEUED_PENDING_ENGINE','LEASED','ACKED','DLQ'));
ALTER TABLE abc.eng03_input_jobs
  ADD COLUMN attempts integer NOT NULL DEFAULT 0 CHECK(attempts>=0),
  ADD COLUMN lease_token uuid,
  ADD COLUMN lease_until timestamptz,
  ADD COLUMN next_attempt_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  ADD COLUMN error_code text,
  ADD COLUMN updated_at timestamptz NOT NULL DEFAULT clock_timestamp();
ALTER TABLE abc.eng03_input_jobs ADD CONSTRAINT eng03_lease_state_ck
  CHECK(status<>'LEASED' OR (lease_token IS NOT NULL AND lease_until IS NOT NULL));
CREATE INDEX eng03_jobs_ready ON abc.eng03_input_jobs(status,next_attempt_at,updated_at);
CREATE POLICY eng03_executor_scope ON abc.eng03_input_jobs
  FOR ALL TO abc_eng03_worker
  USING(EXISTS (SELECT 1 FROM abc.eng03_worker_bindings b
    WHERE b.worker_role=current_user AND b.consumer_id=abc.eng03_input_jobs.consumer_id
      AND b.tenant_id=abc.eng03_input_jobs.tenant_id AND b.active))
  WITH CHECK(EXISTS (SELECT 1 FROM abc.eng03_worker_bindings b
    WHERE b.worker_role=current_user AND b.consumer_id=abc.eng03_input_jobs.consumer_id
      AND b.tenant_id=abc.eng03_input_jobs.tenant_id AND b.active));
GRANT SELECT ON abc.eng03_input_jobs TO abc_eng03_worker;
GRANT UPDATE(status,attempts,lease_token,lease_until,next_attempt_at,error_code,updated_at)
  ON abc.eng03_input_jobs TO abc_eng03_worker;
-- ENG03 worker cannot read answer table, user identities, or authorize itself.

CREATE TABLE abc.eng03_evidence_ledger (
  evidence_id uuid PRIMARY KEY,
  consumer_id text NOT NULL,
  source_job_id uuid NOT NULL REFERENCES abc.eng03_input_jobs(job_id),
  source_event_id uuid NOT NULL,
  source_answer_id uuid NOT NULL,
  policy_decision_id uuid NOT NULL,
  source_lease_token uuid NOT NULL,
  tenant_id text NOT NULL,
  branch_id text NOT NULL,
  session_id uuid NOT NULL,
  aggregate_version integer NOT NULL CHECK(aggregate_version>0),
  question_id text NOT NULL CHECK(question_id LIKE 'synthetic:%'),
  source_kind text NOT NULL CHECK(source_kind IN ('CLIENT','SPECIALIST')),
  evidence_json jsonb NOT NULL,
  evidence_digest char(64) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE(consumer_id,source_event_id),
  UNIQUE(consumer_id,session_id,aggregate_version),
  FOREIGN KEY(consumer_id,tenant_id)
    REFERENCES abc.worker_subscriptions(consumer_id,tenant_id)
);
ALTER TABLE abc.eng03_evidence_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.eng03_evidence_ledger FORCE ROW LEVEL SECURITY;
CREATE POLICY eng03_evidence_create_scope ON abc.eng03_evidence_ledger
  FOR INSERT TO abc_eng03_worker WITH CHECK(
    EXISTS(SELECT 1 FROM abc.eng03_worker_bindings b
      WHERE b.worker_role=current_user AND b.consumer_id=abc.eng03_evidence_ledger.consumer_id
        AND b.tenant_id=abc.eng03_evidence_ledger.tenant_id AND b.active));
CREATE POLICY eng03_evidence_analysis_scope ON abc.eng03_evidence_ledger
  FOR SELECT TO abc_pipeline_worker USING(
    EXISTS(SELECT 1 FROM abc.eng03_worker_bindings b
      WHERE b.worker_role=current_user AND b.consumer_id=abc.eng03_evidence_ledger.consumer_id
        AND b.tenant_id=abc.eng03_evidence_ledger.tenant_id AND b.active));
REVOKE ALL ON abc.eng03_evidence_ledger FROM PUBLIC,abc_app,abc_worker,
  abc_answer_worker,abc_orchestrator;
GRANT INSERT ON abc.eng03_evidence_ledger TO abc_eng03_worker;
GRANT SELECT ON abc.eng03_evidence_ledger TO abc_pipeline_worker;

CREATE TABLE abc.eng04_06_jobs (
  job_id uuid PRIMARY KEY,
  consumer_id text NOT NULL,
  source_job_id uuid NOT NULL REFERENCES abc.eng03_input_jobs(job_id),
  source_evidence_id uuid NOT NULL REFERENCES abc.eng03_evidence_ledger(evidence_id),
  tenant_id text NOT NULL,
  branch_id text NOT NULL,
  session_id uuid NOT NULL,
  aggregate_version integer NOT NULL CHECK(aggregate_version>0),
  status text NOT NULL DEFAULT 'QUEUED' CHECK(status IN ('QUEUED','LEASED','ACKED','DLQ')),
  attempts integer NOT NULL DEFAULT 0 CHECK(attempts>=0),
  lease_token uuid,
  lease_until timestamptz,
  next_attempt_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  error_code text,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE(consumer_id,source_job_id),
  UNIQUE(consumer_id,source_evidence_id),
  FOREIGN KEY(consumer_id,tenant_id)
    REFERENCES abc.worker_subscriptions(consumer_id,tenant_id),
  CHECK(status<>'LEASED' OR (lease_token IS NOT NULL AND lease_until IS NOT NULL))
);
ALTER TABLE abc.eng04_06_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.eng04_06_jobs FORCE ROW LEVEL SECURITY;
CREATE POLICY pipeline_job_write_from_eng03 ON abc.eng04_06_jobs
  FOR INSERT TO abc_eng03_worker WITH CHECK(
    EXISTS(SELECT 1 FROM abc.eng03_worker_bindings b
       WHERE b.worker_role=current_user AND b.consumer_id=abc.eng04_06_jobs.consumer_id
          AND b.tenant_id=abc.eng04_06_jobs.tenant_id AND b.active));
CREATE POLICY pipeline_job_execute ON abc.eng04_06_jobs
  FOR ALL TO abc_pipeline_worker
  USING(EXISTS(SELECT 1 FROM abc.eng03_worker_bindings b
       WHERE b.worker_role=current_user AND b.consumer_id=abc.eng04_06_jobs.consumer_id
          AND b.tenant_id=abc.eng04_06_jobs.tenant_id AND b.active))
  WITH CHECK(EXISTS(SELECT 1 FROM abc.eng03_worker_bindings b
       WHERE b.worker_role=current_user AND b.consumer_id=abc.eng04_06_jobs.consumer_id
          AND b.tenant_id=abc.eng04_06_jobs.tenant_id AND b.active));
REVOKE ALL ON abc.eng04_06_jobs FROM PUBLIC,abc_app,abc_worker,abc_answer_worker,abc_orchestrator;
GRANT INSERT ON abc.eng04_06_jobs TO abc_eng03_worker;
GRANT SELECT ON abc.eng04_06_jobs TO abc_pipeline_worker;
GRANT UPDATE(status,attempts,lease_token,lease_until,next_attempt_at,error_code,updated_at)
  ON abc.eng04_06_jobs TO abc_pipeline_worker;

CREATE TABLE abc.eng04_06_results (
  result_id uuid PRIMARY KEY,
  consumer_id text NOT NULL,
  source_pipeline_job_id uuid NOT NULL UNIQUE REFERENCES abc.eng04_06_jobs(job_id),
  tenant_id text NOT NULL,
  branch_id text NOT NULL,
  session_id uuid NOT NULL,
  aggregate_version integer NOT NULL CHECK(aggregate_version>0),
  source_evidence_digest char(64) NOT NULL,
  analysis_json jsonb NOT NULL,
  knowledge_json jsonb NOT NULL,
  decision_json jsonb NOT NULL,
  policy_version text NOT NULL CHECK(policy_version='eng14.synthetic.1'),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  FOREIGN KEY(consumer_id,tenant_id)
    REFERENCES abc.worker_subscriptions(consumer_id,tenant_id)
);
ALTER TABLE abc.eng04_06_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.eng04_06_results FORCE ROW LEVEL SECURITY;
CREATE POLICY eng04_06_result_write ON abc.eng04_06_results
  FOR INSERT TO abc_pipeline_worker WITH CHECK(
    EXISTS(SELECT 1 FROM abc.eng03_worker_bindings b
      WHERE b.worker_role=current_user AND b.consumer_id=abc.eng04_06_results.consumer_id
        AND b.tenant_id=abc.eng04_06_results.tenant_id AND b.active));
REVOKE ALL ON abc.eng04_06_results FROM PUBLIC,abc_app,abc_worker,
   abc_answer_worker,abc_orchestrator,abc_eng03_worker;
GRANT INSERT ON abc.eng04_06_results TO abc_pipeline_worker;

-- Privileged narrow source broker, allowing only the current leased job and
-- immutable policy-bound answer. Never grant direct SELECT on ENG02 answers.
CREATE FUNCTION abc.eng03_source_for_lease(p_job uuid,p_token uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,abc
AS $body$
DECLARE result jsonb;
BEGIN
  IF session_user<>'abc_eng03_worker' THEN
     RAISE EXCEPTION 'dedicated eng03 worker required' USING ERRCODE='42501';
  END IF;
  SELECT jsonb_build_object(
    'job_id',j.job_id,'event_id',j.source_event_id,
    'tenant_id',j.tenant_id,'branch_id',j.branch_id,
    'session_id',j.session_id,'aggregate_version',j.aggregate_version,
    'answer_id',a.answer_id,'question_id',a.question_id,'answer_source',a.answer_source,
    'answer_value',a.value,'policy_decision_id',p.decision_id,
    'policy_version',p.policy_version,'profile_version',a.question_profile_version
  ) INTO result
  FROM abc.eng03_input_jobs j
  JOIN abc.eng03_worker_bindings b
    ON b.consumer_id=j.consumer_id AND b.tenant_id=j.tenant_id
       AND b.worker_role=session_user AND b.active
  JOIN abc.answer_index_projection proj
    ON proj.consumer_id=j.consumer_id AND proj.event_id=j.source_event_id
       AND proj.tenant_id=j.tenant_id AND proj.branch_id=j.branch_id
       AND proj.session_id=j.session_id AND proj.aggregate_version=j.aggregate_version
  JOIN abc.eng02_answers a ON a.answer_id=proj.answer_id AND a.session_id=j.session_id
       AND a.tenant_id=j.tenant_id AND a.branch_id=j.branch_id
       AND a.aggregate_version=j.aggregate_version
       AND a.question_id=proj.question_id
  JOIN abc.eng14_policy_audit p ON p.decision_id=a.policy_decision_id
       AND p.tenant_id=j.tenant_id AND p.branch_id=j.branch_id AND p.session_id=j.session_id
       AND p.aggregate_version=j.aggregate_version AND p.decision='ALLOW'
       AND p.scope='QUESTION' AND p.policy_version='eng14.synthetic.1'
  JOIN abc.sessions s ON s.session_id=j.session_id
       AND s.tenant_id=j.tenant_id AND s.branch_id=j.branch_id
       AND s.service_id='synthetic:hair-color'
  WHERE j.job_id=p_job AND j.status='LEASED' AND j.lease_token=p_token
    AND j.lease_until>clock_timestamp();
  IF result IS NULL THEN
      RAISE EXCEPTION 'source unavailable or lease expired' USING ERRCODE='42501';
  END IF;
  RETURN result;
END
$body$;
REVOKE ALL ON FUNCTION abc.eng03_source_for_lease(uuid,uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION abc.eng03_source_for_lease(uuid,uuid) TO abc_eng03_worker;
-- An executor cannot forge source attributes, answer values or policy approval
-- even with valid INSERT rights. Validate immutable snapshot at the DB boundary.
CREATE FUNCTION abc.verify_eng03_evidence_source() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,abc
AS $source$
DECLARE a record; expected_key text; expected_kind text;
BEGIN
  IF session_user<>'abc_eng03_worker' THEN
     RAISE EXCEPTION 'trusted eng03 writer required' USING ERRCODE='42501';
  END IF;
  SELECT answer.value,answer.answer_source,answer.question_id,
         answer.answer_id,answer.policy_decision_id
    INTO a
    FROM abc.eng03_input_jobs j
    JOIN abc.answer_index_projection proj
      ON proj.consumer_id=j.consumer_id AND proj.event_id=j.source_event_id
      AND proj.session_id=j.session_id AND proj.tenant_id=j.tenant_id
      AND proj.branch_id=j.branch_id AND proj.aggregate_version=j.aggregate_version
    JOIN abc.eng02_answers answer
      ON answer.answer_id=proj.answer_id AND answer.session_id=j.session_id
      AND answer.tenant_id=j.tenant_id AND answer.branch_id=j.branch_id
      AND answer.aggregate_version=j.aggregate_version
    JOIN abc.eng14_policy_audit policy
      ON policy.decision_id=answer.policy_decision_id
         AND policy.session_id=j.session_id AND policy.tenant_id=j.tenant_id
         AND policy.aggregate_version=j.aggregate_version
         AND policy.decision='ALLOW' AND policy.policy_version='eng14.synthetic.1'
    JOIN abc.eng03_worker_bindings b
      ON b.worker_role=session_user AND b.consumer_id=j.consumer_id
         AND b.tenant_id=j.tenant_id AND b.active
    WHERE j.job_id=NEW.source_job_id AND j.consumer_id=NEW.consumer_id
      AND j.source_event_id=NEW.source_event_id
      AND j.tenant_id=NEW.tenant_id AND j.branch_id=NEW.branch_id
      AND j.session_id=NEW.session_id AND j.aggregate_version=NEW.aggregate_version
      AND j.status='LEASED' AND j.lease_token=NEW.source_lease_token
      AND j.lease_until>clock_timestamp();
  expected_key=CASE a.question_id
     WHEN 'synthetic:prior-treatment' THEN 'prior_treatment'
     WHEN 'synthetic:sensitivity' THEN 'sensitivity_flag'
     WHEN 'synthetic:desired-goal' THEN 'goal'
     WHEN 'synthetic:maintenance' THEN 'maintenance'
     ELSE NULL END;
  expected_kind=CASE a.answer_source
       WHEN 'CLIENT' THEN 'CLIENT_ANSWER'
       WHEN 'SPECIALIST' THEN 'SALON_RECORD'
       ELSE NULL END;
  IF expected_key IS NULL OR NEW.source_answer_id IS DISTINCT FROM a.answer_id
      OR NEW.policy_decision_id IS DISTINCT FROM a.policy_decision_id
      OR NEW.question_id IS DISTINCT FROM a.question_id
      OR NEW.source_kind IS DISTINCT FROM a.answer_source
      OR NEW.evidence_json->>'session_id' IS DISTINCT FROM NEW.session_id::text
      OR NEW.evidence_json->>'service_id' IS DISTINCT FROM 'synthetic:hair-color'
      OR NEW.evidence_json->>'evidence_id' IS DISTINCT FROM NEW.evidence_id::text
      OR NEW.evidence_json->>'attribute_key' IS DISTINCT FROM expected_key
      OR NEW.evidence_json->>'confidence_label' IS DISTINCT FROM 'UNRATED'
      OR NEW.evidence_digest !~ '^[0-9a-f]{64}

  THEN
      RAISE EXCEPTION 'ENG03 trusted evidence lineage mismatch' USING ERRCODE='23514';
  END IF;
  IF a.value IN ('UNKNOWN','UNSURE') THEN
    IF NEW.evidence_json->>'evidence_class' IS DISTINCT FROM 'UNKNOWN'
      OR NEW.evidence_json->>'source_type' IS DISTINCT FROM 'NOT_AVAILABLE'
      OR (NEW.evidence_json ? 'source_id')
      OR NEW.evidence_json->'value' IS DISTINCT FROM 'null'::jsonb
    THEN
      RAISE EXCEPTION 'ENG03 unknown value cannot be promoted' USING ERRCODE='23514';
    END IF;
  ELSE
    IF NEW.evidence_json->>'evidence_class' IS DISTINCT FROM 'USER_REPORTED'
      OR NEW.evidence_json->>'source_type' IS DISTINCT FROM expected_kind
      OR NEW.evidence_json->>'value' IS DISTINCT FROM a.value
      OR NEW.evidence_json->>'source_id' IS DISTINCT FROM a.answer_id::text
      OR NEW.evidence_id IS DISTINCT FROM a.answer_id
    THEN
      RAISE EXCEPTION 'ENG03 reported source may not be fabricated' USING ERRCODE='23514';
    END IF;
  END IF;
  RETURN NEW;
END;
$source$;
REVOKE ALL ON FUNCTION abc.verify_eng03_evidence_source() FROM PUBLIC;
CREATE TRIGGER eng03_evidence_lineage_gate
  BEFORE INSERT ON abc.eng03_evidence_ledger
  FOR EACH ROW EXECUTE FUNCTION abc.verify_eng03_evidence_source();

COMMIT;

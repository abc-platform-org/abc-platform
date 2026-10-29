-- 0013 hardening: authenticated per-consumer PostgreSQL LOGIN with NOINHERIT.
-- Role group remains the SQL permission principal but it is NOLOGIN.
-- `session_user` is determined by the DB connection and cannot be spoofed by
-- SET ROLE, custom GUC, claimed consumer_id or request JSON.
BEGIN;
ALTER ROLE abc_eng03_worker NOLOGIN;
ALTER ROLE abc_pipeline_worker NOLOGIN;
CREATE TABLE abc.worker_login_bindings (
  login_name name PRIMARY KEY,
  worker_role name NOT NULL CHECK(worker_role IN ('abc_eng03_worker','abc_pipeline_worker')),
  consumer_id text NOT NULL,
  tenant_id text NOT NULL,
  active boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  FOREIGN KEY (worker_role,consumer_id,tenant_id)
   REFERENCES abc.eng03_worker_bindings(worker_role,consumer_id,tenant_id)
);
CREATE UNIQUE INDEX worker_login_exact_scope
  ON abc.worker_login_bindings(login_name,worker_role,consumer_id,tenant_id);
ALTER TABLE abc.worker_login_bindings ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.worker_login_bindings FORCE ROW LEVEL SECURITY;
CREATE POLICY worker_login_only_self ON abc.worker_login_bindings
  FOR SELECT TO abc_eng03_worker,abc_pipeline_worker
  USING(login_name=session_user AND worker_role=current_user AND active);
REVOKE ALL ON abc.worker_login_bindings FROM PUBLIC,abc_app,abc_worker,
  abc_answer_worker,abc_orchestrator;
GRANT SELECT ON abc.worker_login_bindings TO abc_eng03_worker,abc_pipeline_worker;

-- RESTRICTIVE scope is conjoined to the original permission policy. Every
-- child table policy depends on the original binding visibility, hence one
-- restrictive gate covers all existing job, projection and result RLS.
CREATE POLICY eng03_exact_authenticated_login ON abc.eng03_worker_bindings
  AS RESTRICTIVE FOR SELECT TO abc_eng03_worker,abc_pipeline_worker
  USING(EXISTS(
      SELECT 1 FROM abc.worker_login_bindings login
       WHERE login.login_name=session_user
         AND login.worker_role=abc.eng03_worker_bindings.worker_role
         AND login.consumer_id=abc.eng03_worker_bindings.consumer_id
         AND login.tenant_id=abc.eng03_worker_bindings.tenant_id
         AND login.active));
-- The group role cannot authenticate directly, but a granted workload LOGIN
-- can SET ROLE to only its own inherited-disabled engine permission group.
-- Admin provisioning (including CREATE ROLE and GRANT) must remain offline
-- and never be performed from the application/worker credentials.
CREATE OR REPLACE FUNCTION abc.eng03_source_for_lease(p_job uuid,p_token uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,abc
AS $body$
DECLARE result jsonb;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM abc.worker_login_bindings x
     WHERE x.login_name=session_user AND x.worker_role='abc_eng03_worker'
       AND x.active) THEN
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
       AND b.worker_role='abc_eng03_worker' AND b.active
  JOIN abc.worker_login_bindings identity_binding
    ON identity_binding.login_name=session_user
       AND identity_binding.worker_role='abc_eng03_worker'
       AND identity_binding.consumer_id=j.consumer_id
       AND identity_binding.tenant_id=j.tenant_id AND identity_binding.active
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

CREATE OR REPLACE FUNCTION abc.verify_eng03_evidence_source() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,abc
AS $source$
DECLARE a record; expected_key text; expected_kind text;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM abc.worker_login_bindings x
     WHERE x.login_name=session_user AND x.worker_role='abc_eng03_worker'
       AND x.active) THEN
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
      ON b.worker_role='abc_eng03_worker' AND b.consumer_id=j.consumer_id
         AND b.tenant_id=j.tenant_id AND b.active
    JOIN abc.worker_login_bindings identity_binding
      ON identity_binding.login_name=session_user
         AND identity_binding.worker_role='abc_eng03_worker'
         AND identity_binding.consumer_id=j.consumer_id
         AND identity_binding.tenant_id=j.tenant_id AND identity_binding.active
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
      OR NEW.evidence_digest !~ '^[0-9a-f]{64}'
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
      OR NEW.evidence_id IS DISTINCT FROM
           substring(encode(sha256(convert_to(
              NEW.consumer_id||'|'||a.answer_id::text,'UTF8'
            )),'hex'),1,32)::uuid
    THEN
      RAISE EXCEPTION 'ENG03 reported source may not be fabricated' USING ERRCODE='23514';
    END IF;
  END IF;
  RETURN NEW;
END;
$source$;

CREATE OR REPLACE FUNCTION abc.verify_synthetic_pipeline_result() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,abc
AS $pipeline$
DECLARE candidate jsonb; item record; n integer;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM abc.worker_login_bindings x
     WHERE x.login_name=session_user AND x.worker_role='abc_pipeline_worker'
       AND x.active) THEN
    RAISE EXCEPTION 'dedicated pipeline principal required' USING ERRCODE='42501';
  END IF;
  SELECT j.job_id,j.source_evidence_id INTO item
    FROM abc.eng04_06_jobs j
    JOIN abc.eng03_worker_bindings b
      ON b.worker_role='abc_pipeline_worker' AND b.consumer_id=j.consumer_id
       AND b.tenant_id=j.tenant_id AND b.active
    JOIN abc.worker_login_bindings identity_binding
      ON identity_binding.login_name=session_user
         AND identity_binding.worker_role='abc_pipeline_worker'
         AND identity_binding.consumer_id=j.consumer_id
         AND identity_binding.tenant_id=j.tenant_id AND identity_binding.active
    JOIN abc.eng03_evidence_ledger e
      ON e.evidence_id=j.source_evidence_id
       AND e.consumer_id=j.consumer_id AND e.tenant_id=j.tenant_id
       AND e.session_id=j.session_id AND e.aggregate_version=j.aggregate_version
       AND e.policy_decision_id IS NOT NULL
    WHERE j.job_id=NEW.source_pipeline_job_id AND j.consumer_id=NEW.consumer_id
      AND j.tenant_id=NEW.tenant_id AND j.branch_id=NEW.branch_id
      AND j.session_id=NEW.session_id AND j.aggregate_version=NEW.aggregate_version
      AND j.status='LEASED' AND j.lease_until>clock_timestamp();
  IF NOT FOUND OR NEW.policy_version<>'eng14.synthetic.1'
     OR NEW.analysis_json->>'session_id' IS DISTINCT FROM NEW.session_id::text
     OR NEW.knowledge_json->>'service_id' IS DISTINCT FROM 'synthetic:hair-color'
     OR NEW.decision_json->>'session_id' IS DISTINCT FROM NEW.session_id::text
     OR NEW.decision_json->>'service_id' IS DISTINCT FROM 'synthetic:hair-color'
     OR jsonb_typeof(NEW.decision_json->'candidates') IS DISTINCT FROM 'array'
     OR jsonb_array_length(NEW.decision_json->'candidates')>2
     OR NEW.source_evidence_digest !~ '^[0-9a-f]{64}'
  THEN
     RAISE EXCEPTION 'synthetic pipeline policy context invalid' USING ERRCODE='23514';
  END IF;
  SELECT count(*) INTO n FROM abc.eng03_evidence_ledger e
       WHERE e.consumer_id=NEW.consumer_id AND e.tenant_id=NEW.tenant_id
         AND e.session_id=NEW.session_id AND e.aggregate_version<=NEW.aggregate_version;
  IF jsonb_array_length(NEW.decision_json->'candidates')>0 THEN
      IF NEW.knowledge_json->>'ontology_version' IS DISTINCT FROM 'synthetic-ontology.1'
         OR NEW.knowledge_json->'retrieval_sources'->0->>'source_id'
               IS DISTINCT FROM 'synthetic:offline-catalog'
         OR NEW.knowledge_json->'retrieval_sources'->0->>'source_version'
               IS DISTINCT FROM 'test-v1'
         OR NEW.knowledge_json->'retrieval_sources'->0->>'validated_by'
               IS DISTINCT FROM 'TEST_FIXTURE_ONLY'
         OR NEW.analysis_json->>'engine_version'
               IS DISTINCT FROM 'eng04.synthetic-evidence.1'
         OR NEW.decision_json->>'decision_engine_version'
               IS DISTINCT FROM 'eng06.synthetic.1'
         OR jsonb_typeof(NEW.knowledge_json->'grounded_facts') IS DISTINCT FROM 'array'
         OR jsonb_array_length(NEW.knowledge_json->'grounded_facts')<>2
         OR EXISTS(SELECT 1 FROM abc.eng03_evidence_ledger e
            WHERE e.consumer_id=NEW.consumer_id AND e.tenant_id=NEW.tenant_id
              AND e.session_id=NEW.session_id AND e.aggregate_version<=NEW.aggregate_version
              AND (e.evidence_json->>'evidence_class' IS DISTINCT FROM 'USER_REPORTED'
                  OR e.evidence_json->>'value' IN ('UNKNOWN','UNSURE')
                  OR e.evidence_json->>'value' IS NULL))
      THEN
         RAISE EXCEPTION 'synthetic source unreviewed or incomplete' USING ERRCODE='23514';
      END IF;
      IF n<>4 OR
         jsonb_array_length(COALESCE(NEW.knowledge_json->'retrieval_sources','[]'::jsonb))<>1 OR
         EXISTS(SELECT 1 FROM abc.eng03_evidence_ledger e
           WHERE e.consumer_id=NEW.consumer_id AND e.tenant_id=NEW.tenant_id
             AND e.session_id=NEW.session_id AND e.aggregate_version<=NEW.aggregate_version
             AND ((e.evidence_json->>'attribute_key' IN ('prior_treatment','sensitivity_flag')
                      AND e.evidence_json->>'evidence_class'<>'USER_REPORTED')
                   OR (e.evidence_json->>'attribute_key'='sensitivity_flag'
                      AND e.evidence_json->>'value'='YES')))
      THEN
         RAISE EXCEPTION 'critical evidence blocks synthetic candidates' USING ERRCODE='23514';
      END IF;
  END IF;
  FOR candidate IN SELECT value FROM jsonb_array_elements(NEW.decision_json->'candidates') LOOP
    IF candidate->>'candidate_id' NOT IN ('synthetic:style-a','synthetic:style-b')
       OR candidate->>'feasibility_label' IS DISTINCT FROM 'PROFESSIONAL_CHECK_REQUIRED'
       OR candidate->>'hard_filter_status' IS DISTINCT FROM 'CONDITIONALLY_PASSED'
       OR candidate->>'reason' IS DISTINCT FROM 'SYNTHETIC_TEST_ONLY_REQUIRES_PROFESSIONAL_REVIEW'
       OR NOT EXISTS (
          SELECT 1 FROM jsonb_array_elements(NEW.knowledge_json->'grounded_facts') AS source_fact(fact_json)
          WHERE source_fact.fact_json->>'key'=candidate->>'candidate_id'
             AND source_fact.fact_json->>'source_id'='synthetic:offline-catalog'
             AND source_fact.fact_json->'value'='true'::jsonb)
    THEN
       RAISE EXCEPTION 'synthetic candidate was upgraded or invented' USING ERRCODE='23514';
    END IF;
  END LOOP;
  RETURN NEW;
END;
$pipeline$;
COMMIT;

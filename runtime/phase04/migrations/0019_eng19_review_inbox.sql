-- 0019: Review-only durable handoff inbox. NOT a production engine dispatcher.
-- ENG14 purpose-consent and session-version guard is checked IN DATABASE.
-- A caller-provided proof reference has no authorization authority.
BEGIN;
CREATE TABLE abc.eng19_review_edges(
  from_engine text NOT NULL,
  to_engine text NOT NULL,
  artifact_kind text NOT NULL,
  PRIMARY KEY(from_engine,to_engine,artifact_kind),
  CHECK(from_engine ~ '^ENG-(0[1-9]|1[0-9])$'),
  CHECK(to_engine ~ '^ENG-(0[1-9]|1[0-9])$')
);
INSERT INTO abc.eng19_review_edges VALUES
  ('ENG-02','ENG-03','PURPOSE_BOUND_CONSULTATION_EVIDENCE'),
  ('ENG-03','ENG-04','TRACEABLE_EVIDENCE_PACKAGE'),
  ('ENG-04','ENG-05','BEAUTY_ANALYSIS_REPORT'),
  ('ENG-05','ENG-06','PROFESSIONAL_KNOWLEDGE_BUNDLE'),
  ('ENG-06','ENG-07','AUDITABLE_RECOMMENDATION_DECISION'),
  ('ENG-07','ENG-08','VERSIONED_LOOK_SPECIFICATION'),
  ('ENG-08','ENG-09','AUTHORIZED_REGION_MASK_SET'),
  ('ENG-09','ENG-10','DRAFT_VISUAL_VARIANT'),
  ('ENG-10','ENG-11','COMPOSITED_PREVIEW'),
  ('ENG-11','ENG-12','MASKED_VISUAL_QA_REPORT'),
  ('ENG-12','ENG-13','IMMUTABLE_LOOK_VERSION_AND_LOCK'),
  ('ENG-13','ENG-15','EVIDENCE_GATED_FEASIBILITY_REPORT'),
  ('ENG-15','ENG-16','SPECIALIST_REVIEWABLE_TECHNICAL_PLAN'),
  ('ENG-16','ENG-17','SIGNED_SPECIALIST_VALIDATION'),
  ('ENG-17','ENG-18','AUTHORIZED_OPERATIONAL_HANDOFF'),
  ('ENG-18','ENG-19','AUDITABLE_SALON_KPI_FACTS');
REVOKE ALL ON abc.eng19_review_edges FROM PUBLIC,abc_app,abc_worker,
  abc_answer_worker,abc_orchestrator,abc_eng03_worker,abc_pipeline_worker;

CREATE TABLE abc.eng19_review_inbox(
  handoff_id uuid PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES abc.tenants(tenant_id),
  branch_id text NOT NULL,
  session_id uuid NOT NULL REFERENCES abc.sessions(session_id),
  state_version integer NOT NULL CHECK(state_version>=0),
  correlation_id uuid NOT NULL,
  from_engine text NOT NULL,
  to_engine text NOT NULL,
  artifact_kind text NOT NULL,
  message_sha256 text NOT NULL CHECK(message_sha256 ~ '^[0-9a-f]{64}$'),
  received_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  FOREIGN KEY(from_engine,to_engine,artifact_kind)
    REFERENCES abc.eng19_review_edges(from_engine,to_engine,artifact_kind)
);
CREATE INDEX eng19_review_inbox_scope ON abc.eng19_review_inbox(
  tenant_id,branch_id,session_id,state_version);
ALTER TABLE abc.eng19_review_inbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.eng19_review_inbox FORCE ROW LEVEL SECURITY;
REVOKE ALL ON abc.eng19_review_inbox FROM PUBLIC,abc_app,abc_worker,
  abc_answer_worker,abc_orchestrator,abc_eng03_worker,abc_pipeline_worker;
DO $policy$ BEGIN
  IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='abc_staging_migrator') THEN
    -- The SECURITY DEFINER migrator owns schema and is already trusted.
    -- FORCE RLS otherwise hides sessions/consent from the DB-owned gate;
    -- this does NOT give application, worker or direct client any access.
    CREATE POLICY eng19_migrator_session_read
      ON abc.sessions FOR SELECT TO abc_staging_migrator USING(true);
    CREATE POLICY eng19_migrator_consent_read
      ON abc.consent_evidence FOR SELECT TO abc_staging_migrator USING(true);
    CREATE POLICY eng19_review_migrator
      ON abc.eng19_review_inbox FOR ALL TO abc_staging_migrator
      USING(true) WITH CHECK(true);
  END IF;
END $policy$;

CREATE FUNCTION abc.eng19_record_review_handoff(
 p_handoff uuid,p_tenant text,p_branch text,p_session uuid,p_version integer,
 p_correlation uuid,p_from text,p_to text,p_artifact text,p_message_sha text
) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,abc
AS $receipt$
DECLARE v_existing abc.eng19_review_inbox%ROWTYPE;
BEGIN
  IF p_handoff IS NULL OR p_session IS NULL OR p_correlation IS NULL
     OR p_version IS NULL OR p_version<0
     OR p_message_sha !~ '^[0-9a-f]{64}$'
     OR NOT abc.eng14_workload_allowed(p_tenant)
     OR p_branch IS DISTINCT FROM current_setting('abc.branch',true)
     OR NOT EXISTS(
       SELECT 1 FROM abc.eng19_review_edges
        WHERE from_engine=p_from AND to_engine=p_to AND artifact_kind=p_artifact)
  THEN
    RAISE EXCEPTION 'ENG19 review inbox authority denied' USING ERRCODE='42501';
  END IF;
  -- FOR SHARE locks both records; consent revocation and session PAUSE
  -- must serialize before or after the inbox receipt transaction.
  IF NOT EXISTS(
    SELECT 1 FROM abc.sessions s
      JOIN abc.consent_evidence ce ON
        ce.session_id=s.session_id AND ce.tenant_id=s.tenant_id
        AND ce.branch_id=s.branch_id AND ce.client_id=s.client_id
    WHERE s.session_id=p_session AND s.tenant_id=p_tenant
      AND s.branch_id=p_branch AND s.state='CREATED'
      AND s.state_version=p_version
      AND ce.status='ACTIVE' AND ce.verified_at IS NOT NULL
      AND ce.revoked_at IS NULL AND ce.valid_until>clock_timestamp()
      AND ce.purpose @> ARRAY['AI_PROCESSING','INTERNAL_HANDOFF']::text[]
    FOR SHARE OF s,ce
  ) THEN
    RAISE EXCEPTION 'ENG19 consent or session scope denied' USING ERRCODE='42501';
  END IF;
  INSERT INTO abc.eng19_review_inbox(
    handoff_id,tenant_id,branch_id,session_id,state_version,correlation_id,
    from_engine,to_engine,artifact_kind,message_sha256)
  VALUES(p_handoff,p_tenant,p_branch,p_session,p_version,p_correlation,
         p_from,p_to,p_artifact,p_message_sha)
  ON CONFLICT (handoff_id) DO NOTHING;
  IF FOUND THEN RETURN 'RECORDED_REVIEW_ONLY'; END IF;
  SELECT * INTO v_existing FROM abc.eng19_review_inbox WHERE handoff_id=p_handoff;
  IF NOT FOUND OR
    (v_existing.tenant_id,v_existing.branch_id,v_existing.session_id,
     v_existing.state_version,v_existing.correlation_id,
     v_existing.from_engine,v_existing.to_engine,
     v_existing.artifact_kind,v_existing.message_sha256) IS DISTINCT FROM
    (p_tenant,p_branch,p_session,p_version,p_correlation,
     p_from,p_to,p_artifact,p_message_sha)
  THEN
    RAISE EXCEPTION 'ENG19 handoff idempotency content conflict'
      USING ERRCODE='23505';
  END IF;
  RETURN 'ALREADY_RECORDED_REVIEW_ONLY';
END;
$receipt$;
REVOKE ALL ON FUNCTION abc.eng19_record_review_handoff(
 uuid,text,text,uuid,integer,uuid,text,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION abc.eng19_record_review_handoff(
 uuid,text,text,uuid,integer,uuid,text,text,text,text) TO abc_app;
COMMIT;

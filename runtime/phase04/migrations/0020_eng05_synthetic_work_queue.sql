-- 0020: ENG05 synthetic review worker; never a deployable salon treatment engine.
BEGIN;
CREATE TABLE abc.eng19_synthetic_jobs(
  handoff_id uuid PRIMARY KEY REFERENCES abc.eng19_review_inbox(handoff_id),
  tenant_id text NOT NULL REFERENCES abc.tenants(tenant_id),
  branch_id text NOT NULL,
  session_id uuid NOT NULL REFERENCES abc.sessions(session_id),
  state_version integer NOT NULL CHECK(state_version>=0),
  consumer_id text NOT NULL CHECK(length(consumer_id) BETWEEN 3 AND 64),
  source_bytes bytea NOT NULL CHECK(octet_length(source_bytes) BETWEEN 16 AND 32768),
  source_sha256 text NOT NULL CHECK(source_sha256 ~ '^[a-f0-9]{64}$'),
  status text NOT NULL DEFAULT 'QUEUED'
    CHECK(status IN ('QUEUED','LEASED','ACKED','DLQ')),
  attempts integer NOT NULL DEFAULT 0 CHECK(attempts BETWEEN 0 AND 3),
  lease_token uuid,lease_until timestamptz,
  available_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  failure_code text,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  CHECK(status<>'LEASED' OR (lease_token IS NOT NULL AND lease_until IS NOT NULL)),
  UNIQUE(handoff_id,source_sha256)
);
CREATE INDEX eng19_synthetic_jobs_due ON abc.eng19_synthetic_jobs(status,available_at,lease_until);
CREATE TABLE abc.eng19_synthetic_results(
  handoff_id uuid PRIMARY KEY REFERENCES abc.eng19_synthetic_jobs(handoff_id),
  worker_lease uuid NOT NULL,
  consumer_id text NOT NULL,
  engine_id text NOT NULL CHECK(engine_id='ENG-05'),
  engine_version text NOT NULL CHECK(engine_version='synthetic-ontology.1'),
  source_sha256 text NOT NULL CHECK(source_sha256 ~ '^[a-f0-9]{64}$'),
  output_sha256 text NOT NULL CHECK(output_sha256 ~ '^[a-f0-9]{64}$'),
  output_bytes bytea NOT NULL CHECK(octet_length(output_bytes) BETWEEN 16 AND 32768),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE abc.eng19_synthetic_outbox(
  handoff_id uuid PRIMARY KEY REFERENCES abc.eng19_synthetic_results(handoff_id),
  target_handoff_id uuid NOT NULL UNIQUE,
  from_engine text NOT NULL CHECK(from_engine='ENG-05'),
  to_engine text NOT NULL CHECK(to_engine='ENG-06'),
  artifact_kind text NOT NULL CHECK(artifact_kind='PROFESSIONAL_KNOWLEDGE_BUNDLE'),
  artifact_sha256 text NOT NULL CHECK(artifact_sha256 ~ '^[a-f0-9]{64}$'),
  status text NOT NULL DEFAULT 'BLOCKED_PENDING_AUTHORITY'
    CHECK(status='BLOCKED_PENDING_AUTHORITY'),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
DO $acl$ DECLARE t text; BEGIN
  FOREACH t IN ARRAY ARRAY['eng19_synthetic_jobs','eng19_synthetic_results',
                            'eng19_synthetic_outbox'] LOOP
    EXECUTE format('ALTER TABLE abc.%I ENABLE ROW LEVEL SECURITY',t);
    EXECUTE format('ALTER TABLE abc.%I FORCE ROW LEVEL SECURITY',t);
    EXECUTE format('REVOKE ALL ON abc.%I FROM PUBLIC,abc_app,abc_worker,abc_answer_worker,abc_orchestrator,abc_eng03_worker,abc_pipeline_worker',t);
    IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='abc_staging_migrator') THEN
      EXECUTE format('CREATE POLICY eng19_migrator_all ON abc.%I FOR ALL TO abc_staging_migrator USING(true) WITH CHECK(true)',t);
    END IF;
  END LOOP;
END $acl$;

-- In managed staging the SECURITY DEFINER migrator obeys FORCE RLS
-- on this pre-existing worker-binding table. Give ONLY that migration owner
-- SELECT visibility for enforcing the physical worker role's active binding.
-- No application/worker SELECT privilege is added by this policy.
DO $migrator_read$ BEGIN
  IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='abc_staging_migrator') THEN
    CREATE POLICY eng19_migrator_binding_read
      ON abc.eng03_worker_bindings FOR SELECT TO abc_staging_migrator
      USING(true);
    CREATE POLICY eng19_migrator_worker_login_read
      ON abc.worker_login_bindings FOR SELECT TO abc_staging_migrator
      USING(true);
  END IF;
END $migrator_read$;

CREATE FUNCTION abc.eng19_submit_synthetic(
  p_handoff uuid,p_tenant text,p_branch text,p_session uuid,p_version integer,
  p_correlation uuid,p_artifact_sha text,p_message_sha text,p_source bytea,
  p_consumer text
) RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,abc
AS $submit$
DECLARE v_status text;v_payload jsonb;v_found abc.eng19_synthetic_jobs%ROWTYPE;
BEGIN
  IF p_tenant IS DISTINCT FROM 'tenant-test'
     OR p_branch IS DISTINCT FROM 'branch-test'
     OR p_source IS NULL OR octet_length(p_source) NOT BETWEEN 16 AND 32768
     OR p_consumer IS NULL OR length(p_consumer) NOT BETWEEN 3 AND 64
     OR p_artifact_sha IS NULL
     OR encode(sha256(p_source),'hex') IS DISTINCT FROM p_artifact_sha
  THEN RAISE EXCEPTION 'synthetic artifact digest invalid' USING ERRCODE='42501'; END IF;
  v_payload:=convert_from(p_source,'UTF8')::jsonb;
  IF jsonb_typeof(v_payload)<>'object'
     OR v_payload->>'engine_version'<>'eng04.synthetic-evidence.1'
     OR v_payload->>'service_scope'<>'SYNTHETIC_NON_MEDIA_ONLY'
     OR v_payload->>'service_id'<>'synthetic:hair-color'
     OR v_payload->>'session_id' IS DISTINCT FROM p_session::text
     OR jsonb_typeof(v_payload->'evidence_ids')<>'array'
     OR jsonb_array_length(v_payload->'evidence_ids')=0
  THEN RAISE EXCEPTION 'source must be scoped synthetic ENG04 analysis' USING ERRCODE='42501'; END IF;
  v_status:=abc.eng19_record_review_handoff(
    p_handoff,p_tenant,p_branch,p_session,p_version,p_correlation,
    'ENG-04','ENG-05','BEAUTY_ANALYSIS_REPORT',p_message_sha);
  INSERT INTO abc.eng19_synthetic_jobs(
    handoff_id,tenant_id,branch_id,session_id,state_version,
    consumer_id,source_bytes,source_sha256)
  VALUES(p_handoff,p_tenant,p_branch,p_session,p_version,
         p_consumer,p_source,p_artifact_sha)
  ON CONFLICT(handoff_id) DO NOTHING;
  SELECT * INTO v_found FROM abc.eng19_synthetic_jobs WHERE handoff_id=p_handoff;
  IF NOT FOUND OR v_found.source_sha256<>p_artifact_sha
     OR v_found.source_bytes<>p_source
     OR (v_found.tenant_id,v_found.branch_id,v_found.session_id,
         v_found.state_version,v_found.consumer_id)
        IS DISTINCT FROM (p_tenant,p_branch,p_session,p_version,p_consumer)
  THEN RAISE EXCEPTION 'immutable source job conflict' USING ERRCODE='23505'; END IF;
  RETURN v_status;
END;$submit$;

CREATE FUNCTION abc.eng19_claim_synthetic(p_consumer text,p_seconds integer DEFAULT 30)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,abc
AS $claim$
DECLARE j abc.eng19_synthetic_jobs%ROWTYPE;v_lease uuid;v_now timestamptz:=clock_timestamp();
BEGIN
  IF session_user='abc_pipeline_worker' OR p_seconds NOT BETWEEN 1 AND 120
     OR p_consumer IS NULL
     OR NOT EXISTS (SELECT 1 FROM abc.worker_login_bindings w
       WHERE w.login_name=session_user AND w.worker_role='abc_pipeline_worker'
         AND w.consumer_id=p_consumer AND w.active)
  THEN RAISE EXCEPTION 'independent synthetic worker required' USING ERRCODE='42501'; END IF;
  -- A crashed worker on its third lease must not strand a perpetual LEASED
  -- row. Mark it DLQ before choosing another ready job, and only for a
  -- currently authorized worker subscription.
  UPDATE abc.eng19_synthetic_jobs expired
     SET status='DLQ',lease_token=NULL,lease_until=NULL,
         failure_code='CI_LEASE_EXHAUSTED',
         updated_at=v_now
    WHERE expired.status='LEASED' AND expired.attempts>=3
      AND expired.lease_until<v_now AND expired.consumer_id=p_consumer
      AND EXISTS(SELECT 1 FROM abc.eng03_worker_bindings b
        WHERE b.consumer_id=expired.consumer_id
          AND b.tenant_id=expired.tenant_id
          AND b.worker_role='abc_pipeline_worker' AND b.active
        AND EXISTS(SELECT 1 FROM abc.worker_login_bindings w
          WHERE w.login_name=session_user
            AND w.worker_role='abc_pipeline_worker'
            AND w.consumer_id=b.consumer_id AND w.tenant_id=b.tenant_id
            AND w.active));
  SELECT job.* INTO j FROM abc.eng19_synthetic_jobs job
    JOIN abc.eng03_worker_bindings b
      ON b.consumer_id=job.consumer_id AND b.tenant_id=job.tenant_id
        AND b.worker_role='abc_pipeline_worker' AND b.active
    JOIN abc.worker_login_bindings w
      ON w.login_name=session_user AND w.worker_role='abc_pipeline_worker'
        AND w.consumer_id=b.consumer_id AND w.tenant_id=b.tenant_id AND w.active
    JOIN abc.sessions s
      ON s.session_id=job.session_id AND s.tenant_id=job.tenant_id
        AND s.branch_id=job.branch_id AND s.state='CREATED'
        AND s.state_version=job.state_version
    JOIN abc.consent_evidence ce
      ON ce.session_id=job.session_id AND ce.tenant_id=job.tenant_id
        AND ce.branch_id=job.branch_id AND ce.client_id=s.client_id
        AND ce.status='ACTIVE' AND ce.revoked_at IS NULL
        AND ce.verified_at IS NOT NULL AND ce.valid_until>v_now
        AND ce.purpose @> ARRAY['AI_PROCESSING','INTERNAL_HANDOFF']::text[]
    WHERE job.consumer_id=p_consumer AND job.attempts<3
      AND ((job.status='QUEUED' AND job.available_at<=v_now)
          OR (job.status='LEASED' AND job.lease_until<v_now))
    ORDER BY job.created_at,job.handoff_id LIMIT 1 FOR UPDATE OF job SKIP LOCKED;
  IF NOT FOUND THEN RETURN NULL; END IF;
  v_lease:=gen_random_uuid();
  UPDATE abc.eng19_synthetic_jobs SET status='LEASED',
    lease_token=v_lease,lease_until=v_now+make_interval(secs=>p_seconds),
    attempts=attempts+1,updated_at=v_now WHERE handoff_id=j.handoff_id;
  RETURN jsonb_build_object('handoff_id',j.handoff_id,'tenant_id',j.tenant_id,
    'branch_id',j.branch_id,'session_id',j.session_id,
    'state_version',j.state_version,'consumer_id',j.consumer_id,
    'source_sha256',j.source_sha256,
    'source',convert_from(j.source_bytes,'UTF8')::jsonb,
    'lease_token',v_lease,'attempt',j.attempts+1,
    'engine_id','ENG-05','engine_version','synthetic-ontology.1');
END;$claim$;

CREATE FUNCTION abc.eng19_ack_synthetic(
 p_handoff uuid,p_lease uuid,p_out bytea,p_next uuid
) RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,abc
AS $ack$
DECLARE j abc.eng19_synthetic_jobs%ROWTYPE;v_out jsonb;v_sha text;
BEGIN
 IF session_user='abc_pipeline_worker' OR p_lease IS NULL OR p_next IS NULL
    OR p_out IS NULL OR octet_length(p_out) NOT BETWEEN 16 AND 32768
 THEN RAISE EXCEPTION 'worker ACK context denied' USING ERRCODE='42501'; END IF;
 SELECT * INTO j FROM abc.eng19_synthetic_jobs WHERE handoff_id=p_handoff FOR UPDATE;
 IF NOT FOUND OR j.status<>'LEASED' OR j.lease_token IS DISTINCT FROM p_lease
    OR j.lease_until<=clock_timestamp()
    OR NOT EXISTS(SELECT 1 FROM abc.eng03_worker_bindings b
       WHERE b.consumer_id=j.consumer_id AND b.tenant_id=j.tenant_id
         AND b.worker_role='abc_pipeline_worker' AND b.active
         AND EXISTS(SELECT 1 FROM abc.worker_login_bindings w
            WHERE w.login_name=session_user
              AND w.worker_role='abc_pipeline_worker'
              AND w.consumer_id=b.consumer_id AND w.tenant_id=b.tenant_id
              AND w.active))
 THEN RAISE EXCEPTION 'stale lease or revoked worker denied' USING ERRCODE='42501'; END IF;
 IF NOT EXISTS(
   SELECT 1 FROM abc.sessions s
     JOIN abc.consent_evidence ce ON ce.session_id=s.session_id
       AND ce.tenant_id=s.tenant_id AND ce.branch_id=s.branch_id
       AND ce.client_id=s.client_id
   WHERE s.session_id=j.session_id AND s.tenant_id=j.tenant_id
     AND s.branch_id=j.branch_id AND s.state='CREATED'
     AND s.state_version=j.state_version AND ce.status='ACTIVE'
     AND ce.revoked_at IS NULL AND ce.verified_at IS NOT NULL
     AND ce.valid_until>clock_timestamp()
     AND ce.purpose @> ARRAY['AI_PROCESSING','INTERNAL_HANDOFF']::text[]
   FOR SHARE OF s,ce
 ) THEN RAISE EXCEPTION 'revoked consent or stale session at ACK' USING ERRCODE='42501'; END IF;
 v_out:=convert_from(p_out,'UTF8')::jsonb;
 IF jsonb_typeof(v_out)<>'object'
   OR v_out->>'ontology_version'<>'synthetic-ontology.1'
   OR v_out->>'service_id'<>'synthetic:hair-color'
   OR v_out->'retrieval_sources'<>'[]'::jsonb
   OR NOT (v_out->'unknowns' ? 'SOURCE_UNVERIFIED')
 THEN RAISE EXCEPTION 'unapproved or invented knowledge result' USING ERRCODE='42501'; END IF;
 v_sha:=encode(sha256(p_out),'hex');
 INSERT INTO abc.eng19_synthetic_results(
   handoff_id,worker_lease,consumer_id,engine_id,engine_version,
   source_sha256,output_sha256,output_bytes)
 VALUES(p_handoff,p_lease,j.consumer_id,'ENG-05','synthetic-ontology.1',
        j.source_sha256,v_sha,p_out);
 INSERT INTO abc.eng19_synthetic_outbox(
   handoff_id,target_handoff_id,from_engine,to_engine,artifact_kind,artifact_sha256)
 VALUES(p_handoff,p_next,'ENG-05','ENG-06','PROFESSIONAL_KNOWLEDGE_BUNDLE',v_sha);
 UPDATE abc.eng19_synthetic_jobs SET status='ACKED',lease_token=NULL,
   lease_until=NULL,updated_at=clock_timestamp() WHERE handoff_id=p_handoff;
 RETURN 'ACKED_REVIEW_ONLY';
END;$ack$;

CREATE FUNCTION abc.eng19_fail_synthetic(p_handoff uuid,p_lease uuid,p_error text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,abc
AS $fail$
DECLARE j abc.eng19_synthetic_jobs%ROWTYPE;v_status text;
BEGIN
 IF session_user='abc_pipeline_worker'
    OR p_error IS NULL OR p_error !~ '^CI_[A-Z_]{3,60}$'
 THEN RAISE EXCEPTION 'synthetic worker failure denied' USING ERRCODE='42501'; END IF;
 SELECT * INTO j FROM abc.eng19_synthetic_jobs WHERE handoff_id=p_handoff FOR UPDATE;
 IF NOT FOUND OR j.status<>'LEASED' OR j.lease_token IS DISTINCT FROM p_lease
    OR j.lease_until<=clock_timestamp()
    OR NOT EXISTS(SELECT 1 FROM abc.eng03_worker_bindings b
      WHERE b.consumer_id=j.consumer_id AND b.tenant_id=j.tenant_id
        AND b.worker_role='abc_pipeline_worker' AND b.active
        AND EXISTS(SELECT 1 FROM abc.worker_login_bindings w
           WHERE w.login_name=session_user
             AND w.worker_role='abc_pipeline_worker'
             AND w.consumer_id=b.consumer_id AND w.tenant_id=b.tenant_id
             AND w.active))
 THEN RAISE EXCEPTION 'stale worker fail receipt' USING ERRCODE='42501'; END IF;
 v_status:=CASE WHEN j.attempts>=3 THEN 'DLQ' ELSE 'QUEUED' END;
 UPDATE abc.eng19_synthetic_jobs SET status=v_status,
    available_at=clock_timestamp()+make_interval(secs=>j.attempts),
    failure_code=p_error,lease_token=NULL,lease_until=NULL,
    updated_at=clock_timestamp() WHERE handoff_id=p_handoff;
 RETURN v_status;
END;$fail$;

DO $functions$ DECLARE f text; BEGIN
 FOREACH f IN ARRAY ARRAY[
   'abc.eng19_submit_synthetic(uuid,text,text,uuid,integer,uuid,text,text,bytea,text)',
   'abc.eng19_claim_synthetic(text,integer)',
   'abc.eng19_ack_synthetic(uuid,uuid,bytea,uuid)',
   'abc.eng19_fail_synthetic(uuid,uuid,text)'] LOOP
   EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC',f);
 END LOOP;
END $functions$;
GRANT EXECUTE ON FUNCTION abc.eng19_submit_synthetic(uuid,text,text,uuid,integer,uuid,text,text,bytea,text) TO abc_app;
GRANT EXECUTE ON FUNCTION abc.eng19_claim_synthetic(text,integer) TO abc_pipeline_worker;
GRANT EXECUTE ON FUNCTION abc.eng19_ack_synthetic(uuid,uuid,bytea,uuid) TO abc_pipeline_worker;
GRANT EXECUTE ON FUNCTION abc.eng19_fail_synthetic(uuid,uuid,text) TO abc_pipeline_worker;
COMMIT;

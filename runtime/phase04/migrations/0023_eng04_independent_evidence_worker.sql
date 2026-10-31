-- 0023: ENG04 independent synthetic evidence worker. No automatic ingress.
-- An authorized CI administrator must explicitly seed review jobs from real
-- ENG03 source ledger. No ENG04->ENG05 dispatcher is deployed.
BEGIN;
CREATE TABLE abc.eng04_ci_worker_bindings (
 login_name name NOT NULL,consumer_id text NOT NULL,
 tenant_id text NOT NULL REFERENCES abc.tenants(tenant_id),
 active boolean NOT NULL DEFAULT false,
 PRIMARY KEY(login_name,consumer_id,tenant_id),
 CHECK(length(consumer_id) BETWEEN 3 AND 64)
);
CREATE TABLE abc.eng04_ci_jobs (
 job_id uuid PRIMARY KEY,tenant_id text NOT NULL REFERENCES abc.tenants(tenant_id),
 branch_id text NOT NULL,session_id uuid NOT NULL REFERENCES abc.sessions(session_id),
 consumer_id text NOT NULL,state_version integer NOT NULL CHECK(state_version>=0),
 status text NOT NULL DEFAULT 'QUEUED'
    CHECK(status IN ('QUEUED','LEASED','ACKED','DLQ')),
 attempts integer NOT NULL DEFAULT 0 CHECK(attempts BETWEEN 0 AND 3),
 lease_token uuid,lease_until timestamptz,
 available_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 failure_code text,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK(status<>'LEASED' OR (lease_token IS NOT NULL AND lease_until IS NOT NULL)),
 UNIQUE(consumer_id,session_id,state_version)
);
CREATE TABLE abc.eng04_ci_results (
 job_id uuid PRIMARY KEY REFERENCES abc.eng04_ci_jobs(job_id),
 engine_id text NOT NULL CHECK(engine_id='ENG-04'),
 engine_version text NOT NULL CHECK(engine_version='eng04.synthetic-evidence.1'),
 worker_lease uuid NOT NULL,source_manifest_sha256 text NOT NULL
 CHECK(source_manifest_sha256 ~ '^[0-9a-f]{64}$'),
 output_sha256 text NOT NULL CHECK(output_sha256 ~ '^[0-9a-f]{64}$'),
 output_bytes bytea NOT NULL CHECK(octet_length(output_bytes) BETWEEN 32 AND 32768),
 artifact_kind text NOT NULL CHECK(artifact_kind='BEAUTY_ANALYSIS_REPORT'),
 status text NOT NULL CHECK(status='BLOCKED_PENDING_AUTHORITY'),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX eng04_ci_due ON abc.eng04_ci_jobs(status,available_at,lease_until);
DO $pol$ DECLARE n text;BEGIN
 FOREACH n IN ARRAY ARRAY['eng04_ci_worker_bindings','eng04_ci_jobs',
                          'eng04_ci_results'] LOOP
   EXECUTE format('ALTER TABLE abc.%I ENABLE ROW LEVEL SECURITY',n);
   EXECUTE format('ALTER TABLE abc.%I FORCE ROW LEVEL SECURITY',n);
   EXECUTE format('REVOKE ALL ON abc.%I FROM PUBLIC,abc_app,abc_worker,abc_answer_worker,abc_orchestrator,abc_eng03_worker,abc_pipeline_worker,abc_eng04_worker,abc_eng05_worker,abc_eng06_review_worker',n);
   IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='abc_staging_migrator') THEN
     EXECUTE format('CREATE POLICY eng04_migrator_all ON abc.%I FOR ALL TO abc_staging_migrator USING(true) WITH CHECK(true)',n);
   END IF;
 END LOOP;
 IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='abc_staging_migrator') THEN
   CREATE POLICY eng04_migrator_source_read ON abc.eng03_evidence_ledger
      FOR SELECT TO abc_staging_migrator USING(true);
   CREATE POLICY eng04_migrator_eng03_job_read ON abc.eng03_input_jobs
      FOR SELECT TO abc_staging_migrator USING(true);
 END IF;
END $pol$;

CREATE FUNCTION abc.eng04_ci_claim(p_consumer text,p_seconds integer DEFAULT 30)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,abc
AS $claim$
DECLARE j abc.eng04_ci_jobs%ROWTYPE;v_now timestamptz:=clock_timestamp();
 v_lease uuid;v_src jsonb;v_hash text;v_count integer;v_distinct integer;
BEGIN
 IF session_user='abc_eng04_worker' OR p_consumer IS NULL
   OR length(p_consumer) NOT BETWEEN 3 AND 64
   OR p_seconds IS NULL OR p_seconds NOT BETWEEN 1 AND 120
   OR NOT EXISTS(SELECT 1 FROM abc.eng04_ci_worker_bindings b
          WHERE b.login_name=session_user AND b.consumer_id=p_consumer AND b.active)
 THEN RAISE EXCEPTION 'ENG04 physical identity not bound' USING ERRCODE='42501'; END IF;
 UPDATE abc.eng04_ci_jobs expired SET status='DLQ',lease_token=NULL,
   lease_until=NULL,failure_code='CI_LEASE_EXHAUSTED',updated_at=v_now
 WHERE expired.consumer_id=p_consumer AND expired.status='LEASED'
   AND expired.lease_until<v_now AND expired.attempts>=3
   AND EXISTS(SELECT 1 FROM abc.eng04_ci_worker_bindings b
      WHERE b.login_name=session_user AND b.consumer_id=expired.consumer_id
        AND b.tenant_id=expired.tenant_id AND b.active);
 SELECT q.* INTO j FROM abc.eng04_ci_jobs q
  JOIN abc.eng04_ci_worker_bindings b
    ON b.login_name=session_user AND b.consumer_id=q.consumer_id
      AND b.tenant_id=q.tenant_id AND b.active
  JOIN abc.sessions s ON s.session_id=q.session_id
    AND s.tenant_id=q.tenant_id AND s.branch_id=q.branch_id
    AND s.state='CREATED' AND s.state_version=q.state_version
    AND s.service_id='synthetic:hair-color'
  JOIN abc.consent_evidence ce ON ce.session_id=s.session_id
    AND ce.tenant_id=s.tenant_id AND ce.branch_id=s.branch_id
    AND ce.client_id=s.client_id AND ce.status='ACTIVE'
    AND ce.verified_at IS NOT NULL AND ce.revoked_at IS NULL
    AND ce.valid_until>v_now
    AND ce.purpose @> ARRAY['AI_PROCESSING','INTERNAL_HANDOFF']::text[]
 WHERE q.consumer_id=p_consumer AND q.attempts<3 AND
  ((q.status='QUEUED' AND q.available_at<=v_now)
   OR(q.status='LEASED' AND q.lease_until<v_now))
 ORDER BY q.created_at,q.job_id LIMIT 1 FOR UPDATE OF q SKIP LOCKED;
 IF NOT FOUND THEN RETURN NULL; END IF;
 SELECT jsonb_agg(jsonb_build_object('evidence',e.evidence_json,
     'evidence_id',e.evidence_id,'digest',trim(e.evidence_digest),
     'source_job_id',e.source_job_id,'source_answer_id',e.source_answer_id,
     'policy_decision_id',e.policy_decision_id)
   ORDER BY e.evidence_id),
   count(*),count(DISTINCT e.evidence_json->>'attribute_key'),
   encode(sha256(convert_to(string_agg(
       e.evidence_id::text||':'||trim(e.evidence_digest),'|'
       ORDER BY e.evidence_id),'UTF8')),'hex')
 INTO v_src,v_count,v_distinct,v_hash
 FROM abc.eng03_evidence_ledger e
 JOIN abc.eng03_input_jobs src ON src.job_id=e.source_job_id
   AND src.status='ACKED' AND src.consumer_id=e.consumer_id
   AND src.tenant_id=e.tenant_id AND src.session_id=e.session_id
 JOIN abc.eng14_policy_audit pol ON pol.decision_id=e.policy_decision_id
   AND pol.decision='ALLOW' AND pol.policy_version='eng14.synthetic.1'
   AND pol.tenant_id=e.tenant_id AND pol.branch_id=e.branch_id
   AND pol.session_id=e.session_id
 WHERE e.tenant_id=j.tenant_id AND e.branch_id=j.branch_id
   AND e.session_id=j.session_id AND e.consumer_id=j.consumer_id
   AND e.aggregate_version<=j.state_version
   AND e.evidence_json->>'session_id'=j.session_id::text
   AND e.evidence_json->>'service_id'='synthetic:hair-color'
   AND e.evidence_json->>'evidence_id'=e.evidence_id::text
   AND e.evidence_json->>'attribute_key'
      IN ('prior_treatment','sensitivity_flag','goal','maintenance');
 IF v_count IS DISTINCT FROM 4 OR v_distinct IS DISTINCT FROM 4
    OR v_hash IS NULL THEN
   RAISE EXCEPTION 'ENG03 four-source proof incomplete' USING ERRCODE='42501'; END IF;
 v_lease:=gen_random_uuid();
 UPDATE abc.eng04_ci_jobs SET status='LEASED',attempts=attempts+1,
   lease_token=v_lease,lease_until=v_now+make_interval(secs=>p_seconds),
   updated_at=v_now WHERE job_id=j.job_id;
 RETURN jsonb_build_object('job_id',j.job_id,'consumer_id',j.consumer_id,
  'tenant_id',j.tenant_id,'branch_id',j.branch_id,
  'session_id',j.session_id,'state_version',j.state_version,
  'lease_token',v_lease,'attempt',j.attempts+1,'sources',v_src,
  'source_manifest_sha256',v_hash,'engine_id','ENG-04',
  'artifact_kind','BEAUTY_ANALYSIS_REPORT');
END;$claim$;

CREATE FUNCTION abc.eng04_ci_ack(p_job uuid,p_lease uuid,p_manifest text,p_output bytea)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,abc
AS $ack$
DECLARE j abc.eng04_ci_jobs%ROWTYPE;v jsonb;
 v_hash text;v_ids jsonb;v_count integer;v_now timestamptz:=clock_timestamp();
BEGIN
 IF session_user='abc_eng04_worker' OR p_job IS NULL OR p_lease IS NULL
    OR p_output IS NULL OR octet_length(p_output) NOT BETWEEN 32 AND 32768
 THEN RAISE EXCEPTION 'ENG04 ACK invalid' USING ERRCODE='42501';END IF;
 SELECT * INTO j FROM abc.eng04_ci_jobs WHERE job_id=p_job FOR UPDATE;
 IF NOT FOUND OR j.status<>'LEASED' OR j.lease_token IS DISTINCT FROM p_lease
   OR j.lease_until<=v_now
   OR NOT EXISTS(SELECT 1 FROM abc.eng04_ci_worker_bindings b
      WHERE b.login_name=session_user AND b.consumer_id=j.consumer_id
        AND b.tenant_id=j.tenant_id AND b.active)
 THEN RAISE EXCEPTION 'ENG04 lease revoked' USING ERRCODE='42501'; END IF;
 IF NOT EXISTS(SELECT 1 FROM abc.sessions s JOIN abc.consent_evidence ce
   ON ce.session_id=s.session_id AND ce.tenant_id=s.tenant_id
     AND ce.branch_id=s.branch_id AND ce.client_id=s.client_id
   WHERE s.session_id=j.session_id AND s.tenant_id=j.tenant_id
     AND s.branch_id=j.branch_id AND s.state='CREATED'
     AND s.state_version=j.state_version AND ce.status='ACTIVE'
     AND ce.verified_at IS NOT NULL AND ce.revoked_at IS NULL
     AND ce.valid_until>v_now
     AND ce.purpose @> ARRAY['AI_PROCESSING','INTERNAL_HANDOFF']::text[]
   FOR SHARE OF s,ce)
 THEN RAISE EXCEPTION 'ENG04 consent revoked' USING ERRCODE='42501';END IF;
 SELECT encode(sha256(convert_to(string_agg(
     e.evidence_id::text||':'||trim(e.evidence_digest),'|'
     ORDER BY e.evidence_id),'UTF8')),'hex'),
   to_jsonb(array_agg(e.evidence_id::text ORDER BY e.evidence_id)),
   count(*) INTO v_hash,v_ids,v_count
 FROM abc.eng03_evidence_ledger e JOIN abc.eng03_input_jobs src
    ON src.job_id=e.source_job_id AND src.status='ACKED'
 WHERE e.tenant_id=j.tenant_id AND e.branch_id=j.branch_id
   AND e.session_id=j.session_id AND e.consumer_id=j.consumer_id
   AND e.aggregate_version<=j.state_version;
 IF v_count IS DISTINCT FROM 4 OR v_hash IS DISTINCT FROM p_manifest
 THEN RAISE EXCEPTION 'ENG04 provenance drift' USING ERRCODE='42501';END IF;
 v:=convert_from(p_output,'UTF8')::jsonb;
 IF jsonb_typeof(v) IS DISTINCT FROM 'object'
    OR v->>'engine_version' IS DISTINCT FROM 'eng04.synthetic-evidence.1'
    OR v->>'service_scope' IS DISTINCT FROM 'SYNTHETIC_NON_MEDIA_ONLY'
    OR v->>'session_id' IS DISTINCT FROM j.session_id::text
    OR v->>'service_id' IS DISTINCT FROM 'synthetic:hair-color'
    OR v->>'source_engine' IS DISTINCT FROM 'ENG-03'
    OR v->>'source_manifest_sha256' IS DISTINCT FROM p_manifest
    OR v->>'professional_validation_verified' IS DISTINCT FROM 'false'
    OR v->'evidence_ids' IS DISTINCT FROM v_ids
    OR v->>'customer_release_approved' IS NOT NULL
 THEN RAISE EXCEPTION 'ENG04 output contract invalid' USING ERRCODE='42501';END IF;
 INSERT INTO abc.eng04_ci_results(job_id,engine_id,engine_version,
     worker_lease,source_manifest_sha256,output_sha256,output_bytes,
     artifact_kind,status)
 VALUES(p_job,'ENG-04','eng04.synthetic-evidence.1',p_lease,v_hash,
   encode(sha256(p_output),'hex'),p_output,'BEAUTY_ANALYSIS_REPORT',
   'BLOCKED_PENDING_AUTHORITY');
 UPDATE abc.eng04_ci_jobs SET status='ACKED',lease_token=NULL,
   lease_until=NULL,updated_at=clock_timestamp() WHERE job_id=p_job;
 RETURN 'ACKED_REVIEW_ONLY';
END;$ack$;

CREATE FUNCTION abc.eng04_ci_fail(p_job uuid,p_lease uuid,p_code text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,abc
AS $fail$
DECLARE j abc.eng04_ci_jobs%ROWTYPE;v text;
BEGIN
 IF session_user='abc_eng04_worker' OR p_code IS NULL
    OR p_code !~ '^CI_[A-Z_]{3,60}$'
 THEN RAISE EXCEPTION 'ENG04 failure invalid' USING ERRCODE='42501';END IF;
 SELECT * INTO j FROM abc.eng04_ci_jobs WHERE job_id=p_job FOR UPDATE;
 IF NOT FOUND OR j.status<>'LEASED' OR j.lease_token IS DISTINCT FROM p_lease
   OR j.lease_until<=clock_timestamp()
   OR NOT EXISTS(SELECT 1 FROM abc.eng04_ci_worker_bindings b
     WHERE b.login_name=session_user AND b.consumer_id=j.consumer_id
       AND b.tenant_id=j.tenant_id AND b.active)
 THEN RAISE EXCEPTION 'ENG04 failure lease revoked' USING ERRCODE='42501';END IF;
 v:=CASE WHEN j.attempts>=3 THEN 'DLQ' ELSE 'QUEUED' END;
 UPDATE abc.eng04_ci_jobs SET status=v,lease_token=NULL,lease_until=NULL,
    failure_code=p_code,available_at=clock_timestamp()+make_interval(secs=>j.attempts),
    updated_at=clock_timestamp() WHERE job_id=p_job;
 RETURN v;
END;$fail$;
CREATE FUNCTION abc.eng04_ci_result_for_review(p_job uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,abc
AS $export$
DECLARE j abc.eng04_ci_jobs%ROWTYPE;r abc.eng04_ci_results%ROWTYPE;
BEGIN
 IF session_user='abc_eng04_worker' THEN
  RAISE EXCEPTION 'ENG04 physical login required' USING ERRCODE='42501';END IF;
 SELECT * INTO j FROM abc.eng04_ci_jobs WHERE job_id=p_job;
 SELECT * INTO r FROM abc.eng04_ci_results WHERE job_id=p_job;
 IF NOT FOUND OR j.status IS DISTINCT FROM 'ACKED'
  OR r.status IS DISTINCT FROM 'BLOCKED_PENDING_AUTHORITY'
  OR NOT EXISTS(SELECT 1 FROM abc.eng04_ci_worker_bindings b
    WHERE b.login_name=session_user AND b.consumer_id=j.consumer_id
      AND b.tenant_id=j.tenant_id AND b.active)
  OR NOT EXISTS(SELECT 1 FROM abc.sessions s JOIN abc.consent_evidence ce
     ON ce.session_id=s.session_id AND ce.tenant_id=s.tenant_id
       AND ce.branch_id=s.branch_id AND ce.client_id=s.client_id
     WHERE s.session_id=j.session_id AND s.tenant_id=j.tenant_id
       AND s.branch_id=j.branch_id AND s.state='CREATED'
       AND s.state_version=j.state_version AND ce.status='ACTIVE'
       AND ce.verified_at IS NOT NULL AND ce.revoked_at IS NULL
       AND ce.valid_until>clock_timestamp()
       AND ce.purpose @> ARRAY['AI_PROCESSING','INTERNAL_HANDOFF']::text[])
  OR encode(sha256(r.output_bytes),'hex') IS DISTINCT FROM r.output_sha256
 THEN RAISE EXCEPTION 'ENG04 review export denied' USING ERRCODE='42501';END IF;
 RETURN jsonb_build_object('analysis',convert_from(r.output_bytes,'UTF8')::jsonb,
    'analysis_sha256',r.output_sha256,'source_manifest_sha256',
     r.source_manifest_sha256,'tenant_id',j.tenant_id,
     'branch_id',j.branch_id,'session_id',j.session_id,
     'state_version',j.state_version,'consumer_id',j.consumer_id,
     'status','BLOCKED_PENDING_AUTHORITY');
END;$export$;
REVOKE ALL ON FUNCTION abc.eng04_ci_result_for_review(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION abc.eng04_ci_result_for_review(uuid) TO abc_eng04_worker;
REVOKE ALL ON FUNCTION abc.eng04_ci_claim(text,integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION abc.eng04_ci_ack(uuid,uuid,text,bytea) FROM PUBLIC;
REVOKE ALL ON FUNCTION abc.eng04_ci_fail(uuid,uuid,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION abc.eng04_ci_claim(text,integer) TO abc_eng04_worker;
GRANT EXECUTE ON FUNCTION abc.eng04_ci_ack(uuid,uuid,text,bytea) TO abc_eng04_worker;
GRANT EXECUTE ON FUNCTION abc.eng04_ci_fail(uuid,uuid,text) TO abc_eng04_worker;
COMMIT;

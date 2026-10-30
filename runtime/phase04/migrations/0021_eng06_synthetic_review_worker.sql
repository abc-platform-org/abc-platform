-- 0021: Isolated ENG06 synthetic decision worker (manual CI seeding ONLY).
-- NO automatic ENG05 outbox release, NO ENG07 dispatch, NO customer use.
BEGIN;
DO $role$ BEGIN
  IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='abc_eng06_review_worker') THEN
    CREATE ROLE abc_eng06_review_worker NOLOGIN NOINHERIT
      NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
  END IF;
END $role$;
GRANT USAGE ON SCHEMA abc TO abc_eng06_review_worker;

CREATE TABLE abc.eng06_ci_worker_bindings(
  login_name name PRIMARY KEY, consumer_id text NOT NULL,
  tenant_id text NOT NULL REFERENCES abc.tenants(tenant_id),
  active boolean NOT NULL DEFAULT false,
  CHECK(length(consumer_id) BETWEEN 3 AND 64)
);
CREATE TABLE abc.eng06_ci_jobs(
  upstream_handoff uuid PRIMARY KEY REFERENCES abc.eng19_synthetic_outbox(handoff_id),
  consumer_id text NOT NULL CHECK(length(consumer_id) BETWEEN 3 AND 64),
  tenant_id text NOT NULL REFERENCES abc.tenants(tenant_id),
  branch_id text NOT NULL,session_id uuid NOT NULL REFERENCES abc.sessions(session_id),
  state_version integer NOT NULL CHECK(state_version>=0),
  status text NOT NULL DEFAULT 'QUEUED'
    CHECK(status IN ('QUEUED','LEASED','ACKED','DLQ')),
  attempts integer NOT NULL DEFAULT 0 CHECK(attempts BETWEEN 0 AND 3),
  lease_token uuid,lease_until timestamptz,
  available_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  failure_code text,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  CHECK(status<>'LEASED' OR (lease_token IS NOT NULL AND lease_until IS NOT NULL))
);
CREATE INDEX eng06_ci_ready ON abc.eng06_ci_jobs(status,available_at,lease_until);
CREATE TABLE abc.eng06_ci_results(
  upstream_handoff uuid PRIMARY KEY REFERENCES abc.eng06_ci_jobs(upstream_handoff),
  worker_lease uuid NOT NULL,
  engine_id text NOT NULL CHECK(engine_id='ENG-06'),
  engine_version text NOT NULL CHECK(engine_version='eng06.synthetic.1'),
  analysis_sha256 text NOT NULL CHECK(analysis_sha256 ~ '^[a-f0-9]{64}$'),
  knowledge_sha256 text NOT NULL CHECK(knowledge_sha256 ~ '^[a-f0-9]{64}$'),
  output_sha256 text NOT NULL CHECK(output_sha256 ~ '^[a-f0-9]{64}$'),
  output_bytes bytea NOT NULL CHECK(octet_length(output_bytes) BETWEEN 32 AND 32768),
  status text NOT NULL CHECK(status='BLOCKED_PROFESSIONAL_SOURCE'),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
DO $acl$ DECLARE t text; BEGIN
  FOREACH t IN ARRAY ARRAY['eng06_ci_worker_bindings','eng06_ci_jobs','eng06_ci_results'] LOOP
    EXECUTE format('ALTER TABLE abc.%I ENABLE ROW LEVEL SECURITY',t);
    EXECUTE format('ALTER TABLE abc.%I FORCE ROW LEVEL SECURITY',t);
    EXECUTE format('REVOKE ALL ON abc.%I FROM PUBLIC,abc_app,abc_worker,abc_answer_worker,abc_orchestrator,abc_eng03_worker,abc_pipeline_worker,abc_eng06_review_worker',t);
    IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='abc_staging_migrator') THEN
      EXECUTE format('CREATE POLICY eng06_migrator_all ON abc.%I FOR ALL TO abc_staging_migrator USING(true) WITH CHECK(true)',t);
    END IF;
  END LOOP;
END $acl$;

-- These SECURITY DEFINER functions are owned by the migration authority.
-- No queue-submit function or external dispatcher is granted. The only queue
-- insertion in this phase is by disposable CI administrator test fixture.
CREATE FUNCTION abc.eng06_ci_claim(p_consumer text,p_seconds integer DEFAULT 30)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,abc
AS $claim$
DECLARE j abc.eng06_ci_jobs%ROWTYPE;v_now timestamptz:=clock_timestamp();
        v_lease uuid;v_analysis bytea;v_knowledge bytea;v_asha text;v_ksha text;
BEGIN
  IF session_user='abc_eng06_review_worker' OR p_consumer IS NULL
     OR length(p_consumer) NOT BETWEEN 3 AND 64
     OR p_seconds IS NULL OR p_seconds NOT BETWEEN 1 AND 120
     OR NOT EXISTS(SELECT 1 FROM abc.eng06_ci_worker_bindings b
           WHERE b.login_name=session_user AND b.consumer_id=p_consumer AND b.active)
  THEN RAISE EXCEPTION 'dedicated ENG06 worker denied' USING ERRCODE='42501'; END IF;
  UPDATE abc.eng06_ci_jobs expired SET status='DLQ',
         lease_token=NULL,lease_until=NULL,failure_code='CI_LEASE_EXHAUSTED',
         updated_at=v_now
    WHERE expired.consumer_id=p_consumer AND expired.status='LEASED'
      AND expired.lease_until<v_now AND expired.attempts>=3
      AND EXISTS(SELECT 1 FROM abc.eng06_ci_worker_bindings b
          WHERE b.login_name=session_user AND b.consumer_id=expired.consumer_id
            AND b.tenant_id=expired.tenant_id AND b.active);
  SELECT job.* INTO j FROM abc.eng06_ci_jobs job
    JOIN abc.eng06_ci_worker_bindings b
      ON b.login_name=session_user AND b.consumer_id=job.consumer_id
        AND b.tenant_id=job.tenant_id AND b.active
    JOIN abc.eng19_synthetic_outbox o
      ON o.handoff_id=job.upstream_handoff
        AND o.from_engine='ENG-05' AND o.to_engine='ENG-06'
        AND o.artifact_kind='PROFESSIONAL_KNOWLEDGE_BUNDLE'
        AND o.status='BLOCKED_PENDING_AUTHORITY'
    JOIN abc.eng19_synthetic_results r
      ON r.handoff_id=o.handoff_id AND r.engine_id='ENG-05'
        AND r.engine_version='synthetic-ontology.1'
        AND r.output_sha256=o.artifact_sha256
    JOIN abc.eng19_synthetic_jobs src
      ON src.handoff_id=job.upstream_handoff
       AND src.status='ACKED' AND src.tenant_id=job.tenant_id
       AND src.branch_id=job.branch_id AND src.session_id=job.session_id
       AND src.state_version=job.state_version
    JOIN abc.sessions s
      ON s.session_id=job.session_id AND s.tenant_id=job.tenant_id
       AND s.branch_id=job.branch_id AND s.state='CREATED'
       AND s.state_version=job.state_version
    JOIN abc.consent_evidence ce
      ON ce.session_id=s.session_id AND ce.tenant_id=s.tenant_id
       AND ce.branch_id=s.branch_id AND ce.client_id=s.client_id
       AND ce.status='ACTIVE' AND ce.verified_at IS NOT NULL
       AND ce.revoked_at IS NULL AND ce.valid_until>v_now
       AND ce.purpose @> ARRAY['AI_PROCESSING','INTERNAL_HANDOFF']::text[]
    WHERE job.consumer_id=p_consumer AND job.attempts<3
      AND ((job.status='QUEUED' AND job.available_at<=v_now)
          OR (job.status='LEASED' AND job.lease_until<v_now))
    ORDER BY job.created_at,job.upstream_handoff
    LIMIT 1 FOR UPDATE OF job SKIP LOCKED;
  IF NOT FOUND THEN RETURN NULL; END IF;
  SELECT src.source_bytes,r.output_bytes,src.source_sha256,r.output_sha256
    INTO v_analysis,v_knowledge,v_asha,v_ksha
    FROM abc.eng19_synthetic_jobs src
      JOIN abc.eng19_synthetic_results r ON r.handoff_id=src.handoff_id
    WHERE src.handoff_id=j.upstream_handoff AND src.status='ACKED';
  IF NOT FOUND OR encode(sha256(v_analysis),'hex') IS DISTINCT FROM v_asha
     OR encode(sha256(v_knowledge),'hex') IS DISTINCT FROM v_ksha
     OR convert_from(v_analysis,'UTF8')::jsonb->>'session_id' IS DISTINCT FROM j.session_id::text
     OR convert_from(v_knowledge,'UTF8')::jsonb->>'ontology_version'<>'synthetic-ontology.1'
     OR convert_from(v_knowledge,'UTF8')::jsonb->'retrieval_sources' IS DISTINCT FROM '[]'::jsonb
     OR NOT(convert_from(v_knowledge,'UTF8')::jsonb->'unknowns' ? 'SOURCE_UNVERIFIED')
  THEN RAISE EXCEPTION 'untrusted ENG05 provenance' USING ERRCODE='42501'; END IF;
  v_lease:=gen_random_uuid();
  UPDATE abc.eng06_ci_jobs SET status='LEASED',lease_token=v_lease,
    lease_until=v_now+make_interval(secs=>p_seconds),
    attempts=attempts+1,updated_at=v_now
    WHERE upstream_handoff=j.upstream_handoff;
  RETURN jsonb_build_object(
    'upstream_handoff',j.upstream_handoff,'consumer_id',j.consumer_id,
    'tenant_id',j.tenant_id,'branch_id',j.branch_id,
    'session_id',j.session_id,'state_version',j.state_version,
    'lease_token',v_lease,'attempt',j.attempts+1,
    'analysis',convert_from(v_analysis,'UTF8')::jsonb,
    'knowledge',convert_from(v_knowledge,'UTF8')::jsonb,
    'analysis_sha256',v_asha,'knowledge_sha256',v_ksha,
    'engine_id','ENG-06','engine_version','eng06.synthetic.1');
END;$claim$;

CREATE FUNCTION abc.eng06_ci_ack(
 p_handoff uuid,p_lease uuid,p_analysis_sha text,p_knowledge_sha text,p_output bytea
) RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,abc
AS $ack$
DECLARE j abc.eng06_ci_jobs%ROWTYPE;v jsonb;v_a text;v_k text;v_now timestamptz:=clock_timestamp();
BEGIN
  IF session_user='abc_eng06_review_worker' OR p_handoff IS NULL
     OR p_lease IS NULL OR p_output IS NULL
     OR octet_length(p_output) NOT BETWEEN 32 AND 32768
  THEN RAISE EXCEPTION 'invalid ENG06 ACK' USING ERRCODE='42501'; END IF;
  SELECT * INTO j FROM abc.eng06_ci_jobs WHERE upstream_handoff=p_handoff FOR UPDATE;
  IF NOT FOUND OR j.status<>'LEASED' OR j.lease_token IS DISTINCT FROM p_lease
     OR j.lease_until<=v_now
     OR NOT EXISTS(SELECT 1 FROM abc.eng06_ci_worker_bindings b
       WHERE b.login_name=session_user AND b.consumer_id=j.consumer_id
         AND b.tenant_id=j.tenant_id AND b.active)
  THEN RAISE EXCEPTION 'ENG06 expired or revoked lease' USING ERRCODE='42501'; END IF;
  IF NOT EXISTS(SELECT 1 FROM abc.sessions s
       JOIN abc.consent_evidence ce
         ON ce.session_id=s.session_id AND ce.tenant_id=s.tenant_id
           AND ce.branch_id=s.branch_id AND ce.client_id=s.client_id
       WHERE s.session_id=j.session_id AND s.tenant_id=j.tenant_id
         AND s.branch_id=j.branch_id AND s.state='CREATED'
         AND s.state_version=j.state_version
         AND ce.status='ACTIVE' AND ce.verified_at IS NOT NULL
         AND ce.revoked_at IS NULL AND ce.valid_until>v_now
         AND ce.purpose @> ARRAY['AI_PROCESSING','INTERNAL_HANDOFF']::text[]
       FOR SHARE OF s,ce)
  THEN RAISE EXCEPTION 'ENG06 consent or state revoked' USING ERRCODE='42501'; END IF;
  SELECT src.source_sha256,r.output_sha256 INTO v_a,v_k
    FROM abc.eng19_synthetic_jobs src
      JOIN abc.eng19_synthetic_results r ON r.handoff_id=src.handoff_id
      JOIN abc.eng19_synthetic_outbox o ON o.handoff_id=r.handoff_id
    WHERE src.handoff_id=j.upstream_handoff AND src.status='ACKED'
      AND o.status='BLOCKED_PENDING_AUTHORITY'
      AND o.artifact_sha256=r.output_sha256
      AND encode(sha256(src.source_bytes),'hex')=src.source_sha256
      AND encode(sha256(r.output_bytes),'hex')=r.output_sha256;
  IF NOT FOUND OR v_a IS DISTINCT FROM p_analysis_sha
     OR v_k IS DISTINCT FROM p_knowledge_sha
  THEN RAISE EXCEPTION 'ENG06 source artifact drift' USING ERRCODE='42501'; END IF;
  v:=convert_from(p_output,'UTF8')::jsonb;
  IF jsonb_typeof(v)<>'object' OR v->>'engine_id' IS DISTINCT FROM 'ENG-06'
     OR v->>'engine_version' IS DISTINCT FROM 'eng06.synthetic.1'
     OR v->>'status' IS DISTINCT FROM 'BLOCKED_PROFESSIONAL_SOURCE'
     OR v->>'analysis_sha256' IS DISTINCT FROM v_a
     OR v->>'knowledge_sha256' IS DISTINCT FROM v_k
     OR v->>'downstream_dispatch_authorized' IS DISTINCT FROM 'false'
     OR v->>'customer_release_approved' IS DISTINCT FROM 'false'
     OR v->'decision'->>'session_id' IS DISTINCT FROM j.session_id::text
     OR v->'decision'->>'decision_engine_version' IS DISTINCT FROM 'eng06.synthetic.1'
     OR v->'decision'->'candidates' IS DISTINCT FROM '[]'::jsonb
     OR jsonb_typeof(v->'decision'->'excluded_options') IS DISTINCT FROM 'array'
     OR jsonb_array_length(v->'decision'->'excluded_options') IS DISTINCT FROM 2
     OR EXISTS(SELECT 1 FROM jsonb_array_elements(v->'decision'->'excluded_options') e
               WHERE e->>'reason' IS DISTINCT FROM 'UNVERIFIED_KNOWLEDGE_SOURCE')
  THEN RAISE EXCEPTION 'ENG06 unverified recommendation denied' USING ERRCODE='42501'; END IF;
  INSERT INTO abc.eng06_ci_results(
    upstream_handoff,worker_lease,engine_id,engine_version,
    analysis_sha256,knowledge_sha256,output_sha256,output_bytes,status)
  VALUES(p_handoff,p_lease,'ENG-06','eng06.synthetic.1',
    v_a,v_k,encode(sha256(p_output),'hex'),p_output,'BLOCKED_PROFESSIONAL_SOURCE');
  UPDATE abc.eng06_ci_jobs SET status='ACKED',lease_token=NULL,
      lease_until=NULL,updated_at=clock_timestamp() WHERE upstream_handoff=p_handoff;
  RETURN 'ACKED_BLOCKED_REVIEW_ONLY';
END;$ack$;

CREATE FUNCTION abc.eng06_ci_fail(p_handoff uuid,p_lease uuid,p_error text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,abc
AS $fail$
DECLARE j abc.eng06_ci_jobs%ROWTYPE; v_status text;
BEGIN
 IF session_user='abc_eng06_review_worker' OR p_error IS NULL
    OR p_error !~ '^CI_[A-Z_]{3,60}$'
 THEN RAISE EXCEPTION 'ENG06 failure receipt denied' USING ERRCODE='42501'; END IF;
 SELECT * INTO j FROM abc.eng06_ci_jobs WHERE upstream_handoff=p_handoff FOR UPDATE;
 IF NOT FOUND OR j.status<>'LEASED' OR j.lease_token IS DISTINCT FROM p_lease
    OR j.lease_until<=clock_timestamp()
    OR NOT EXISTS(SELECT 1 FROM abc.eng06_ci_worker_bindings b
      WHERE b.login_name=session_user AND b.consumer_id=j.consumer_id
        AND b.tenant_id=j.tenant_id AND b.active)
 THEN RAISE EXCEPTION 'ENG06 stale failure receipt' USING ERRCODE='42501'; END IF;
 v_status:=CASE WHEN j.attempts>=3 THEN 'DLQ' ELSE 'QUEUED' END;
 UPDATE abc.eng06_ci_jobs SET status=v_status,
   available_at=clock_timestamp()+make_interval(secs=>j.attempts),
   failure_code=p_error,lease_token=NULL,lease_until=NULL,
   updated_at=clock_timestamp() WHERE upstream_handoff=p_handoff;
 RETURN v_status;
END;$fail$;

REVOKE ALL ON FUNCTION abc.eng06_ci_claim(text,integer) FROM PUBLIC;
REVOKE ALL ON FUNCTION abc.eng06_ci_ack(uuid,uuid,text,text,bytea) FROM PUBLIC;
REVOKE ALL ON FUNCTION abc.eng06_ci_fail(uuid,uuid,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION abc.eng06_ci_claim(text,integer) TO abc_eng06_review_worker;
GRANT EXECUTE ON FUNCTION abc.eng06_ci_ack(uuid,uuid,text,text,bytea) TO abc_eng06_review_worker;
GRANT EXECUTE ON FUNCTION abc.eng06_ci_fail(uuid,uuid,text) TO abc_eng06_review_worker;
COMMIT;

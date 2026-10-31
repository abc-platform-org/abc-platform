-- 0025: Independent ENG05 review worker consumes exact, ACKed ENG04 results.
-- Synthetic CI only; no new dispatcher, professional sources or ENG06 release.
BEGIN;
CREATE TABLE abc.eng05_ci_source_receipts(
  handoff_id uuid PRIMARY KEY REFERENCES abc.eng19_synthetic_results(handoff_id),
  eng04_job_id uuid NOT NULL REFERENCES abc.eng04_ci_results(job_id),
  tenant_id text NOT NULL REFERENCES abc.tenants(tenant_id),
  consumer_id text NOT NULL CHECK(length(consumer_id) BETWEEN 3 AND 64),
  eng04_artifact_sha256 text NOT NULL CHECK(eng04_artifact_sha256 ~ '^[a-f0-9]{64}$'),
  eng03_manifest_sha256 text NOT NULL CHECK(eng03_manifest_sha256 ~ '^[a-f0-9]{64}$'),
  eng05_result_sha256 text NOT NULL CHECK(eng05_result_sha256 ~ '^[a-f0-9]{64}$'),
  status text NOT NULL CHECK(status='BLOCKED_PENDING_AUTHORITY'),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
ALTER TABLE abc.eng05_ci_source_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.eng05_ci_source_receipts FORCE ROW LEVEL SECURITY;
REVOKE ALL ON abc.eng05_ci_source_receipts FROM PUBLIC,abc_app,
  abc_worker,abc_answer_worker,abc_orchestrator,abc_eng03_worker,
  abc_pipeline_worker,abc_eng04_worker,abc_eng05_worker,abc_eng06_review_worker;
DO $acl$
BEGIN
  IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='abc_staging_migrator') THEN
    CREATE POLICY eng05_migrator_source_provenance ON abc.eng05_ci_source_receipts
      FOR ALL TO abc_staging_migrator USING(true) WITH CHECK(true);
  END IF;
END;$acl$;

-- Must be invoked only by migration-owned SECDEF broker functions; callers
-- cannot invoke it directly. Historical synthetic tenant-test sources
-- without ENG03 claims use the old local fixture flow unchanged.
CREATE FUNCTION abc.eng05_ci_verify_eng04_source(p_handoff uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,abc
AS $proof$
DECLARE v_job abc.eng19_synthetic_jobs%ROWTYPE;
  v_payload jsonb;v_e4 abc.eng04_ci_jobs%ROWTYPE;
  v_result abc.eng04_ci_results%ROWTYPE;
  v_count integer;v_distinct integer;v_manifest text;
BEGIN
  SELECT * INTO v_job FROM abc.eng19_synthetic_jobs WHERE handoff_id=p_handoff;
  IF NOT FOUND THEN RAISE EXCEPTION 'ENG05 source job not found'
     USING ERRCODE='42501';END IF;
  IF v_job.source_sha256 IS DISTINCT FROM encode(sha256(v_job.source_bytes),'hex')
  THEN RAISE EXCEPTION 'ENG05 persisted bytes invalid'
     USING ERRCODE='42501'; END IF;
  v_payload:=convert_from(v_job.source_bytes,'UTF8')::jsonb;
  IF jsonb_typeof(v_payload) IS DISTINCT FROM 'object'
  THEN RAISE EXCEPTION 'ENG05 non-object source denied' USING ERRCODE='42501';END IF;
  IF NOT (v_payload ?| ARRAY['source_engine','source_manifest_sha256',
                              'professional_validation_verified']) THEN
    -- Frozen, synthetic tenant-test fixture only: never accepted for new
    -- tenants, and never treated as professional-validated provenance.
    IF v_job.tenant_id IS DISTINCT FROM 'tenant-test'
      OR v_job.branch_id IS DISTINCT FROM 'branch-test'
    THEN RAISE EXCEPTION 'unverified legacy source scope denied'
       USING ERRCODE='42501';END IF;
    RETURN NULL;
  END IF;
  IF v_payload->>'source_engine' IS DISTINCT FROM 'ENG-03'
    OR v_payload->>'source_manifest_sha256' !~ '^[a-f0-9]{64}$'
    OR v_payload->>'professional_validation_verified' IS DISTINCT FROM 'false'
    OR v_payload->>'engine_version' IS DISTINCT FROM 'eng04.synthetic-evidence.1'
    OR v_payload->>'service_scope' IS DISTINCT FROM 'SYNTHETIC_NON_MEDIA_ONLY'
    OR v_payload->>'session_id' IS DISTINCT FROM v_job.session_id::text
    OR v_payload->>'service_id' IS DISTINCT FROM 'synthetic:hair-color'
    OR jsonb_typeof(v_payload->'evidence_ids') IS DISTINCT FROM 'array'
    OR jsonb_array_length(v_payload->'evidence_ids') IS DISTINCT FROM 4
  THEN RAISE EXCEPTION 'ENG05 untrusted ENG04 report'
     USING ERRCODE='42501';END IF;
  -- Share-lock source identity to serialize binding revocation against ACK.
  SELECT j.* INTO v_e4 FROM abc.eng04_ci_jobs j
    JOIN abc.eng04_ci_results r ON r.job_id=j.job_id
    JOIN abc.eng04_ci_worker_bindings binding
      ON binding.tenant_id=j.tenant_id
       AND binding.consumer_id=j.consumer_id
       AND binding.login_name='abc_eng04_ci_login' AND binding.active
    WHERE j.session_id=v_job.session_id AND j.tenant_id=v_job.tenant_id
      AND j.branch_id=v_job.branch_id AND j.consumer_id=v_job.consumer_id
      AND j.state_version=v_job.state_version AND j.status='ACKED'
      AND r.status='BLOCKED_PENDING_AUTHORITY'
      AND r.artifact_kind='BEAUTY_ANALYSIS_REPORT'
      AND r.engine_id='ENG-04'
      AND r.engine_version='eng04.synthetic-evidence.1'
      AND r.output_bytes=v_job.source_bytes
      AND r.output_sha256=v_job.source_sha256
      AND r.source_manifest_sha256=v_payload->>'source_manifest_sha256'
    LIMIT 1 FOR SHARE OF j,r,binding;
  IF NOT FOUND THEN RAISE EXCEPTION 'ENG05 exact ACKed ENG04 proof missing'
    USING ERRCODE='42501'; END IF;
  SELECT * INTO v_result FROM abc.eng04_ci_results
    WHERE job_id=v_e4.job_id;
  SELECT count(*),count(DISTINCT e.evidence_id),
   encode(sha256(convert_to(string_agg(
     e.evidence_id::text||':'||trim(e.evidence_digest),'|'
     ORDER BY e.evidence_id),'UTF8')),'hex')
  INTO v_count,v_distinct,v_manifest
  FROM abc.eng03_evidence_ledger e
  JOIN abc.eng03_input_jobs src ON src.job_id=e.source_job_id
     AND src.consumer_id=e.consumer_id AND src.status='ACKED'
  WHERE e.consumer_id=v_e4.consumer_id AND e.tenant_id=v_e4.tenant_id
    AND e.branch_id=v_e4.branch_id AND e.session_id=v_e4.session_id
    AND e.aggregate_version<=v_e4.state_version;
  IF v_count IS DISTINCT FROM 4 OR v_distinct IS DISTINCT FROM 4
     OR v_manifest IS DISTINCT FROM v_result.source_manifest_sha256
  THEN RAISE EXCEPTION 'ENG05 ENG03 source manifest drift'
    USING ERRCODE='42501'; END IF;
  RETURN jsonb_build_object('eng04_job_id',v_e4.job_id,
    'eng04_artifact_sha256',v_job.source_sha256,
    'eng03_manifest_sha256',v_manifest,
    'source_identity_verified',true,
    'professional_validation_verified',false,
    'eng05_to_eng06_release_approved',false);
END;$proof$;
REVOKE ALL ON FUNCTION abc.eng05_ci_verify_eng04_source(uuid) FROM PUBLIC,
  abc_app,abc_worker,abc_answer_worker,abc_orchestrator,
  abc_eng03_worker,abc_pipeline_worker,abc_eng04_worker,
  abc_eng05_worker,abc_eng06_review_worker;

-- Versioned recompile of the two ENG05 broker functions in historical 0022.
-- Existing lease and revocation semantics are retained; the only additional
-- preconditions are independently persisted ENG04 lineage and result receipt.
CREATE OR REPLACE FUNCTION abc.eng19_claim_synthetic(p_consumer text,p_seconds integer DEFAULT 30)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,abc
AS $claim$
DECLARE j abc.eng19_synthetic_jobs%ROWTYPE;v_lease uuid;v_now timestamptz:=clock_timestamp(); v_verified jsonb;
BEGIN
  IF session_user='abc_eng05_worker' OR p_seconds NOT BETWEEN 1 AND 120
     OR p_consumer IS NULL
     OR NOT EXISTS (SELECT 1 FROM abc.eng05_worker_bindings w
       WHERE w.login_name=session_user AND w.worker_role='abc_eng05_worker'
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
      AND EXISTS(SELECT 1 FROM abc.eng05_worker_bindings b
        WHERE b.consumer_id=expired.consumer_id
          AND b.tenant_id=expired.tenant_id
          AND b.worker_role='abc_eng05_worker' AND b.active
        AND EXISTS(SELECT 1 FROM abc.eng05_worker_bindings w
          WHERE w.login_name=session_user
            AND w.worker_role='abc_eng05_worker'
            AND w.consumer_id=b.consumer_id AND w.tenant_id=b.tenant_id
            AND w.active));
  SELECT job.* INTO j FROM abc.eng19_synthetic_jobs job
    JOIN abc.eng05_worker_bindings b
      ON b.consumer_id=job.consumer_id AND b.tenant_id=job.tenant_id
        AND b.worker_role='abc_eng05_worker' AND b.active
    JOIN abc.eng05_worker_bindings w
      ON w.login_name=session_user AND w.worker_role='abc_eng05_worker'
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
  -- The claim is atomic with a fresh, database-owned verification of the
  -- original ENG04 ACKed report; revocation/tampering cannot slip through.
  v_verified:=abc.eng05_ci_verify_eng04_source(j.handoff_id);
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
    'engine_id','ENG-05','engine_version','synthetic-ontology.1',
    'eng04_verified_lineage',v_verified);
END;$claim$;

CREATE OR REPLACE FUNCTION abc.eng19_ack_synthetic(
 p_handoff uuid,p_lease uuid,p_out bytea,p_next uuid
) RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,abc
AS $ack$
DECLARE j abc.eng19_synthetic_jobs%ROWTYPE;v_out jsonb;v_sha text;v_verified jsonb;
BEGIN
 IF session_user='abc_eng05_worker' OR p_lease IS NULL OR p_next IS NULL
    OR p_out IS NULL OR octet_length(p_out) NOT BETWEEN 16 AND 32768
 THEN RAISE EXCEPTION 'worker ACK context denied' USING ERRCODE='42501'; END IF;
 SELECT * INTO j FROM abc.eng19_synthetic_jobs WHERE handoff_id=p_handoff FOR UPDATE;
 IF NOT FOUND OR j.status<>'LEASED' OR j.lease_token IS DISTINCT FROM p_lease
    OR j.lease_until<=clock_timestamp()
    OR NOT EXISTS(SELECT 1 FROM abc.eng05_worker_bindings b
       WHERE b.consumer_id=j.consumer_id AND b.tenant_id=j.tenant_id
         AND b.worker_role='abc_eng05_worker' AND b.active
         AND EXISTS(SELECT 1 FROM abc.eng05_worker_bindings w
            WHERE w.login_name=session_user
              AND w.worker_role='abc_eng05_worker'
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
 -- Re-verify the immutable source, source-engine identity and ENG03
 -- ledger AFTER consent fencing, before writing any ENG05 result.
 v_verified:=abc.eng05_ci_verify_eng04_source(j.handoff_id);
 v_out:=convert_from(p_out,'UTF8')::jsonb;
 IF jsonb_typeof(v_out)<>'object'
   OR v_out->>'ontology_version'<>'synthetic-ontology.1'
   OR v_out->>'service_id'<>'synthetic:hair-color'
   OR v_out->'retrieval_sources' IS DISTINCT FROM '[]'::jsonb
   OR v_out->'grounded_facts' IS DISTINCT FROM '[]'::jsonb
   OR v_out->'unknowns' IS DISTINCT FROM '["SOURCE_UNVERIFIED"]'::jsonb
 THEN RAISE EXCEPTION 'unapproved or invented knowledge result' USING ERRCODE='42501'; END IF;
 v_sha:=encode(sha256(p_out),'hex');
 INSERT INTO abc.eng19_synthetic_results(
   handoff_id,worker_lease,consumer_id,engine_id,engine_version,
   source_sha256,output_sha256,output_bytes)
 VALUES(p_handoff,p_lease,j.consumer_id,'ENG-05','synthetic-ontology.1',
        j.source_sha256,v_sha,p_out);
 -- Durable evidence lineage commits with the result in this transaction.
 IF v_verified IS NOT NULL THEN
   INSERT INTO abc.eng05_ci_source_receipts(
     handoff_id,eng04_job_id,tenant_id,consumer_id,
     eng04_artifact_sha256,eng03_manifest_sha256,eng05_result_sha256,
     status)
   VALUES(p_handoff,(v_verified->>'eng04_job_id')::uuid,
     j.tenant_id,j.consumer_id,j.source_sha256,
     v_verified->>'eng03_manifest_sha256',v_sha,
     'BLOCKED_PENDING_AUTHORITY');
 END IF;
 INSERT INTO abc.eng19_synthetic_outbox(
   handoff_id,target_handoff_id,from_engine,to_engine,artifact_kind,artifact_sha256)
 VALUES(p_handoff,p_next,'ENG-05','ENG-06','PROFESSIONAL_KNOWLEDGE_BUNDLE',v_sha);
 UPDATE abc.eng19_synthetic_jobs SET status='ACKED',lease_token=NULL,
   lease_until=NULL,updated_at=clock_timestamp() WHERE handoff_id=p_handoff;
 RETURN 'ACKED_REVIEW_ONLY';
END;$ack$;

REVOKE ALL ON FUNCTION abc.eng19_claim_synthetic(text,integer)
 FROM PUBLIC,abc_pipeline_worker,abc_eng04_worker;
REVOKE ALL ON FUNCTION abc.eng19_ack_synthetic(uuid,uuid,bytea,uuid)
 FROM PUBLIC,abc_pipeline_worker,abc_eng04_worker;
GRANT EXECUTE ON FUNCTION abc.eng19_claim_synthetic(text,integer) TO abc_eng05_worker;
GRANT EXECUTE ON FUNCTION abc.eng19_ack_synthetic(uuid,uuid,bytea,uuid) TO abc_eng05_worker;
COMMIT;

-- 0024: authenticated ENG04 same-artifact -> ENG05 local review handoff.
-- Synthetic-only; no production dispatcher, unsigned ADR, media or release.
-- Append-only. Legacy tenant-test synthetic function is unchanged.
BEGIN;
CREATE FUNCTION abc.eng19_submit_verified_eng04(
  p_handoff uuid,p_tenant text,p_branch text,p_session uuid,p_version integer,
  p_correlation uuid,p_artifact_sha text,p_message_sha text,p_source bytea,
  p_consumer text
) RETURNS text LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,abc
AS $submit$
DECLARE v_src jsonb;v_job abc.eng04_ci_jobs%ROWTYPE;
  v_result abc.eng04_ci_results%ROWTYPE;
  v_existing abc.eng19_synthetic_jobs%ROWTYPE;
  v_receipt text;v_count integer;v_source_hash text;
BEGIN
 IF p_source IS NULL OR octet_length(p_source) NOT BETWEEN 32 AND 32768
   OR p_artifact_sha !~ '^[a-f0-9]{64}$'
   OR p_message_sha !~ '^[a-f0-9]{64}$'
   OR p_consumer IS NULL OR length(p_consumer) NOT BETWEEN 3 AND 64
   OR p_handoff IS NULL OR p_correlation IS NULL OR p_session IS NULL
   OR p_version IS NULL OR p_version<0
   OR encode(sha256(p_source),'hex') IS DISTINCT FROM p_artifact_sha
 THEN RAISE EXCEPTION 'ENG04 source bytes invalid' USING ERRCODE='42501';END IF;
 v_src:=convert_from(p_source,'UTF8')::jsonb;
 IF jsonb_typeof(v_src) IS DISTINCT FROM 'object'
   OR v_src->>'engine_version' IS DISTINCT FROM 'eng04.synthetic-evidence.1'
   OR v_src->>'service_scope' IS DISTINCT FROM 'SYNTHETIC_NON_MEDIA_ONLY'
   OR v_src->>'source_engine' IS DISTINCT FROM 'ENG-03'
   OR v_src->>'service_id' IS DISTINCT FROM 'synthetic:hair-color'
   OR v_src->>'session_id' IS DISTINCT FROM p_session::text
   OR v_src->>'professional_validation_verified' IS DISTINCT FROM 'false'
   OR v_src->>'source_manifest_sha256' !~ '^[a-f0-9]{64}$'
   OR jsonb_typeof(v_src->'evidence_ids') IS DISTINCT FROM 'array'
   OR jsonb_array_length(v_src->'evidence_ids') IS DISTINCT FROM 4
 THEN RAISE EXCEPTION 'ENG04 source contract invalid' USING ERRCODE='42501';END IF;
 -- Only an actual completed, independently identified ENG04 job may supply
 -- bytes. An asserted hash/message, even with a valid JWT, is never enough.
 SELECT j.* INTO v_job FROM abc.eng04_ci_jobs j
 JOIN abc.eng04_ci_results r ON r.job_id=j.job_id
 JOIN abc.eng04_ci_worker_bindings b ON b.consumer_id=j.consumer_id
   AND b.tenant_id=j.tenant_id AND b.active
   AND b.login_name='abc_eng04_ci_login'
 WHERE j.tenant_id=p_tenant AND j.branch_id=p_branch
   AND j.session_id=p_session AND j.state_version=p_version
   AND j.consumer_id=p_consumer AND j.status='ACKED'
   AND r.status='BLOCKED_PENDING_AUTHORITY'
   AND r.engine_id='ENG-04'
   AND r.artifact_kind='BEAUTY_ANALYSIS_REPORT'
   AND r.engine_version='eng04.synthetic-evidence.1'
   AND r.output_sha256=p_artifact_sha AND r.output_bytes=p_source
   AND r.source_manifest_sha256=v_src->>'source_manifest_sha256'
 LIMIT 1 FOR SHARE OF j,r,b;
 IF NOT FOUND THEN
   RAISE EXCEPTION 'ENG04 durable source or binding missing' USING ERRCODE='42501';
 END IF;
 SELECT * INTO v_result FROM abc.eng04_ci_results
   WHERE job_id=v_job.job_id;
 -- Defense-in-depth: the same four verified immutable ENG03 evidence IDs
 -- must still match this exact job's source-manifest before submission.
 SELECT count(*),encode(sha256(convert_to(string_agg(
   e.evidence_id::text||':'||trim(e.evidence_digest),'|'
   ORDER BY e.evidence_id),'UTF8')),'hex')
 INTO v_count,v_source_hash
 FROM abc.eng03_evidence_ledger e
 JOIN abc.eng03_input_jobs src ON src.job_id=e.source_job_id
   AND src.consumer_id=e.consumer_id AND src.status='ACKED'
 WHERE e.consumer_id=v_job.consumer_id AND e.tenant_id=v_job.tenant_id
   AND e.branch_id=v_job.branch_id AND e.session_id=v_job.session_id
   AND e.aggregate_version<=v_job.state_version;
 IF v_count IS DISTINCT FROM 4
    OR v_source_hash IS DISTINCT FROM v_result.source_manifest_sha256 THEN
   RAISE EXCEPTION 'ENG04 source provenance changed' USING ERRCODE='42501';
 END IF;
 -- This DB-owned receipt revalidates current session CAS and active
 -- AI_PROCESSING+INTERNAL_HANDOFF consent under row share locks, plus
 -- the verified local workload claim established by the receiver.
 v_receipt:=abc.eng19_record_review_handoff(
   p_handoff,p_tenant,p_branch,p_session,p_version,p_correlation,
   'ENG-04','ENG-05','BEAUTY_ANALYSIS_REPORT',p_message_sha);
 INSERT INTO abc.eng19_synthetic_jobs(
   handoff_id,tenant_id,branch_id,session_id,state_version,
   consumer_id,source_bytes,source_sha256
 ) VALUES(p_handoff,p_tenant,p_branch,p_session,p_version,
   p_consumer,p_source,p_artifact_sha)
 ON CONFLICT(handoff_id) DO NOTHING;
 SELECT * INTO v_existing FROM abc.eng19_synthetic_jobs
    WHERE handoff_id=p_handoff;
 IF NOT FOUND OR v_existing.source_sha256 IS DISTINCT FROM p_artifact_sha
   OR v_existing.source_bytes IS DISTINCT FROM p_source
   OR (v_existing.tenant_id,v_existing.branch_id,v_existing.session_id,
       v_existing.state_version,v_existing.consumer_id)
      IS DISTINCT FROM (p_tenant,p_branch,p_session,p_version,p_consumer)
 THEN RAISE EXCEPTION 'ENG05 source receipt content conflict'
      USING ERRCODE='23505';END IF;
 RETURN v_receipt;
END;$submit$;
REVOKE ALL ON FUNCTION abc.eng19_submit_verified_eng04(
 uuid,text,text,uuid,integer,uuid,text,text,bytea,text)
 FROM PUBLIC,abc_worker,abc_answer_worker,abc_orchestrator,
      abc_eng03_worker,abc_pipeline_worker,abc_eng04_worker,abc_eng05_worker;
GRANT EXECUTE ON FUNCTION abc.eng19_submit_verified_eng04(
 uuid,text,text,uuid,integer,uuid,text,text,bytea,text) TO abc_app;
COMMIT;

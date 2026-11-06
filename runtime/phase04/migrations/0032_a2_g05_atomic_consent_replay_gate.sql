-- 0032 / A2-G05: synthetic-only authenticated ENGINE v2 admission gate.
-- Adds a transaction-scoped, owner-controlled PG authorization + JTI claim.
-- No existing migration/contract altered. No human credential is issued.
-- In production, managed tenants still require physical PG clientcert identity,
-- independent human/workload attestation and signed operational approval.
BEGIN;

CREATE FUNCTION abc.eng14_g05_admit_and_claim(
  p_tenant text, p_branch text, p_session uuid, p_state_version integer,
  p_caller text, p_target text, p_consumer text,
  p_human_issuer text, p_human_subject text,
  p_workload_issuer text, p_audience text,
  p_jti uuid, p_expires_at timestamptz
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,abc
AS $gate$
DECLARE
  v_session uuid;
BEGIN
  -- This is deliberately NOT a general-purpose service authorization API.
  -- Only a synthetic local draft flow can execute. Human identity is injected
  -- by the trusted integration caller, never from a client request body.
  IF p_target NOT IN ('ENG-04','ENG-05','ENG-06')
    OR (p_caller,p_target) NOT IN (
       ('ENG-03','ENG-04'),('ENG-04','ENG-05'),('ENG-05','ENG-06'))
    OR nullif(p_consumer,'') IS NULL OR length(p_consumer) NOT BETWEEN 3 AND 96
    OR p_state_version IS NULL OR p_state_version<0
    OR p_human_issuer NOT LIKE 'https://%'
    OR nullif(p_human_subject,'') IS NULL
    OR p_audience IS DISTINCT FROM 'abc-engine:'||p_target
    OR current_setting('abc.tenant',true) IS DISTINCT FROM p_tenant
    OR current_setting('abc.branch',true) IS DISTINCT FROM p_branch
    OR current_setting('abc.issuer',true) IS DISTINCT FROM p_human_issuer
    OR current_setting('abc.subject',true) IS DISTINCT FROM p_human_subject
    OR NOT abc.eng14_workload_allowed(p_tenant)
  THEN
    RAISE EXCEPTION 'A2-G05 untrusted principal, route or context'
       USING ERRCODE='42501';
  END IF;

  -- FOR SHARE protects the exact membership, session and consent rows until
  -- the caller's transaction completes, including the bounded execution.
  -- No caller-controlled AI output can authorize the session.
  SELECT s.session_id INTO v_session
    FROM abc.sessions s
    JOIN abc.memberships m
      ON m.issuer=p_human_issuer AND m.subject=s.specialist_id
     AND m.tenant_id=s.tenant_id AND m.branch_id=s.branch_id
     AND m.role='SPECIALIST' AND m.active AND m.verified_qualification
    JOIN abc.consent_evidence c
      ON c.session_id=s.session_id AND c.tenant_id=s.tenant_id
     AND c.branch_id=s.branch_id AND c.client_id=s.client_id
     AND c.status='ACTIVE' AND c.revoked_at IS NULL
     AND c.verified_at IS NOT NULL AND c.valid_until>clock_timestamp()
     AND c.purpose @> ARRAY['AI_STUDIO_SYNTHETIC_PREVIEW']::text[]
    WHERE s.session_id=p_session AND s.tenant_id=p_tenant
      AND s.branch_id=p_branch AND s.specialist_id=p_human_subject
      AND s.state_version=p_state_version AND s.state='CREATED'
      AND s.service_id='synthetic:hair-color'
    FOR SHARE OF s,m,c;
  IF NOT FOUND OR v_session IS NULL THEN
    RAISE EXCEPTION 'A2-G05 current consent, qualification or session denied'
       USING ERRCODE='42501';
  END IF;

  IF NOT abc.eng14_claim_v2_jti(
       p_tenant,p_workload_issuer,p_audience,p_jti,p_expires_at) THEN
    RAISE EXCEPTION 'A2-G05 distributed JWT replay'
       USING ERRCODE='42501';
  END IF;
  RETURN true;
END;
$gate$;

REVOKE ALL ON FUNCTION abc.eng14_g05_admit_and_claim(
  text,text,uuid,integer,text,text,text,text,text,text,text,uuid,timestamptz)
  FROM PUBLIC;
GRANT EXECUTE ON FUNCTION abc.eng14_g05_admit_and_claim(
  text,text,uuid,integer,text,text,text,text,text,text,text,uuid,timestamptz)
  TO abc_app;

-- The external staging migrator, when present, is a reviewed administrative
-- owner and needs explicit FORCE-RLS access to read consent evidence.
DO $policy$ BEGIN
  IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='abc_staging_migrator') THEN
    CREATE POLICY abc_migrator_g05_consent_read
      ON abc.consent_evidence FOR SELECT TO abc_staging_migrator
      USING(true);
  END IF;
END $policy$;

COMMENT ON FUNCTION abc.eng14_g05_admit_and_claim(
  text,text,uuid,integer,text,text,text,text,text,text,text,uuid,timestamptz)
IS 'A2 G05 synthetic local v2 only; never operational or professional authorization';
COMMIT;

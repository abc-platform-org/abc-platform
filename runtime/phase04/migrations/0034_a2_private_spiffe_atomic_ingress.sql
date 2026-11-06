-- 0034: local-only PostgreSQL atomic private ingress/ENG14 authorization + shared JTI.
-- Versioned independent ENG03->04->05->06 synthetic review path. NEVER hosted
-- staging or production; real provider-issued PKI and physical PG clientcert
-- remain mandatory before any deployment. Existing migrations unchanged.
BEGIN;

DO $roles$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='abc_private_ingress_exec') THEN
    CREATE ROLE abc_private_ingress_exec NOLOGIN NOINHERIT NOSUPERUSER
      NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
  END IF;
END $roles$;
GRANT USAGE ON SCHEMA abc TO abc_private_ingress_exec;

CREATE TABLE abc.a2_private_synthetic_bindings (
  tenant_id text NOT NULL REFERENCES abc.tenants(tenant_id),
  branch_id text NOT NULL,
  login_name name NOT NULL,
  caller_engine text NOT NULL,
  target_engine text NOT NULL,
  consumer_id text NOT NULL CHECK(length(consumer_id) BETWEEN 3 AND 96),
  spiffe_id text NOT NULL,
  certificate_sha256 text NOT NULL CHECK(certificate_sha256 ~ '^[a-f0-9]{64}$'),
  human_issuer text NOT NULL,
  specialist_subject text NOT NULL,
  active boolean NOT NULL DEFAULT false,
  valid_until timestamptz NOT NULL,
  revoked_at timestamptz,
  PRIMARY KEY (tenant_id,branch_id,login_name,caller_engine,target_engine,consumer_id,certificate_sha256),
  CONSTRAINT a2_canonical_route CHECK ((caller_engine,target_engine) IN (
      ('ENG-03','ENG-04'),('ENG-04','ENG-05'),('ENG-05','ENG-06'))),
  CONSTRAINT a2_canonical_spiffe CHECK (
      spiffe_id = 'spiffe://abc.internal/staging/' || lower(caller_engine))
);
ALTER TABLE abc.a2_private_synthetic_bindings ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.a2_private_synthetic_bindings FORCE ROW LEVEL SECURITY;
REVOKE ALL ON abc.a2_private_synthetic_bindings FROM PUBLIC;
-- Only an independently controlled migration/operator identity may insert or
-- revoke a binding. Runtime obtains NO table privilege, even SELECT.
DO $owner$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='abc_staging_migrator') THEN
    CREATE POLICY a2_private_operator_binding
      ON abc.a2_private_synthetic_bindings FOR ALL TO abc_staging_migrator
      USING (true) WITH CHECK (true);
  END IF;
END $owner$;

CREATE TABLE abc.a2_private_synthetic_audit (
  replay_digest text PRIMARY KEY REFERENCES abc.eng14_v2_replay_ledger(replay_digest),
  tenant_id text NOT NULL,
  branch_id text NOT NULL,
  session_id uuid NOT NULL,
  state_version integer NOT NULL,
  physical_login name NOT NULL,
  caller_engine text NOT NULL,
  target_engine text NOT NULL,
  consumer_id text NOT NULL,
  request_id uuid NOT NULL,
  message_sha256 text NOT NULL CHECK(message_sha256 ~ '^[a-f0-9]{64}$'),
  recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
ALTER TABLE abc.a2_private_synthetic_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.a2_private_synthetic_audit FORCE ROW LEVEL SECURITY;
REVOKE ALL ON abc.a2_private_synthetic_audit FROM PUBLIC;
DO $owner$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='abc_staging_migrator') THEN
    CREATE POLICY a2_private_operator_audit
      ON abc.a2_private_synthetic_audit FOR SELECT TO abc_staging_migrator
      USING (true);
  END IF;
END $owner$;

CREATE FUNCTION abc.a2_private_atomic_admit(
  p_tenant text,p_branch text,p_session uuid,p_version integer,
  p_caller text,p_target text,p_consumer text,p_spiffe_id text,
  p_cert_sha256 text,p_human_issuer text,p_human_subject text,
  p_workload_issuer text,p_audience text,p_jti uuid,
  p_expires_at timestamptz,p_request uuid,p_message_sha256 text
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,abc
AS $gate$
DECLARE
  v_digest text;
  v_inserted boolean;
  v_now timestamptz := clock_timestamp();
BEGIN
  -- The physical SQL login (session_user) must exist in the operator-owned
  -- binding. A caller-controlled GUC, body, or SET ROLE is never sufficient.
  IF p_tenant IS NULL OR p_branch IS NULL
    OR nullif(p_consumer,'') IS NULL OR length(p_consumer) NOT BETWEEN 3 AND 96
    OR p_session IS NULL OR p_version IS NULL OR p_version<0
    OR p_request IS NULL OR p_jti IS NULL
    OR substr(p_jti::text,15,1)<>'4'
    OR p_expires_at IS NULL OR p_expires_at<=v_now
    OR p_expires_at>v_now+interval '120 seconds'
    OR p_workload_issuer NOT LIKE 'https://%'
    OR p_human_issuer NOT LIKE 'https://%'
    OR nullif(p_human_subject,'') IS NULL
    OR p_audience IS DISTINCT FROM 'abc-engine:'||p_target
    OR (p_caller,p_target) NOT IN (
      ('ENG-03','ENG-04'),('ENG-04','ENG-05'),('ENG-05','ENG-06'))
    OR p_spiffe_id IS DISTINCT FROM 'spiffe://abc.internal/staging/'||lower(p_caller)
    OR p_cert_sha256 IS NULL OR p_cert_sha256 !~ '^[a-f0-9]{64}$'
    OR p_message_sha256 IS NULL OR p_message_sha256 !~ '^[a-f0-9]{64}$'
    OR current_setting('abc.tenant',true) IS DISTINCT FROM p_tenant
    OR current_setting('abc.branch',true) IS DISTINCT FROM p_branch
    OR current_setting('abc.issuer',true) IS DISTINCT FROM p_human_issuer
    OR current_setting('abc.subject',true) IS DISTINCT FROM p_human_subject
    OR COALESCE((SELECT mode.managed_required
         FROM abc.eng14_tenant_workload_mode mode WHERE mode.tenant_id=p_tenant),
         false) IS TRUE
  THEN
    RAISE EXCEPTION 'A2 atomic ingress rejected: identity or managed scope'
      USING ERRCODE='42501';
  END IF;

  -- FOR SHARE guards against operator revocation during bounded execution.
  PERFORM 1 FROM abc.a2_private_synthetic_bindings binding
    WHERE binding.login_name=session_user
      AND binding.tenant_id=p_tenant AND binding.branch_id=p_branch
      AND binding.caller_engine=p_caller AND binding.target_engine=p_target
      AND binding.consumer_id=p_consumer AND binding.spiffe_id=p_spiffe_id
      AND binding.certificate_sha256=p_cert_sha256
      AND binding.human_issuer=p_human_issuer
      AND binding.specialist_subject=p_human_subject
      AND binding.active AND binding.revoked_at IS NULL
      AND binding.valid_until>v_now
    FOR SHARE OF binding;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'A2 atomic ingress rejected: physical binding'
      USING ERRCODE='42501';
  END IF;

  -- The ENG14 membership+consent+session decision and replay admission occur
  -- in one DB transaction; locks remain held until the engine response is
  -- checked and the caller commits, or all changes roll back on failure.
  PERFORM 1 FROM abc.sessions s
    JOIN abc.memberships m
      ON m.tenant_id=s.tenant_id AND m.branch_id=s.branch_id
     AND m.subject=s.specialist_id AND m.issuer=p_human_issuer
     AND m.role='SPECIALIST' AND m.active AND m.verified_qualification
    JOIN abc.consent_evidence consent
      ON consent.tenant_id=s.tenant_id AND consent.branch_id=s.branch_id
     AND consent.session_id=s.session_id AND consent.client_id=s.client_id
     AND consent.status='ACTIVE' AND consent.revoked_at IS NULL
     AND consent.verified_at IS NOT NULL AND consent.valid_until>v_now
     AND consent.purpose @> ARRAY['AI_STUDIO_SYNTHETIC_PREVIEW']::text[]
    WHERE s.tenant_id=p_tenant AND s.branch_id=p_branch
      AND s.session_id=p_session AND s.state_version=p_version
      AND s.state='CREATED' AND s.specialist_id=p_human_subject
      AND s.service_id='synthetic:hair-color'
    FOR SHARE OF s,m,consent;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'A2 atomic ingress rejected: ENG14 consent state qualification'
      USING ERRCODE='42501';
  END IF;

  -- Shared existing ENG14 replay ledger ensures atomic one-shot JTI across
  -- independent processes *and* the prior v2 admission protocol.
  v_digest:=encode(sha256(convert_to(p_workload_issuer||chr(31)||
             p_audience||chr(31)||p_jti::text,'UTF8')),'hex');
  INSERT INTO abc.eng14_v2_replay_ledger(
    replay_digest,tenant_id,issuer,audience,issued_jti,expires_at)
  VALUES(v_digest,p_tenant,p_workload_issuer,p_audience,p_jti,p_expires_at)
  ON CONFLICT (replay_digest) DO NOTHING RETURNING true INTO v_inserted;
  IF NOT COALESCE(v_inserted,false) THEN
    RAISE EXCEPTION 'A2 atomic ingress rejected: global replay'
      USING ERRCODE='42501';
  END IF;
  INSERT INTO abc.a2_private_synthetic_audit(
    replay_digest,tenant_id,branch_id,session_id,state_version,physical_login,
    caller_engine,target_engine,consumer_id,request_id,message_sha256)
  VALUES(v_digest,p_tenant,p_branch,p_session,p_version,session_user,
         p_caller,p_target,p_consumer,p_request,p_message_sha256);
  RETURN true;
END;
$gate$;

REVOKE ALL ON FUNCTION abc.a2_private_atomic_admit(
  text,text,uuid,integer,text,text,text,text,text,text,text,
  text,text,uuid,timestamptz,uuid,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION abc.a2_private_atomic_admit(
  text,text,uuid,integer,text,text,text,text,text,text,text,
  text,text,uuid,timestamptz,uuid,text) TO abc_private_ingress_exec;
COMMENT ON FUNCTION abc.a2_private_atomic_admit(
  text,text,uuid,integer,text,text,text,text,text,text,text,
  text,text,uuid,timestamptz,uuid,text)
IS 'A2 local CI synthetic preview only; no external provider or professional release authority';
COMMIT;

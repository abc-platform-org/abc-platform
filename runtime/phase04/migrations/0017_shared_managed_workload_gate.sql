-- 0017: Shared physical-login authorization for ENG01 create and ENG14 pause.
-- In particular, a verified OIDC GUC cannot override a tenant's managed mode.
-- Staging remains synthetic until independently issued client PKI is enrolled.
BEGIN;
CREATE TABLE abc.eng14_tenant_workload_mode (
  tenant_id text PRIMARY KEY REFERENCES abc.tenants(tenant_id),
  managed_required boolean NOT NULL DEFAULT false,
  activated_at timestamptz,
  activated_by text,
  CHECK (NOT managed_required OR (activated_at IS NOT NULL AND nullif(activated_by,'') IS NOT NULL))
);
ALTER TABLE abc.eng14_tenant_workload_mode ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.eng14_tenant_workload_mode FORCE ROW LEVEL SECURITY;
REVOKE ALL ON abc.eng14_tenant_workload_mode FROM PUBLIC,abc_app,
 abc_worker,abc_answer_worker,abc_orchestrator,abc_eng03_worker,abc_pipeline_worker;
ALTER TABLE abc.eng01_api_login_bindings
  ADD COLUMN certificate_client_dn text,
  ADD COLUMN certificate_issuer_dn text,
  ADD COLUMN certificate_serial text;
-- No app, engine, or model obtains a binding/mode write grant.
CREATE FUNCTION abc.eng14_workload_allowed(p_tenant text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,abc
AS $workload$
DECLARE
  v_managed boolean;
  v_login name:=session_user;
  v_ssl record;
  v_binding record;
BEGIN
  IF p_tenant IS NULL OR p_tenant='' OR
     current_setting('abc.tenant',true) IS DISTINCT FROM p_tenant THEN
    RETURN false;
  END IF;
  SELECT managed_required INTO v_managed
    FROM abc.eng14_tenant_workload_mode WHERE tenant_id=p_tenant;
  v_managed:=COALESCE(v_managed,false);
  -- Dedicated managed login may SET ROLE abc_app; session_user stays physical.
  IF v_login='abc_app' THEN
    RETURN NOT v_managed;
  END IF;
  SELECT consumer_id,certificate_client_dn,certificate_issuer_dn,certificate_serial
    INTO v_binding FROM abc.eng01_api_login_bindings
    WHERE login_name=v_login AND tenant_id=p_tenant
      AND engine_id='ENG-01' AND active AND approved_at IS NOT NULL;
  IF NOT FOUND THEN RETURN false; END IF;
  IF NOT v_managed THEN RETURN true; END IF;
  -- These are server-derived, not spoofable custom SET GUC properties.
  -- PostgreSQL pg_hba MUST independently verify client cert chain/CN.
  SELECT ssl,version,client_dn,issuer_dn,client_serial
    INTO v_ssl FROM pg_catalog.pg_stat_ssl
    WHERE pid=pg_backend_pid();
  RETURN COALESCE(v_ssl.ssl,false)
    AND v_ssl.version='TLSv1.3'
    AND nullif(v_ssl.client_dn,'') IS NOT NULL
    AND nullif(v_ssl.issuer_dn,'') IS NOT NULL
    AND nullif(v_ssl.client_serial,'') IS NOT NULL
    AND nullif(v_binding.certificate_client_dn,'') IS NOT NULL
    AND nullif(v_binding.certificate_issuer_dn,'') IS NOT NULL
    AND nullif(v_binding.certificate_serial,'') IS NOT NULL
    AND v_ssl.client_dn=v_binding.certificate_client_dn
    AND v_ssl.issuer_dn=v_binding.certificate_issuer_dn
    AND v_ssl.client_serial=v_binding.certificate_serial;
END;
$workload$;
REVOKE ALL ON FUNCTION abc.eng14_workload_allowed(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION abc.eng14_workload_allowed(text) TO abc_app;

-- Replace all three extant authorities using a single source of truth.
CREATE OR REPLACE FUNCTION abc.eng14_state_transition_gate() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,abc
AS $gate$
BEGIN
  IF NEW.state IS NOT DISTINCT FROM OLD.state THEN
     RETURN NEW;
  END IF;
  -- No client or model can send a proof string to bypass the gate.
  -- The only authorized state mutation is the narrow,
  -- non-treatment CREATED->PAUSED checkpoint.
  IF NOT abc.eng14_workload_allowed(OLD.tenant_id)
     OR OLD.state<>'CREATED' OR NEW.state<>'PAUSED'
     OR NEW.checkpoint IS DISTINCT FROM 'CREATED'
     OR NEW.state_version<>OLD.state_version+1
     OR NEW.session_id<>OLD.session_id
     OR (NEW.tenant_id,NEW.branch_id,NEW.specialist_id,NEW.service_id)
        IS DISTINCT FROM
        (OLD.tenant_id,OLD.branch_id,OLD.specialist_id,OLD.service_id)
     OR current_setting('abc.issuer',true) NOT LIKE 'https://%'
     OR current_setting('abc.subject',true) IS DISTINCT FROM OLD.specialist_id
     OR current_setting('abc.tenant',true) IS DISTINCT FROM OLD.tenant_id
     OR current_setting('abc.branch',true) IS DISTINCT FROM OLD.branch_id
     OR NOT EXISTS (SELECT 1 FROM abc.memberships member
        WHERE member.issuer=current_setting('abc.issuer',true)
          AND member.subject=OLD.specialist_id
          AND member.tenant_id=OLD.tenant_id AND member.branch_id=OLD.branch_id
          AND member.role='SPECIALIST' AND member.active FOR SHARE)
  THEN
     RAISE EXCEPTION 'ENG14 transition forbidden or unverifiable'
       USING ERRCODE='23514';
  END IF;
  INSERT INTO abc.eng14_state_guard_audit(
    session_id,tenant_id,branch_id,source_state,target_state,
    from_version,to_version,result,actor_id,guard_version)
  VALUES(NEW.session_id,NEW.tenant_id,NEW.branch_id,OLD.state,
    NEW.state,OLD.state_version,NEW.state_version,
    'ALLOW_SYNTHETIC_PAUSE_S0',OLD.specialist_id,'eng14.state.synthetic.1');
  RETURN NEW;
END;
$gate$;
CREATE OR REPLACE FUNCTION abc.eng14_apply_pause(p_session uuid,p_expected_version integer)
RETURNS SETOF abc.sessions
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,abc
AS $apply$
BEGIN
  IF NOT abc.eng14_workload_allowed(current_setting('abc.tenant',true)) OR p_expected_version<0
    OR current_setting('abc.issuer',true) NOT LIKE 'https://%'
    OR current_setting('abc.subject',true) IS NULL
    OR current_setting('abc.tenant',true) IS NULL
    OR current_setting('abc.branch',true) IS NULL
    OR NOT EXISTS(
        SELECT 1 FROM abc.sessions s
          JOIN abc.memberships m
            ON m.issuer=current_setting('abc.issuer',true)
           AND m.subject=s.specialist_id AND m.role='SPECIALIST'
           AND m.tenant_id=s.tenant_id AND m.branch_id=s.branch_id
           AND m.active
        WHERE s.session_id=p_session AND s.state='CREATED'
          AND s.state_version=p_expected_version
          AND s.specialist_id=current_setting('abc.subject',true)
          AND s.tenant_id=current_setting('abc.tenant',true)
          AND s.branch_id=current_setting('abc.branch',true)
        FOR SHARE OF m)
  THEN
    RAISE EXCEPTION 'ENG14 state transition broker denied'
      USING ERRCODE='23514';
  END IF;
  RETURN QUERY UPDATE abc.sessions s
    SET state='PAUSED',checkpoint='CREATED',
        state_version=s.state_version+1,updated_at=clock_timestamp()
    WHERE s.session_id=p_session AND s.state='CREATED'
      AND s.state_version=p_expected_version
      AND s.tenant_id=current_setting('abc.tenant',true)
      AND s.branch_id=current_setting('abc.branch',true)
      AND s.specialist_id=current_setting('abc.subject',true)
    RETURNING s.*;
END;
$apply$;
CREATE OR REPLACE FUNCTION abc.eng01_create_session(p_body jsonb,p_key text)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,abc
AS $broker$
DECLARE
  v_issuer text := current_setting('abc.issuer',true);
  v_actor text := current_setting('abc.subject',true);
  v_tenant text := current_setting('abc.tenant',true);
  v_branch text := current_setting('abc.branch',true);
  v_digest text;
  v_old record;
  v_sid uuid;
  v_eid uuid;
  v_trace uuid;
  v_now timestamptz;
  v_stamp text;
  v_response jsonb;
  v_event jsonb;
  v_field text;
BEGIN
  IF NOT abc.eng14_workload_allowed(v_tenant)
     OR v_issuer NOT LIKE 'https://%'
     OR nullif(v_actor,'') IS NULL OR nullif(v_tenant,'') IS NULL
     OR nullif(v_branch,'') IS NULL
     OR p_key IS NULL OR length(p_key) NOT BETWEEN 8 AND 128
     OR p_key !~ '^[A-Za-z0-9_.-]+$'
     OR p_body IS NULL OR jsonb_typeof(p_body)<>'object'
     OR p_body->>'scope' IS DISTINCT FROM 'IN_SALON_SHARED_SCREEN'
     OR p_body->>'branch_id' IS DISTINCT FROM v_branch
     OR EXISTS(SELECT 1 FROM jsonb_object_keys(p_body) AS k
         WHERE k NOT IN ('branch_id','scope','client_id','appointment_id','service_id'))
  THEN
    RAISE EXCEPTION 'ENG01 create broker denied scope/body/identity'
      USING ERRCODE='23514';
  END IF;
  FOREACH v_field IN ARRAY ARRAY['branch_id','scope','client_id','appointment_id','service_id'] LOOP
    IF p_body ? v_field AND
       (jsonb_typeof(p_body->v_field)<>'string'
       OR btrim(p_body->>v_field)='')
    THEN
      RAISE EXCEPTION 'ENG01 create broker invalid field'
        USING ERRCODE='23514';
    END IF;
  END LOOP;
  IF NOT EXISTS(
    SELECT 1 FROM abc.memberships m
     WHERE m.issuer=v_issuer AND m.subject=v_actor
       AND m.tenant_id=v_tenant AND m.branch_id=v_branch
       AND m.role='SPECIALIST' AND m.active
     FOR SHARE
  ) THEN
    RAISE EXCEPTION 'ENG01 create broker membership revoked'
      USING ERRCODE='23514';
  END IF;

  -- Digest is computed inside the database from canonical jsonb, not from a
  -- client-supplied header. Per-actor intent lock closes same-key races.
  v_digest:=encode(sha256(convert_to(p_body::text,'UTF8')),'hex');
  PERFORM pg_advisory_xact_lock(hashtextextended(
      v_tenant||'|'||v_actor||'|create|'||p_key,0));
  SELECT fingerprint,response_json INTO v_old
    FROM abc.idempotency
    WHERE tenant_id=v_tenant AND actor_id=v_actor
      AND operation='create' AND request_key=p_key;
  IF FOUND THEN
    IF v_old.fingerprint<>v_digest THEN
      RAISE EXCEPTION 'ENG01 create idempotency payload conflict'
        USING ERRCODE='23505';
    END IF;
    RETURN v_old.response_json;
  END IF;

  v_sid:=gen_random_uuid();v_eid:=gen_random_uuid();v_trace:=gen_random_uuid();
  v_now:=clock_timestamp();
  v_stamp:=to_char(v_now AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.MS"Z"');
  INSERT INTO abc.sessions(session_id,tenant_id,branch_id,specialist_id,
        client_id,appointment_id,service_id,state,state_version,
        checkpoint,created_at,updated_at,last_event_id)
   VALUES(v_sid,v_tenant,v_branch,v_actor,p_body->>'client_id',
       p_body->>'appointment_id',p_body->>'service_id','CREATED',0,
       NULL,v_now,v_now,v_eid);

  v_response:=jsonb_strip_nulls(jsonb_build_object(
    'session_id',v_sid::text,'tenant_id',v_tenant,'branch_id',v_branch,
    'specialist_id',v_actor,'client_id',p_body->>'client_id',
    'appointment_id',p_body->>'appointment_id','service_id',p_body->>'service_id',
    'state','CREATED','state_version',0,'created_at',v_stamp,
    'updated_at',v_stamp,'last_event_id',v_eid::text,
    'scope','IN_SALON_SHARED_SCREEN'));
  v_event:=jsonb_build_object(
    'event_id',v_eid::text,'event_type','SESSION_CREATED',
    'event_schema_version','1.0.0-draft','tenant_id',v_tenant,
    'branch_id',v_branch,'session_id',v_sid::text,
    'aggregate_id',v_sid::text,'aggregate_version',0,
    'occurred_at',v_stamp,'correlation_id',v_sid::text,
    'actor',jsonb_build_object('user_id',v_actor,'role','SPECIALIST'),
    'payload',jsonb_build_object('session_id',v_sid::text,'branch_id',v_branch),
    'producer_engine_id','ENG-01','trace_id',v_trace::text);
  INSERT INTO abc.outbox(event_id,tenant_id,aggregate_id,aggregate_version,event_json,created_at)
    VALUES(v_eid,v_tenant,v_sid,0,v_event,v_now);
  INSERT INTO abc.idempotency(tenant_id,actor_id,operation,request_key,fingerprint,response_json)
    VALUES(v_tenant,v_actor,'create',p_key,v_digest,v_response);
  INSERT INTO abc.eng01_create_audit(session_id,tenant_id,branch_id,actor_id,event_id,request_key)
    VALUES(v_sid,v_tenant,v_branch,v_actor,v_eid,p_key);
  RETURN v_response;
END;
$broker$;

-- No change to frozen product contract / canonical transition graph.
-- Operator owns the managed-required toggle; runtime has no update policy.
DO $owner$ BEGIN
 IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='abc_staging_migrator') THEN
   CREATE POLICY abc_migrator_workload_mode ON abc.eng14_tenant_workload_mode
     FOR ALL TO abc_staging_migrator USING(true) WITH CHECK(true);
 END IF;
END $owner$;
COMMIT;

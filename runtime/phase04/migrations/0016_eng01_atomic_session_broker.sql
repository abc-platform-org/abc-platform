-- 0016: ENG01 transactional SESSION_CREATED creation broker.
-- Existing migration checksums and public product contracts remain immutable.
BEGIN;
CREATE TABLE abc.eng01_create_audit (
  session_id uuid PRIMARY KEY REFERENCES abc.sessions(session_id),
  tenant_id text NOT NULL,
  branch_id text NOT NULL,
  actor_id text NOT NULL,
  event_id uuid NOT NULL UNIQUE REFERENCES abc.outbox(event_id),
  request_key text NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE(tenant_id,actor_id,request_key)
);
ALTER TABLE abc.eng01_create_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.eng01_create_audit FORCE ROW LEVEL SECURITY;
REVOKE ALL ON abc.eng01_create_audit FROM PUBLIC,abc_app,abc_worker,abc_orchestrator,
  abc_answer_worker,abc_eng03_worker,abc_pipeline_worker;

-- Operator-controlled physical PostgreSQL-login binding. Custom GUCs do not
-- identify an authenticated workload; session_user cannot be spoofed by SET.
-- Each managed API service must authenticate under a dedicated LOGIN/NOINHERIT
-- role and then SET ROLE abc_app before using the restricted broker.
CREATE TABLE abc.eng01_api_login_bindings(
  login_name name NOT NULL,
  tenant_id text NOT NULL REFERENCES abc.tenants(tenant_id),
  consumer_id text NOT NULL CHECK(length(consumer_id) BETWEEN 3 AND 96),
  engine_id text NOT NULL CHECK(engine_id='ENG-01'),
  active boolean NOT NULL DEFAULT false,
  approved_at timestamptz,
  PRIMARY KEY(login_name,tenant_id),
  CHECK(active=false OR approved_at IS NOT NULL)
);
ALTER TABLE abc.eng01_api_login_bindings ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.eng01_api_login_bindings FORCE ROW LEVEL SECURITY;
REVOKE ALL ON abc.eng01_api_login_bindings FROM PUBLIC,abc_app,abc_worker,
  abc_orchestrator,abc_answer_worker,abc_eng03_worker,abc_pipeline_worker;

CREATE FUNCTION abc.eng01_create_session(p_body jsonb,p_key text)
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
  IF (session_user <> 'abc_app' AND NOT EXISTS (
        SELECT 1 FROM abc.eng01_api_login_bindings binding
         WHERE binding.login_name=session_user
           AND binding.tenant_id=v_tenant
           AND binding.engine_id='ENG-01'
           AND binding.active AND binding.approved_at IS NOT NULL))
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
REVOKE ALL ON FUNCTION abc.eng01_create_session(jsonb,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION abc.eng01_create_session(jsonb,text) TO abc_app;

-- Direct session INSERT and raw outbox INSERT can no longer bypass the broker.
REVOKE INSERT ON abc.sessions,abc.outbox FROM abc_app;
-- Pause still uses the separately checked idempotency table. Prevent
-- abc_app direct creation of forged 'create' receipts via an invoker trigger.
CREATE FUNCTION abc.eng01_create_receipt_gate() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,abc
AS $receipt$
BEGIN
  IF session_user='abc_app' AND current_user='abc_app' AND NEW.operation='create' THEN
    RAISE EXCEPTION 'ENG01 create receipt must use broker' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END;
$receipt$;
REVOKE ALL ON FUNCTION abc.eng01_create_receipt_gate() FROM PUBLIC;
CREATE TRIGGER eng01_create_receipt_gate_before_insert
  BEFORE INSERT ON abc.idempotency FOR EACH ROW
  EXECUTE FUNCTION abc.eng01_create_receipt_gate();

-- The staging migrator is an explicit privileged owner, not a runtime role.
-- FORCE RLS also applies to table owners; grant this pre-existing operator
-- role its administrative policies when staged, so SECURITY DEFINER functions
-- work consistently under its controlled schema ownership.
DO $policy$ BEGIN
  IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='abc_staging_migrator') THEN
    CREATE POLICY abc_migrator_owner_sessions ON abc.sessions
       FOR ALL TO abc_staging_migrator USING(true) WITH CHECK(true);
    CREATE POLICY abc_migrator_owner_memberships ON abc.memberships
       FOR ALL TO abc_staging_migrator USING(true) WITH CHECK(true);
    CREATE POLICY abc_migrator_owner_outbox ON abc.outbox
       FOR ALL TO abc_staging_migrator USING(true) WITH CHECK(true);
    CREATE POLICY abc_migrator_owner_idempotency ON abc.idempotency
       FOR ALL TO abc_staging_migrator USING(true) WITH CHECK(true);
    CREATE POLICY abc_migrator_owner_create_audit ON abc.eng01_create_audit
       FOR ALL TO abc_staging_migrator USING(true) WITH CHECK(true);
    CREATE POLICY abc_migrator_owner_api_bindings ON abc.eng01_api_login_bindings
       FOR ALL TO abc_staging_migrator USING(true) WITH CHECK(true);
  END IF;
END $policy$;
COMMIT;

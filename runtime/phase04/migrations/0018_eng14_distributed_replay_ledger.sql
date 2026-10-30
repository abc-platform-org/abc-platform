-- 0018: Durable, atomic, cross-process JWT jti replay prevention for v2.
-- No application/worker can SELECT, INSERT, UPDATE or DELETE this table.
-- A gateway must verify JWT signature/issuer/audience/expiry before claiming.
-- Real managed tenants additionally require physical PG clientcert identity
-- through abc.eng14_workload_allowed; GUCs alone never satisfy that gate.
BEGIN;
CREATE TABLE abc.eng14_v2_replay_ledger(
  replay_digest text PRIMARY KEY
    CHECK (replay_digest ~ '^[0-9a-f]{64}$'),
  tenant_id text NOT NULL REFERENCES abc.tenants(tenant_id),
  issuer text NOT NULL CHECK (length(issuer) BETWEEN 9 AND 512),
  audience text NOT NULL CHECK (length(audience) BETWEEN 3 AND 256),
  issued_jti uuid NOT NULL,
  expires_at timestamptz NOT NULL,
  claimed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  CHECK (expires_at>claimed_at)
);
CREATE INDEX eng14_replay_gc_expiry ON abc.eng14_v2_replay_ledger(expires_at);
ALTER TABLE abc.eng14_v2_replay_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.eng14_v2_replay_ledger FORCE ROW LEVEL SECURITY;
REVOKE ALL ON abc.eng14_v2_replay_ledger FROM PUBLIC,abc_app,
  abc_worker,abc_answer_worker,abc_orchestrator,abc_eng03_worker,
  abc_pipeline_worker;

CREATE FUNCTION abc.eng14_claim_v2_jti(
  p_tenant text,p_issuer text,p_audience text,p_jti uuid,p_expires_at timestamptz
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,abc
AS $replay$
DECLARE
  v_claimed boolean;
  v_digest text;
  v_now timestamptz:=clock_timestamp();
BEGIN
  -- SECURITY DEFINER changes current_user, but session_user remains the\n  -- immutable DB-authenticated principal checked by workload_allowed.\n  IF (p_tenant IS NULL OR length(p_tenant) NOT BETWEEN 1 AND 128
      OR p_issuer IS NULL OR length(p_issuer) NOT BETWEEN 9 AND 512
      OR p_issuer NOT LIKE 'https://%'
      OR p_audience IS NULL OR length(p_audience) NOT BETWEEN 3 AND 256
      OR p_jti IS NULL OR p_expires_at IS NULL
      OR p_expires_at<=v_now
      OR p_expires_at>v_now+interval '5 minutes'
      OR NOT abc.eng14_workload_allowed(p_tenant)
  ) THEN
    RAISE EXCEPTION 'ENG14 replay gate denied' USING ERRCODE='42501';
  END IF;
  -- Unique across tenants for the same issuer/audience/JTI; session/tenant
  -- changes cannot turn a previously consumed bearer into a new token.
  -- Digest avoids storing reusable bearer content.
  v_digest:=encode(sha256(convert_to(
      p_issuer||chr(31)||p_audience||chr(31)||p_jti::text,'UTF8'
    )),'hex');
  INSERT INTO abc.eng14_v2_replay_ledger(
      replay_digest,tenant_id,issuer,audience,issued_jti,expires_at)
  VALUES(v_digest,p_tenant,p_issuer,p_audience,p_jti,p_expires_at)
  ON CONFLICT (replay_digest) DO NOTHING
  RETURNING true INTO v_claimed;
  RETURN COALESCE(v_claimed,false);
END;
$replay$;
REVOKE ALL ON FUNCTION abc.eng14_claim_v2_jti(
  text,text,text,uuid,timestamptz) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION abc.eng14_claim_v2_jti(
  text,text,text,uuid,timestamptz) TO abc_app;
DO $owner_policy$ BEGIN
  IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='abc_staging_migrator') THEN
    CREATE POLICY eng14_replay_operator_policy
      ON abc.eng14_v2_replay_ledger FOR ALL TO abc_staging_migrator
      USING(true) WITH CHECK(true);
  END IF;
END $owner_policy$;
-- GC is operator-controlled only, with explicitly reviewed retention.
-- Runtime cannot clean/reuse tokens during a multi-replica race.
COMMIT;

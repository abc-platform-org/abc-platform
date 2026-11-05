-- 0033 / A2-G05 hardened: explicit operator-owned caller certificate grant.
-- Extends 0032 without modifying its checksum. Simulates revocation only
-- in disposable CI. This is NOT an external CA, CRL/OCSP, OIDC or production
-- workload identity. In managed mode physical DB clientcert remains mandatory.
BEGIN;

CREATE TABLE abc.g05_synthetic_cert_grants (
  tenant_id text NOT NULL REFERENCES abc.tenants(tenant_id),
  caller_engine text NOT NULL CHECK (caller_engine IN ('ENG-03','ENG-04','ENG-05')),
  target_engine text NOT NULL CHECK (target_engine IN ('ENG-04','ENG-05','ENG-06')),
  consumer_id text NOT NULL CHECK (length(consumer_id) BETWEEN 3 AND 96),
  client_cert_sha256 text NOT NULL CHECK (client_cert_sha256 ~ '^[0-9a-f]{64}$'),
  active boolean NOT NULL DEFAULT false,
  granted_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  valid_until timestamptz NOT NULL,
  revoked_at timestamptz,
  PRIMARY KEY (tenant_id,caller_engine,target_engine,consumer_id,client_cert_sha256),
  CHECK ((NOT active) OR (revoked_at IS NULL AND valid_until>granted_at))
);
ALTER TABLE abc.g05_synthetic_cert_grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.g05_synthetic_cert_grants FORCE ROW LEVEL SECURITY;
REVOKE ALL ON abc.g05_synthetic_cert_grants FROM PUBLIC;
-- Deliberately no INSERT/UPDATE/SELECT grant to API or engine workers.
DO $policy$ BEGIN
  IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='abc_staging_migrator') THEN
    CREATE POLICY g05_operator_cert_grants ON abc.g05_synthetic_cert_grants
       FOR ALL TO abc_staging_migrator USING(true) WITH CHECK(true);
  END IF;
END $policy$;

CREATE FUNCTION abc.eng14_g05_cert_bound_admit_and_claim(
  p_tenant text,p_branch text,p_session uuid,p_state_version integer,
  p_caller text,p_target text,p_consumer text,
  p_human_issuer text,p_human_subject text,
  p_workload_issuer text,p_audience text,p_jti uuid,p_expires_at timestamptz,
  p_cert_sha256 text
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,abc
AS $bound$
DECLARE
  v_grant text;
BEGIN
  IF p_cert_sha256 IS NULL
     OR p_cert_sha256 !~ '^[0-9a-f]{64}$'
     OR NOT abc.eng14_workload_allowed(p_tenant) THEN
    RAISE EXCEPTION 'A2-G05 certificate identity missing or not managed'
      USING ERRCODE='42501';
  END IF;
  -- The JWT verifier has already authenticated the actual TLS peer DER and
  -- its cnf x5t#S256 binding. This DB-side registry restricts a VERIFIED
  -- certificate to one tenant, consumer and canonical engine route.
  SELECT client_cert_sha256 INTO v_grant
    FROM abc.g05_synthetic_cert_grants
    WHERE tenant_id=p_tenant AND caller_engine=p_caller
      AND target_engine=p_target AND consumer_id=p_consumer
      AND client_cert_sha256=p_cert_sha256
      AND active AND revoked_at IS NULL AND valid_until>clock_timestamp()
    FOR SHARE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'A2-G05 certificate grant absent, expired or revoked'
      USING ERRCODE='42501';
  END IF;
  -- In one transaction, acquire locks on workload grant, session,
  -- specialist qualification and consent, then claim distributed JWT JTI.
  RETURN abc.eng14_g05_admit_and_claim(
     p_tenant,p_branch,p_session,p_state_version,
     p_caller,p_target,p_consumer,p_human_issuer,p_human_subject,
     p_workload_issuer,p_audience,p_jti,p_expires_at);
END;
$bound$;

REVOKE ALL ON FUNCTION abc.eng14_g05_cert_bound_admit_and_claim(
 text,text,uuid,integer,text,text,text,text,text,text,text,uuid,timestamptz,text)
 FROM PUBLIC;
-- Prevent bypassing the certificate registry through legacy 0032 entrypoint.
REVOKE EXECUTE ON FUNCTION abc.eng14_g05_admit_and_claim(
 text,text,uuid,integer,text,text,text,text,text,text,text,uuid,timestamptz)
 FROM abc_app;
GRANT EXECUTE ON FUNCTION abc.eng14_g05_cert_bound_admit_and_claim(
 text,text,uuid,integer,text,text,text,text,text,text,text,uuid,timestamptz,text)
 TO abc_app;
COMMENT ON TABLE abc.g05_synthetic_cert_grants IS
 'Synthetic CI-only certificate policy fixture; NOT managed PKI authority';
COMMIT;

-- 0015: ENG14 guards the session INSERT boundary as well as state UPDATE.
-- 0014 protected mutations, but abc_app could still INSERT a synthetic row
-- already marked PAUSED or with a forged initial version/checkpoint.
-- This append-only migration leaves earlier checksums and contracts intact.
BEGIN;
CREATE FUNCTION abc.eng14_session_creation_gate() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER
SET search_path=pg_catalog,abc
AS $gate$
BEGIN
  -- Privileged database operators retain their existing explicit provisioning
  -- route. Runtime application INSERT is restricted independently of HTTP.
  IF session_user <> 'abc_app' THEN
    RETURN NEW;
  END IF;
  IF NEW.state IS DISTINCT FROM 'CREATED'
     OR NEW.state_version IS DISTINCT FROM 0
     OR NEW.checkpoint IS NOT NULL
     OR current_setting('abc.issuer',true) NOT LIKE 'https://%'
     OR current_setting('abc.subject',true) IS DISTINCT FROM NEW.specialist_id
     OR current_setting('abc.tenant',true) IS DISTINCT FROM NEW.tenant_id
     OR current_setting('abc.branch',true) IS DISTINCT FROM NEW.branch_id
     OR NOT EXISTS (
         SELECT 1 FROM abc.memberships m
          WHERE m.issuer=current_setting('abc.issuer',true)
            AND m.subject=NEW.specialist_id
            AND m.tenant_id=NEW.tenant_id
            AND m.branch_id=NEW.branch_id
            AND m.role='SPECIALIST' AND m.active
          FOR SHARE)
  THEN
    RAISE EXCEPTION 'ENG14 initial session state denied'
      USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END;
$gate$;
REVOKE ALL ON FUNCTION abc.eng14_session_creation_gate() FROM PUBLIC;
CREATE TRIGGER eng14_session_creation_gate_before_insert
  BEFORE INSERT ON abc.sessions
  FOR EACH ROW EXECUTE FUNCTION abc.eng14_session_creation_gate();

-- Both application checkpoint implementations now use the 0014
-- SECURITY DEFINER broker. They no longer require a direct session UPDATE
-- grant, including the previously left-open version/metadata columns.
-- ENG02's distinct abc_orchestrator authorization remains unchanged.
REVOKE UPDATE(state_version,updated_at,last_event_id)
  ON abc.sessions FROM abc_app;
COMMIT;

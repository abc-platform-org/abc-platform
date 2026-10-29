-- 0014: ENG14 first-authority state transition enforcement for ENG01 storage.
-- Consultations only store CREATED and PAUSED; 102 canonical edges are NOT
-- implemented by changing that SQL CHECK. All higher-risk edges fail closed.
BEGIN;
CREATE TABLE abc.eng14_state_guard_audit (
  guard_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL REFERENCES abc.sessions(session_id),
  tenant_id text NOT NULL,
  branch_id text NOT NULL,
  source_state text NOT NULL,
  target_state text NOT NULL,
  from_version integer NOT NULL,
  to_version integer NOT NULL,
  result text NOT NULL CHECK(result='ALLOW_SYNTHETIC_PAUSE_S0'),
  actor_id text NOT NULL,
  guard_version text NOT NULL CHECK(guard_version='eng14.state.synthetic.1'),
  occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE(session_id,to_version)
);
ALTER TABLE abc.eng14_state_guard_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE abc.eng14_state_guard_audit FORCE ROW LEVEL SECURITY;
REVOKE ALL ON abc.eng14_state_guard_audit FROM PUBLIC,abc_app,abc_worker,
 abc_answer_worker,abc_orchestrator,abc_eng03_worker,abc_pipeline_worker;
CREATE FUNCTION abc.eng14_state_transition_gate() RETURNS trigger
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
  IF session_user<>'abc_app'
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
REVOKE ALL ON FUNCTION abc.eng14_state_transition_gate() FROM PUBLIC;
CREATE TRIGGER eng14_state_transition_gate_before_update
  BEFORE UPDATE OF state ON abc.sessions
  FOR EACH ROW EXECUTE FUNCTION abc.eng14_state_transition_gate();
-- Direct application SQL may update answer metadata, not state/checkout.
-- Remove the legacy table-level UPDATE grant, then allow non-state fields only.
REVOKE UPDATE ON abc.sessions FROM abc_app;
GRANT UPDATE(state_version,updated_at,last_event_id) ON abc.sessions TO abc_app;
CREATE FUNCTION abc.eng14_apply_pause(p_session uuid,p_expected_version integer)
RETURNS SETOF abc.sessions
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,abc
AS $apply$
BEGIN
  IF session_user<>'abc_app' OR p_expected_version<0
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
REVOKE ALL ON FUNCTION abc.eng14_apply_pause(uuid,integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION abc.eng14_apply_pause(uuid,integer) TO abc_app;
COMMIT;

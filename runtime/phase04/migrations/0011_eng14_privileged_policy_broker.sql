-- 0011 / security refinement: ENG14 issuance moves into a privileged,
-- deterministic server-side PostgreSQL policy function. Runtime orchestrator
-- has no direct INSERT grant on the approval table. Function checks scoped
-- membership, admin workload ACL, service/profile, current session version,
-- required question order, critical stop conditions and digest shape itself.
BEGIN;
REVOKE INSERT ON abc.eng14_policy_audit FROM abc_orchestrator;
CREATE FUNCTION abc.issue_eng14_answer_proof(
    p_decision_id uuid, p_command_id uuid, p_tenant text, p_branch text,
    p_session uuid, p_actor text, p_version integer, p_digest text,
    p_service_issuer text, p_service_subject text,
    p_question text, p_profile text)
RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,abc
AS $eng14$
DECLARE
  session_row record;
  previous_count integer;
  expected_position integer;
BEGIN
  IF p_profile<>'synthetic-1.0.0'
     OR p_version < 1
     OR p_digest !~ '^[0-9a-f]{64}$'
     OR p_actor <> current_setting('abc.subject',true)
     OR p_tenant <> current_setting('abc.tenant',true)
     OR p_branch <> current_setting('abc.branch',true)
     OR current_setting('abc.issuer',true) IS NULL
  THEN
      RAISE EXCEPTION 'ENG14 invalid trusted context'
        USING ERRCODE='23514';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM abc.memberships m
       WHERE m.issuer=current_setting('abc.issuer',true)
         AND m.subject=p_actor AND m.tenant_id=p_tenant
         AND m.branch_id=p_branch AND m.role='SPECIALIST'
         AND m.active FOR SHARE)
     OR NOT EXISTS (SELECT 1 FROM abc.engine_workload_grants g
       WHERE g.issuer=p_service_issuer AND g.service_subject=p_service_subject
         AND g.engine_id='ENG-02' AND g.tenant_id=p_tenant
         AND g.branch_id=p_branch AND g.permission='ENG02_RECORD_ANSWER'
         AND g.active FOR SHARE)
  THEN
      RAISE EXCEPTION 'ENG14 identity authorization failed'
        USING ERRCODE='23514';
  END IF;
  SELECT s.state,s.state_version,s.service_id,s.specialist_id
       INTO session_row FROM abc.sessions s
       WHERE s.session_id=p_session AND s.tenant_id=p_tenant
         AND s.branch_id=p_branch FOR UPDATE;
  IF NOT FOUND OR session_row.specialist_id<>p_actor
       OR session_row.state<>'CREATED'
       OR session_row.service_id<>'synthetic:hair-color'
       OR session_row.state_version<>p_version
  THEN
      RAISE EXCEPTION 'ENG14 session/version gate failed'
        USING ERRCODE='23514';
  END IF;
  expected_position=CASE p_question
       WHEN 'synthetic:prior-treatment' THEN 0
       WHEN 'synthetic:sensitivity' THEN 1
       WHEN 'synthetic:desired-goal' THEN 2
       WHEN 'synthetic:maintenance' THEN 3
       ELSE -1 END;
  SELECT count(*) INTO previous_count FROM abc.eng02_answers a
       WHERE a.session_id=p_session AND a.tenant_id=p_tenant
         AND a.branch_id=p_branch
         AND a.question_profile_version=p_profile;
  IF expected_position<0 OR previous_count<>expected_position
     OR EXISTS(SELECT 1 FROM abc.eng02_answers a
         WHERE a.session_id=p_session AND a.tenant_id=p_tenant
           AND a.question_id=p_question)
     OR (expected_position>=1 AND NOT EXISTS(
           SELECT 1 FROM abc.eng02_answers a WHERE
             a.session_id=p_session AND a.tenant_id=p_tenant
             AND a.question_id='synthetic:prior-treatment'))
     OR (expected_position>=2 AND NOT EXISTS(
           SELECT 1 FROM abc.eng02_answers a WHERE
             a.session_id=p_session AND a.tenant_id=p_tenant
             AND a.question_id='synthetic:sensitivity'))
     OR (expected_position>=3 AND NOT EXISTS(
           SELECT 1 FROM abc.eng02_answers a WHERE
             a.session_id=p_session AND a.tenant_id=p_tenant
             AND a.question_id='synthetic:desired-goal'))
     OR EXISTS(SELECT 1 FROM abc.eng02_answers a WHERE
         a.session_id=p_session AND a.tenant_id=p_tenant
         AND ((a.question_id='synthetic:prior-treatment' AND a.value='UNKNOWN')
           OR (a.question_id='synthetic:sensitivity' AND a.value IN ('YES','UNKNOWN'))))
  THEN
      RAISE EXCEPTION 'ENG14 question or safety stop failed'
        USING ERRCODE='23514';
  END IF;
  INSERT INTO abc.eng14_policy_audit (
        decision_id,command_id,tenant_id,branch_id,session_id,actor_id,
        aggregate_version,policy_version,scope,decision,input_digest,evaluated_at)
  VALUES(p_decision_id,p_command_id,p_tenant,p_branch,p_session,p_actor,
        p_version,'eng14.synthetic.1','QUESTION','ALLOW',p_digest,clock_timestamp());
  RETURN p_decision_id;
END
$eng14$;
REVOKE ALL ON FUNCTION abc.issue_eng14_answer_proof(
    uuid,uuid,text,text,uuid,text,integer,text,text,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION abc.issue_eng14_answer_proof(
    uuid,uuid,text,text,uuid,text,integer,text,text,text,text,text)
    TO abc_orchestrator;

-- Extra database safety layer against direct table INSERT even if the
-- orchestrator credential is used outside the controlled Python gateway.
CREATE OR REPLACE FUNCTION abc.enforce_eng14_answer_policy() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,abc
AS $policy$
BEGIN
  IF NEW.question_profile_version<>'synthetic-1.0.0'
   OR NOT (
      (NEW.question_id='synthetic:prior-treatment'
       AND NEW.value IN ('YES','NO','UNKNOWN'))
      OR (NEW.question_id='synthetic:sensitivity'
       AND NEW.value IN ('YES','NO','UNKNOWN'))
      OR (NEW.question_id='synthetic:desired-goal'
       AND NEW.value IN ('SUBTLE','BOLD','UNSURE'))
      OR (NEW.question_id='synthetic:maintenance'
       AND NEW.value IN ('LOW','FLEXIBLE','UNKNOWN'))
   )
   OR NEW.policy_decision_id IS NULL
   OR NOT EXISTS(SELECT 1 FROM abc.eng14_policy_audit decision
     WHERE decision.decision_id=NEW.policy_decision_id
       AND decision.tenant_id=NEW.tenant_id
       AND decision.branch_id=NEW.branch_id
       AND decision.session_id=NEW.session_id
       AND decision.actor_id=NEW.actor_id
       AND decision.aggregate_version=NEW.aggregate_version
       AND decision.decision='ALLOW'
       AND decision.scope='QUESTION'
       AND decision.policy_version='eng14.synthetic.1')
  THEN
    RAISE EXCEPTION 'ENG14 verified policy proof required'
      USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END
$policy$;
COMMIT;

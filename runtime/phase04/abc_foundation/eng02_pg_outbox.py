"""ENG01 protected command processing for ENG02: ONE PostgreSQL transaction.

Uses dedicated abc_orchestrator SQL identity, different from the HTTP API and
event worker. Synthetic answer flow only. Never receives real-client data.
Session state can remain CREATED while aggregate version advances per answer.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid

import psycopg
from psycopg.rows import dict_row

from .store import DomainError
from .eng14_policy import SyntheticQuestionPolicy

_PROFILE_FILE=Path(__file__).with_name("eng02_synthetic_profiles.json")
_PROFILE=json.loads(_PROFILE_FILE.read_text())["profiles"][0]
_QUESTIONS={q["question_id"]:q for q in _PROFILE["questions"]}
_SORTED=sorted(_PROFILE["questions"],key=lambda q:(-q["priority"],q["question_id"]))


def _uuid(value):
    try:
        u=uuid.UUID(value)
        if str(u)!=value: raise ValueError()
        return u
    except (ValueError,AttributeError,TypeError):
        raise DomainError(400,"invalid_command_uuid") from None


def _canonical(request):
    try:
        return hashlib.sha256(json.dumps(request,sort_keys=True,separators=(",",":"),
            ensure_ascii=True,allow_nan=False).encode()).hexdigest()
    except (TypeError,ValueError,OverflowError):
        raise DomainError(400,"invalid_command_json") from None


def _timestamp(value):
    if not isinstance(value,str) or len(value)>48:
        raise DomainError(400,"invalid_command_timestamp")
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
        if dt.utcoffset() is None: raise ValueError()
        return dt.astimezone(timezone.utc)
    except (ValueError,AttributeError,TypeError):
        raise DomainError(400,"invalid_command_timestamp") from None


class PGENG02CommandWriter:
    """ENFORCED: only a dedicated DB role abc_orchestrator can persist answers."""
    _FIELDS=frozenset(("command_id","correlation_id","session_id",
        "tenant_id","branch_id","engine_id","contract_version","profile_version",
        "question_id","value","answer_source","expected_state_version",
        "requested_at"))
    def __init__(self, dsn, *, clock=None):
        if not isinstance(dsn,str) or not dsn:
            raise ValueError("orchestrator_database_dsn_required")
        self.dsn=dsn
        self.clock=clock or (lambda:datetime.now(timezone.utc))

    def _connect(self):
        return psycopg.connect(self.dsn,row_factory=dict_row,connect_timeout=4)

    def record_synthetic_answer(self, human,workload,command):
        if not isinstance(command,dict) or set(command)!=self._FIELDS:
            raise DomainError(400,"invalid_eng02_command")
        command_id=_uuid(command["command_id"])
        correlation=_uuid(command["correlation_id"])
        session_id=_uuid(command["session_id"])
        if (command["engine_id"]!="ENG-02" or
            command["contract_version"]!="1.0.0-draft" or
            command["profile_version"]!=_PROFILE["profile_version"]):
            raise DomainError(501,"eng02_contract_not_supported")
        question=_QUESTIONS.get(command["question_id"])
        if (not question or not isinstance(command["value"],str)
            or command["value"] not in question["allowed_values"]
            or command["answer_source"] not in ("CLIENT","SPECIALIST")
            or type(command["expected_state_version"]) is not int
            or command["expected_state_version"]<0):
            raise DomainError(400,"invalid_answer_or_version")
        now=self.clock().astimezone(timezone.utc)
        when=_timestamp(command["requested_at"])
        if abs((now-when).total_seconds())>120:
            raise DomainError(400,"command_outside_time_window")
        subject=getattr(human,"subject",None)
        issuer=getattr(human,"issuer",None)
        engine=getattr(workload,"engine_id",None)
        service_issuer=getattr(workload,"issuer",None)
        service_subject=getattr(workload,"subject",None)
        token_id=getattr(workload,"token_id",None)
        if (not isinstance(subject,str) or not subject or
            not isinstance(issuer,str) or not issuer.startswith("https://") or
            engine!="ENG-02" or service_subject!="svc:abc-eng02" or
            not isinstance(service_issuer,str) or not service_issuer.startswith("https://")
            or not isinstance(token_id,str)):
            raise DomainError(401,"verified_engine_and_human_required")
        # Bind signed service token ID as well as command to idempotent receipt:
        # legitimate retries must reuse exactly the same short-lived service token.
        digest=_canonical({"human":(issuer,subject),
              "service":(service_issuer,service_subject,engine,token_id),
              "command":command})
        tenant,branch=command["tenant_id"],command["branch_id"]
        if any(not isinstance(x,str) or not 1<=len(x)<=128 for x in (tenant,branch)):
            raise DomainError(400,"invalid_command_scope")
        with self._connect() as con:
            current=con.execute("SELECT current_user AS role").fetchone()["role"]
            if current!="abc_orchestrator":
                raise DomainError(403,"dedicated_orchestrator_database_role_required")
            for key,value in (("abc.issuer",issuer),("abc.subject",subject),
                              ("abc.tenant",tenant),("abc.branch",branch)):
                con.execute("SELECT set_config(%s,%s,true)",(key,value))
            # The real authority comes from DB-side grants, not JWT asserted
            # tenant, permission, branch, user role, engine list or headers.
            grant=con.execute("""SELECT 1 FROM abc.engine_workload_grants
               WHERE issuer=%s AND service_subject=%s AND engine_id='ENG-02'
                AND tenant_id=%s AND branch_id=%s
                AND permission='ENG02_RECORD_ANSWER' AND active=true""",
                 (service_issuer,service_subject,tenant,branch)).fetchone()
            if not grant:
                raise DomainError(403,"workload_permission_denied")
            member=con.execute("""SELECT 1 FROM abc.memberships
              WHERE issuer=%s AND subject=%s AND tenant_id=%s AND branch_id=%s
              AND role='SPECIALIST' AND active=true""",
              (issuer,subject,tenant,branch)).fetchone()
            if not member:
                raise DomainError(403,"human_membership_denied")
            row=con.execute("""SELECT session_id,state,state_version,specialist_id,service_id
                   FROM abc.sessions WHERE session_id=%s AND tenant_id=%s
                   AND branch_id=%s AND specialist_id=%s FOR UPDATE""",
                (session_id,tenant,branch,subject)).fetchone()
            if row is None:
                raise DomainError(404,"not_found")
            # RLS + session row lock: no revocation bypass, no concurrent
            # answers crossing the command-version boundary.
            receipt=con.execute("""SELECT request_digest,response_json
                FROM abc.eng02_command_receipts WHERE tenant_id=%s AND command_id=%s""",
                (tenant,command_id)).fetchone()
            if receipt is not None:
                if receipt["request_digest"]!=digest:
                    raise DomainError(409,"idempotency_payload_conflict")
                return receipt["response_json"]
            if (row["state"]!="CREATED" or row["service_id"]!="synthetic:hair-color"):
                raise DomainError(409,"synthetic_active_session_required")
            if row["state_version"]!=command["expected_state_version"]:
                raise DomainError(409,"state_version_conflict")
            answers=con.execute("""SELECT question_id,value FROM abc.eng02_answers
               WHERE tenant_id=%s AND branch_id=%s AND session_id=%s
                 AND question_profile_version=%s""",
               (tenant,branch,session_id,_PROFILE["profile_version"])).fetchall()
            recorded={a["question_id"]:a["value"] for a in answers}
            if any(q["critical"] and recorded.get(q["question_id"])=="UNKNOWN"
                    for q in _SORTED):
                raise DomainError(409,"critical_unknown_requires_specialist")
            if recorded.get("synthetic:sensitivity")=="YES":
                raise DomainError(409,"reported_sensitivity_requires_specialist")
            next_question=next((q["question_id"] for q in _SORTED
                                if q["question_id"] not in recorded),None)
            if command["question_id"]!=next_question:
                raise DomainError(409,"question_order_or_duplicate_denied")
            # ENG14 interception occurs after trusted DB ACL, membership and
            # row lock, but before ANY session/answer/outbox mutation.
            policy=SyntheticQuestionPolicy()
            decision=policy.evaluate(
                command_id=str(command_id),tenant_id=tenant,session_id=str(session_id),
                service_id=row["service_id"],state=row["state"],
                answers=recorded,question_id=command["question_id"],
                expected_question=next_question,profile_version=command["profile_version"])
            policy.require_allow(decision)
            eid,aid=uuid.uuid4(),uuid.uuid4()
            newversion=row["state_version"]+1
            updated=con.execute("""UPDATE abc.sessions SET state_version=%s,
                       updated_at=%s,last_event_id=%s
                       WHERE session_id=%s AND state_version=%s AND state='CREATED'
                       RETURNING state_version""",
                        (newversion,now,eid,session_id,row["state_version"])).fetchone()
            if updated is None:
                raise DomainError(409,"state_version_conflict")
            con.execute("""INSERT INTO abc.eng14_policy_audit
                (decision_id,command_id,tenant_id,branch_id,session_id,
                 actor_id,aggregate_version,policy_version,scope,decision,
                 input_digest,evaluated_at)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'QUESTION','ALLOW',%s,%s)""",
                (uuid.UUID(decision["policy_decision_id"]),command_id,tenant,branch,
                 session_id,subject,newversion,decision["policy_version"],digest,now))
            con.execute("""INSERT INTO abc.eng02_answers
                 (tenant_id,branch_id,session_id,question_profile_version,
                  question_id,value,answer_source,actor_id,answer_id,
                  aggregate_version,policy_decision_id)
                 VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                 (tenant,branch,session_id,_PROFILE["profile_version"],
                  command["question_id"],command["value"],command["answer_source"],
                  subject,aid,newversion,uuid.UUID(decision["policy_decision_id"])))
            event={"event_id":str(eid),"event_type":"ANSWER_RECORDED",
              "event_schema_version":"1.0.0-draft","tenant_id":tenant,"branch_id":branch,
              "session_id":str(session_id),"aggregate_id":str(session_id),
              "aggregate_version":newversion,"occurred_at":now.isoformat().replace("+00:00","Z"),
              "correlation_id":str(correlation),
              "actor":{"user_id":subject,"role":"SPECIALIST"},
              "payload":{"question_id":command["question_id"],
                         "session_id":str(session_id),"answer_id":str(aid)},
              "producer_engine_id":"ENG-02","trace_id":str(uuid.uuid4())}
            con.execute("""INSERT INTO abc.outbox
                (event_id,tenant_id,aggregate_id,aggregate_version,event_json,created_at)
                VALUES(%s,%s,%s,%s,%s,%s)""",
                (eid,tenant,session_id,newversion,json.dumps(event),now))
            response={"answer_id":str(aid),"event_id":str(eid),
               "session_id":str(session_id),"aggregate_version":newversion,
               "status":"ANSWER_RECORDED_ATOMICALLY_SYNTHETIC_ONLY",
               "command_id":str(command_id),"profile_version":_PROFILE["profile_version"]}
            try:
                con.execute("""INSERT INTO abc.eng02_command_receipts
                   (command_id,tenant_id,branch_id,session_id,actor_id,service_issuer,
                    service_subject,request_digest,event_id,response_json)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                   (command_id,tenant,branch,session_id,subject,
                    service_issuer,service_subject,digest,eid,json.dumps(response)))
            except psycopg.errors.UniqueViolation:
                raise DomainError(409,"command_id_conflict") from None
            return response

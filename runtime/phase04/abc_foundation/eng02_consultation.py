"""ENG02 deterministic offline consultation engine, synthetic data ONLY.

An independent SQLite local proof for validated, idempotent question/answer
progress. No medical advice, real clients, session state mutation, provider calls,
canonical outbox publication or claim of a released service pack.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid

from .store import DomainError, _nonempty

SYNTHETIC_SERVICE="synthetic:hair-color"
FIXTURE_PATH=Path(__file__).with_name("eng02_synthetic_profiles.json")


def _stamp():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")


def _digest(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


class ConsultationEngine:
    ENGINE_ID="ENG-02"
    def __init__(self, sqlite_path, authorized_sessions, profiles=None):
        if not callable(getattr(authorized_sessions,"get",None)):
            raise ValueError("authoritative_authenticated_session_store_required")
        self.sessions=authorized_sessions
        self.path=str(sqlite_path)
        cfg=profiles if profiles is not None else json.loads(FIXTURE_PATH.read_text())
        if (cfg.get("kind")!="SYNTHETIC_FIXTURE_NOT_APPROVED_SERVICE_PACK"
            or cfg.get("registry_version")!="eng02.synthetic.1"
            or not isinstance(cfg.get("profiles"),list)
            or len(cfg["profiles"])!=1):
            raise ValueError("synthetic_question_registry_not_validated")
        profile=cfg["profiles"][0]
        if (profile.get("service_id")!=SYNTHETIC_SERVICE
            or profile.get("enabled_for_real_clients") is not False
            or not _nonempty(profile.get("profile_version"))):
            raise ValueError("real_service_or_unknown_profile")
        self.profile=profile
        self.questions={}
        for q in profile.get("questions",[]):
            if (not isinstance(q,dict)
                or set(q)!={"question_id","field","text","reason","priority","critical","allowed_values"}
                or not all(_nonempty(q[k]) for k in ("question_id","field","text","reason"))
                or type(q["priority"]) is not int or not 1<=q["priority"]<=100
                or type(q["critical"]) is not bool
                or q["reason"] not in ("SAFETY_NECESSITY","DECISION_IMPACT")
                or not isinstance(q["allowed_values"],list) or not q["allowed_values"]
                or any(not _nonempty(x) for x in q["allowed_values"])
                or len(set(q["allowed_values"]))!=len(q["allowed_values"])
                or q["question_id"] in self.questions):
                raise ValueError("invalid_synthetic_question")
            self.questions[q["question_id"]]=q
        if not self.questions or len({q["field"] for q in self.questions.values()})!=len(self.questions):
            raise ValueError("invalid_question_fields")
        self._initialize()

    def _connect(self):
        con=sqlite3.connect(self.path,timeout=10,isolation_level=None)
        con.row_factory=sqlite3.Row
        con.execute("PRAGMA busy_timeout=10000")
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def _initialize(self):
        with self._connect() as con:
            con.execute("PRAGMA journal_mode=WAL")
            con.executescript("""
                CREATE TABLE IF NOT EXISTS eng02_answers (
                  tenant_id text NOT NULL, branch_id text NOT NULL,
                  session_id text NOT NULL, profile_version text NOT NULL,
                  question_id text NOT NULL, value text NOT NULL, source text NOT NULL,
                  actor_id text NOT NULL, answer_id text NOT NULL, created_at text NOT NULL,
                  PRIMARY KEY (tenant_id,session_id,profile_version,question_id)
                );
                CREATE TABLE IF NOT EXISTS eng02_receipts (
                  tenant_id text NOT NULL, session_id text NOT NULL,
                  actor_id text NOT NULL, operation_key text NOT NULL,
                  fingerprint text NOT NULL, response_json text NOT NULL,
                  PRIMARY KEY (tenant_id,session_id,actor_id,operation_key)
                );
            """)

    def _authorized(self,principal,session_id):
        sub,iss=getattr(principal,"subject",None),getattr(principal,"issuer",None)
        if not _nonempty(sub) or not isinstance(iss,str) or not iss.startswith("https://"):
            raise DomainError(401,"verified_identity_required")
        try: sid=str(uuid.UUID(session_id))
        except (TypeError,ValueError,AttributeError):
            raise DomainError(404,"not_found") from None
        session=self.sessions.get(principal,sid)
        if (not isinstance(session,dict) or session.get("session_id")!=sid
            or session.get("specialist_id")!=sub or not _nonempty(session.get("tenant_id"))
            or not _nonempty(session.get("branch_id"))):
            raise DomainError(403,"scope_not_authorized")
        if session.get("service_id") != SYNTHETIC_SERVICE:
            raise DomainError(403,"synthetic_service_only")
        if session.get("state") in ("CANCELLED","CLOSED","CLOSED_WITHOUT_DECISION","SAFETY_BLOCKED","PAUSED"):
            raise DomainError(409,"session_not_active")
        return session

    def _read_answers(self,con,s):
        rows=con.execute("""SELECT question_id,value,source,answer_id FROM eng02_answers
                 WHERE tenant_id=? AND branch_id=? AND session_id=? AND profile_version=?
                 ORDER BY question_id""",
                (s["tenant_id"],s["branch_id"],s["session_id"],self.profile["profile_version"])).fetchall()
        return {r["question_id"]:dict(r) for r in rows}

    def next(self,principal,session_id):
        s=self._authorized(principal,session_id)
        with self._connect() as con:
            answers=self._read_answers(con,s)
        critical_unknown=[q["field"] for q in self.questions.values()
                          if q["critical"] and q["question_id"] in answers
                          and answers[q["question_id"]]["value"]=="UNKNOWN"]
        safety_check=[q["field"] for q in self.questions.values()
                      if q["critical"] and q["question_id"] in answers
                      and q["field"]=="sensitivity_flag"
                      and answers[q["question_id"]]["value"]=="YES"]
        # Critical unknowns and flagged safety facts are escalated; a model
        # cannot continue asking its way around a professional review.
        if critical_unknown or safety_check:
            return {"engine_id":self.ENGINE_ID,"readiness":"PROFESSIONAL_CHECK_REQUIRED",
                    "critical_unknown_keys":sorted(critical_unknown+safety_check),
                    "next_question":None,"stop_reason":"SPECIALIST_REVIEW_REQUIRED",
                    "session_id":s["session_id"],"profile_version":self.profile["profile_version"]}
        unanswered=[q for q in self.questions.values() if q["question_id"] not in answers]
        if unanswered:
            chosen=sorted(unanswered,key=lambda q:(-q["priority"],q["question_id"]))[0]
            question={
                "question_id":chosen["question_id"],
                "profile_version":self.profile["profile_version"],
                "session_id":s["session_id"],"service_id":SYNTHETIC_SERVICE,
                "text":chosen["text"],"reason":chosen["reason"],
                "evidence_gap_keys":[chosen["field"]],"state":"PROPOSED",
                "asked_by":"ABC","priority_reason":"STATIC_SYNTHETIC_REGISTRY"
            }
            readiness="NEEDS_QUESTIONS"
        else:
            question=None
            readiness="READY_FOR_RECOMMENDATION"
        return {"engine_id":self.ENGINE_ID,"readiness":readiness,
                "critical_unknown_keys":[],"next_question":question,
                "session_id":s["session_id"],"profile_version":self.profile["profile_version"],
                "stop_reason":"SYNTHETIC_QUESTION_BUDGET_COMPLETE" if question is None else None}

    def record(self,principal,session_id,*,question_id,value,source,operation_key):
        s=self._authorized(principal,session_id)
        if (question_id not in self.questions or source not in ("CLIENT","SPECIALIST")
                or not isinstance(value,str) or value not in self.questions[question_id]["allowed_values"]):
            raise DomainError(400,"invalid_synthetic_answer")
        if not isinstance(operation_key,str) or not 8<=len(operation_key)<=128:
            raise DomainError(400,"invalid_idempotency_key")
        request={"question_id":question_id,"value":value,"source":source,
                 "session_id":s["session_id"],"profile_version":self.profile["profile_version"]}
        fingerprint=_digest(request)
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            try:
                key=(s["tenant_id"],s["session_id"],principal.subject,operation_key)
                prior=con.execute("""SELECT fingerprint,response_json FROM eng02_receipts
                           WHERE tenant_id=? AND session_id=? AND actor_id=? AND operation_key=?""",
                          key).fetchone()
                if prior:
                    if prior["fingerprint"]!=fingerprint:
                        raise DomainError(409,"idempotency_payload_conflict")
                    con.execute("COMMIT")
                    return json.loads(prior["response_json"])
                answers=self._read_answers(con,s)
                existing=answers.get(question_id)
                if existing:
                    if existing["value"]!=value or existing["source"]!=source:
                        raise DomainError(409,"answer_conflict_requires_professional_review")
                    raise DomainError(409,"question_already_answered_use_original_key")
                # Enforce question order, including critical-first priority.
                expected=self.next_question_in_transaction(answers)
                if expected!=question_id:
                    raise DomainError(409,"question_sequence_or_safety_block")
                aid=str(uuid.uuid4())
                now=_stamp()
                con.execute("""INSERT INTO eng02_answers
                    (tenant_id,branch_id,session_id,profile_version,question_id,
                     value,source,actor_id,answer_id,created_at)
                     VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (s["tenant_id"],s["branch_id"],s["session_id"],self.profile["profile_version"],
                     question_id,value,source,principal.subject,aid,now))
                reply={"answer_id":aid,"question_id":question_id,"status":"RECORDED_SYNTHETIC",
                       "session_id":s["session_id"],"profile_version":self.profile["profile_version"]}
                con.execute("""INSERT INTO eng02_receipts
                     (tenant_id,session_id,actor_id,operation_key,fingerprint,response_json)
                     VALUES(?,?,?,?,?,?)""",(*key,fingerprint,json.dumps(reply)))
                con.execute("COMMIT")
                return reply
            except BaseException:
                con.execute("ROLLBACK")
                raise

    def next_question_in_transaction(self,answers):
        for q in self.questions.values():
            if q["critical"] and q["question_id"] in answers and answers[q["question_id"]]["value"]=="UNKNOWN":
                return None
            if (q["field"]=="sensitivity_flag" and q["question_id"] in answers
                    and answers[q["question_id"]]["value"]=="YES"):
                return None
        unanswered=sorted((q for q in self.questions.values() if q["question_id"] not in answers),
                          key=lambda q:(-q["priority"],q["question_id"]))
        return unanswered[0]["question_id"] if unanswered else None

    def profile_snapshot(self,principal,session_id):
        s=self._authorized(principal,session_id)
        with self._connect() as con:
            answers=self._read_answers(con,s)
        next_state=self.next(principal,session_id)
        return {
            "session_id":s["session_id"],"service_id":SYNTHETIC_SERVICE,
            "question_profile_version":self.profile["profile_version"],
            "answer_ids":[answers[x]["answer_id"] for x in sorted(answers)],
            "evidence_ids":[],"readiness":next_state["readiness"],
            "critical_unknown_keys":next_state["critical_unknown_keys"],
            "updated_at":_stamp()
        }

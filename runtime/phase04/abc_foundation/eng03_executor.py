"""ENG03 independent PostgreSQL job executor, synthetic non-media only.

Distinct abc_eng03_worker credential. Claim/lease/fencing and effect+ACK share a
database transaction. Source is only available via a policy-bound SQL broker,
not a blanket ENG02 table SELECT. ENG04/05/06 work is enqueued, not invented.
"""
import hashlib
import json
import re
import uuid
from datetime import datetime,timezone
import psycopg
from psycopg.rows import dict_row

from .eng02_consultation import FIXTURE_PATH
from .store import DomainError
from .pg_outbox import CONSUMER

REGISTRY=json.loads(FIXTURE_PATH.read_text())["profiles"][0]
QUESTION={q["question_id"]:q for q in REGISTRY["questions"]}
_WORKER_ROLE="abc_eng03_worker"
_FAIL=re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")


def _json_digest(item):
    return hashlib.sha256(json.dumps(item,sort_keys=True,separators=(",",":"),
       ensure_ascii=True,allow_nan=False).encode()).hexdigest()


def _uuid(value):
    try:
        u=uuid.UUID(value)
        if str(u)!=value:
            raise ValueError()
        return u
    except (TypeError,ValueError,AttributeError):
        raise DomainError(400,"invalid_job_or_lease_uuid") from None


class ENG03Executor:
    ENGINE_ID="ENG-03"
    def __init__(self,dsn,consumer_id):
        if not isinstance(dsn,str) or not dsn:
            raise ValueError("independent_eng03_dsn_required")
        if not isinstance(consumer_id,str) or not CONSUMER.fullmatch(consumer_id):
            raise ValueError("bound_eng03_consumer_required")
        self.dsn=dsn
        self.consumer_id=consumer_id

    def _connect(self):
        con=psycopg.connect(self.dsn,row_factory=dict_row,connect_timeout=4)
        if con.execute("SELECT current_user AS role").fetchone()["role"]!=_WORKER_ROLE:
            con.close()
            raise DomainError(403,"eng03_independent_database_identity_required")
        return con

    def claim(self,*,seconds=30):
        if type(seconds) is not int or not 1<=seconds<=300:
            raise DomainError(400,"invalid_lease_seconds")
        token=uuid.uuid4()
        with self._connect() as con:
            # Repeated process crashes must not lease forever. Expired third
            # lease is permanently DLQed before attempting a new claim.
            con.execute("""UPDATE abc.eng03_input_jobs SET
                 status='DLQ',lease_until=NULL,lease_token=NULL,
                 error_code='LEASE_RETRY_EXHAUSTED',
                 updated_at=clock_timestamp()
                 WHERE consumer_id=%s AND status='LEASED'
                   AND lease_until<=clock_timestamp() AND attempts>=3""",
                   (self.consumer_id,))
            row=con.execute("""WITH next AS (
                SELECT job_id FROM abc.eng03_input_jobs
                WHERE consumer_id=%s AND (
                    (status='QUEUED_PENDING_ENGINE' AND next_attempt_at<=clock_timestamp())
                   OR (status='LEASED' AND lease_until<=clock_timestamp()))
                ORDER BY updated_at,job_id
                FOR UPDATE SKIP LOCKED LIMIT 1
            )
            UPDATE abc.eng03_input_jobs job
               SET status='LEASED',attempts=attempts+1,
                   lease_token=%s,lease_until=clock_timestamp()+make_interval(secs=>%s),
                   updated_at=clock_timestamp()
            FROM next WHERE job.job_id=next.job_id
            RETURNING job.job_id,job.consumer_id,job.tenant_id,job.session_id,
                      job.source_event_id,job.lease_token,job.attempts""",
                (self.consumer_id,token,seconds)).fetchone()
            return {k:str(v) if isinstance(v,uuid.UUID) else v for k,v in row.items()} if row else None

    def _leased(self,con,job_id,token):
        row=con.execute("""SELECT * FROM abc.eng03_input_jobs
            WHERE job_id=%s AND consumer_id=%s FOR UPDATE""",
            (job_id,self.consumer_id)).fetchone()
        if row is None:
            raise DomainError(404,"job_not_found")
        now=con.execute("SELECT clock_timestamp() AS now").fetchone()["now"]
        if (row["status"]!="LEASED" or row["lease_token"]!=token
            or row["lease_until"] is None or row["lease_until"]<=now):
            raise DomainError(409,"stale_or_expired_lease")
        return row

    def _evidence(self,source):
        q=QUESTION.get(source.get("question_id"))
        if (not q or source.get("profile_version")!=REGISTRY["profile_version"]
            or source.get("policy_version")!="eng14.synthetic.1"
            or source.get("answer_source") not in ("CLIENT","SPECIALIST")
            or source.get("answer_value") not in q["allowed_values"]):
            raise DomainError(422,"untrusted_question_source")
        value=source["answer_value"]
        missing=value in ("UNKNOWN","UNSURE")
        evid=str(uuid.uuid5(uuid.NAMESPACE_URL,"abc:eng03:source:"+
                            source["answer_id"])) if missing else source["answer_id"]
        return {
            "evidence_id":evid,"session_id":source["session_id"],
            "service_id":"synthetic:hair-color","attribute_key":q["field"],
            "value":None if missing else value,
            "evidence_class":"UNKNOWN" if missing else "USER_REPORTED",
            "source_type":"NOT_AVAILABLE" if missing else
                ("CLIENT_ANSWER" if source["answer_source"]=="CLIENT" else "SALON_RECORD"),
            **({} if missing else {"source_id":source["answer_id"]}),
            "captured_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
            "criticality":"EXECUTION_REQUIRED" if q["critical"] else "RECOMMENDATION_REQUIRED",
            "confidence_label":"UNRATED"
        }

    def complete(self,job_id,lease_token):
        jid,token=_uuid(job_id),_uuid(lease_token)
        with self._connect() as con:
            job=self._leased(con,jid,token)
            row=con.execute("SELECT abc.eng03_source_for_lease(%s,%s) AS source",
                            (jid,token)).fetchone()
            source=row["source"]
            if (source["job_id"]!=str(jid)
                or source["session_id"]!=str(job["session_id"])
                or source["event_id"]!=str(job["source_event_id"])
                or source["tenant_id"]!=job["tenant_id"]
                or source["aggregate_version"]!=job["aggregate_version"]):
                raise DomainError(422,"eng03_source_scope_mismatch")
            evidence=self._evidence(source)
            if source["answer_id"]=="" or not source["policy_decision_id"]:
                raise DomainError(422,"missing_eng14_proof")
            digest=_json_digest(evidence)
            uid=uuid.uuid5(uuid.NAMESPACE_URL,
                   "abc:eng04-06:input:"+str(jid))
            con.execute("""INSERT INTO abc.eng03_evidence_ledger (
               evidence_id,consumer_id,source_job_id,source_event_id,
               source_answer_id,policy_decision_id,source_lease_token,tenant_id,branch_id,session_id,
               aggregate_version,question_id,source_kind,evidence_json,evidence_digest)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT DO NOTHING""",
               (uuid.UUID(evidence["evidence_id"]),job["consumer_id"],jid,
                job["source_event_id"],uuid.UUID(source["answer_id"]),
                uuid.UUID(source["policy_decision_id"]),token,job["tenant_id"],
                job["branch_id"],job["session_id"],job["aggregate_version"],
                source["question_id"],source["answer_source"],json.dumps(evidence),digest))
            con.execute("""INSERT INTO abc.eng04_06_jobs (
               job_id,consumer_id,source_job_id,source_evidence_id,
               tenant_id,branch_id,session_id,aggregate_version)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT DO NOTHING""",
                (uid,job["consumer_id"],jid,uuid.UUID(evidence["evidence_id"]),
                 job["tenant_id"],job["branch_id"],job["session_id"],job["aggregate_version"]))
            con.execute("""UPDATE abc.eng03_input_jobs
                  SET status='ACKED',lease_until=NULL,
                      updated_at=clock_timestamp(),error_code=NULL
                  WHERE job_id=%s""",(jid,))
            return {"job_id":str(jid),"status":"ACKED","evidence_id":evidence["evidence_id"],
                    "eng04_06_job_id":str(uid)}

    def fail(self,job_id,lease_token,code="PROCESSING_FAILED"):
        jid,token=_uuid(job_id),_uuid(lease_token)
        if not isinstance(code,str) or not _FAIL.fullmatch(code):
            raise DomainError(400,"invalid_failure_code")
        with self._connect() as con:
            row=self._leased(con,jid,token)
            status="DLQ" if row["attempts"]>=3 else "QUEUED_PENDING_ENGINE"
            con.execute("""UPDATE abc.eng03_input_jobs
                SET status=%s,lease_until=NULL,lease_token=NULL,error_code=%s,
                    next_attempt_at=clock_timestamp()+make_interval(secs=>%s),
                    updated_at=clock_timestamp()
                WHERE job_id=%s""",
                (status,code,min(60,2**row["attempts"]),jid))
            return status

    def run_once(self):
        job=self.claim()
        if not job:
            return None
        try:
            self.complete(job["job_id"],job["lease_token"])
        except DomainError:
            self.fail(job["job_id"],job["lease_token"],"ENG03_SOURCE_REJECTED")
            return "REJECTED"
        # Database outage not ACKed: lease eventually expires for retry.
        return "ACKED"

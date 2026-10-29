"""Distinct ENG04/05/06 PostgreSQL pipeline consumer (synthetic sources only).

No model or professional safety authority. Read only source-bound ENG03
evidence; no ENG02 table access, no photos or client information. Persisted
analysis/knowledge/decision results and lease ACK share one transaction.
"""
import hashlib
import json
import uuid
from datetime import datetime,timezone
import psycopg
from psycopg.rows import dict_row

from .eng02_consultation import SYNTHETIC_SERVICE,FIXTURE_PATH
from .eng03_executor import _json_digest,_uuid
from .eng04_analysis import SyntheticBeautyAnalysis,FIELDS
from .eng05_knowledge import SyntheticKnowledgeEngine
from .eng06_decision import SyntheticDecisionEngine
from .store import DomainError
from .pg_outbox import CONSUMER

QUESTION_REGISTRY=json.loads(FIXTURE_PATH.read_text())["profiles"][0]
_BY_FIELD={q["field"]:q for q in QUESTION_REGISTRY["questions"]}


class SyntheticAnalysisPipeline:
    ENGINE_IDS=("ENG-04","ENG-05","ENG-06")
    def __init__(self,dsn,consumer_id,*,knowledge_fixture=None,engine_runner=None):
        if not isinstance(dsn,str) or not dsn:
            raise ValueError("independent_analysis_database_dsn_required")
        if not isinstance(consumer_id,str) or not CONSUMER.fullmatch(consumer_id):
            raise ValueError("bound_analysis_consumer_required")
        self.dsn=dsn
        self.consumer_id=consumer_id
        self.fixture=knowledge_fixture
        if engine_runner is not None and not callable(getattr(engine_runner,"call",None)):
            raise ValueError("trusted_engine_transport_required")
        self.engine_runner=engine_runner
        # The knowledge engine independently rejects any unreviewed source.
        if knowledge_fixture is not None:
            SyntheticKnowledgeEngine().resolve(service_id=SYNTHETIC_SERVICE,
                                              fixture=knowledge_fixture)

    def _connect(self):
        con=psycopg.connect(self.dsn,row_factory=dict_row,connect_timeout=4)
        try:
            principal=con.execute(
                "SELECT current_user AS actual_login, session_user AS verified_login"
            ).fetchone()
            # Shared engine group identities are NOLOGIN in migration 0013.
            # Never trust an asserted consumer or a caller-owned custom GUC.
            if (principal["actual_login"]!=principal["verified_login"]
                or principal["verified_login"]=="abc_pipeline_worker"):
                raise DomainError(403,"unscoped_workload_database_identity")
            con.execute("SET ROLE abc_pipeline_worker")
            permitted=con.execute("""SELECT 1 FROM abc.worker_login_bindings
                WHERE login_name=session_user AND worker_role=current_user
                  AND consumer_id=%s AND active=true""",
                (self.consumer_id,)).fetchone()
            if permitted is None:
                raise DomainError(403,"consumer_login_binding_denied")
            bound=con.execute("""SELECT 1 FROM abc.eng03_worker_bindings b
                JOIN abc.worker_login_bindings login
                  ON login.consumer_id=b.consumer_id
                 AND login.tenant_id=b.tenant_id
                 AND login.worker_role=b.worker_role
                WHERE login.login_name=session_user AND login.active
                  AND b.worker_role=current_user AND b.active
                  AND b.consumer_id=%s""",
                (self.consumer_id,)).fetchone()
            if bound is None:
                raise DomainError(403,"consumer_binding_revoked")
            return con
        except BaseException:
            con.close()
            raise

    def claim(self,*,seconds=30):
        if type(seconds) is not int or not 1<=seconds<=300:
            raise DomainError(400,"invalid_lease_seconds")
        token=uuid.uuid4()
        with self._connect() as con:
            con.execute("""UPDATE abc.eng04_06_jobs SET
                status='DLQ',lease_until=NULL,lease_token=NULL,
                error_code='LEASE_RETRY_EXHAUSTED',
                updated_at=clock_timestamp()
                WHERE consumer_id=%s AND status='LEASED'
                  AND lease_until<=clock_timestamp() AND attempts>=3""",
                (self.consumer_id,))
            item=con.execute("""WITH chosen AS (
                SELECT job_id FROM abc.eng04_06_jobs
                WHERE consumer_id=%s AND attempts<3 AND (
                      (status='QUEUED' AND next_attempt_at<=clock_timestamp())
                   OR (status='LEASED' AND lease_until<=clock_timestamp()))
                ORDER BY updated_at,job_id FOR UPDATE SKIP LOCKED LIMIT 1
            )
            UPDATE abc.eng04_06_jobs job
                SET status='LEASED',attempts=attempts+1,lease_token=%s,
                    lease_until=clock_timestamp()+make_interval(secs=>%s),
                    updated_at=clock_timestamp()
            FROM chosen WHERE chosen.job_id=job.job_id
            RETURNING job.job_id,job.lease_token,job.consumer_id,job.tenant_id,
                      job.session_id,job.aggregate_version,job.source_evidence_id""",
                (self.consumer_id,token,seconds)).fetchone()
            return {k:str(v) if isinstance(v,uuid.UUID) else v for k,v in item.items()} if item else None

    def _leased(self,con,job_id,token):
        row=con.execute("""SELECT * FROM abc.eng04_06_jobs
                      WHERE job_id=%s AND consumer_id=%s FOR UPDATE""",
                    (job_id,self.consumer_id)).fetchone()
        if row is None:
            raise DomainError(404,"analysis_job_not_found")
        now=con.execute("SELECT clock_timestamp() AS now").fetchone()["now"]
        if (row["status"]!="LEASED" or row["lease_token"]!=token
            or row["lease_until"] is None or row["lease_until"]<=now):
            raise DomainError(409,"stale_or_expired_analysis_lease")
        return row

    def _snapshot(self,con,job):
        rows=con.execute("""SELECT evidence_id,evidence_json,evidence_digest,
                    aggregate_version,source_job_id,
                    policy_decision_id,question_id,tenant_id,branch_id,session_id
               FROM abc.eng03_evidence_ledger
               WHERE consumer_id=%s AND tenant_id=%s AND branch_id=%s
                 AND session_id=%s AND aggregate_version<=%s
               ORDER BY aggregate_version""",
               (job["consumer_id"],job["tenant_id"],job["branch_id"],
                job["session_id"],job["aggregate_version"])).fetchall()
        if not rows:
            raise DomainError(422,"missing_provenance_bound_evidence")
        items={}
        sid=str(job["session_id"])
        for row in rows:
            ev=row["evidence_json"]
            if (not isinstance(ev,dict)
                or _json_digest(ev)!=row["evidence_digest"]
                or ev.get("session_id")!=sid
                or ev.get("service_id")!=SYNTHETIC_SERVICE
                or ev.get("evidence_id")!=str(row["evidence_id"])
                or not row["policy_decision_id"]
                or row["question_id"] not in [q["question_id"] for q in _BY_FIELD.values()]
                or ev.get("attribute_key") not in FIELDS
                or _BY_FIELD[ev["attribute_key"]]["question_id"]!=row["question_id"]):
                raise DomainError(422,"evidence_lineage_or_digest_invalid")
            if ev["attribute_key"] in items:
                raise DomainError(422,"duplicate_evidence_field")
            items[ev["attribute_key"]]=ev
        anchor=next((r for r in rows if r["evidence_id"]==job["source_evidence_id"]),None)
        if anchor is None or anchor["aggregate_version"]!=job["aggregate_version"]:
            raise DomainError(422,"pipeline_job_source_mismatch")
        # Explicitly NOT derived from an image/model: missing questions are
        # represented by UNKNOWN, never guessed from another answer.
        for field,q in _BY_FIELD.items():
            if field not in items:
                items[field]={
                    "evidence_id":str(uuid.uuid5(uuid.NAMESPACE_URL,
                        "abc:eng03:missing:"+sid+":"+field+":"+str(job["aggregate_version"]))),
                    "session_id":sid,"service_id":SYNTHETIC_SERVICE,
                    "attribute_key":field,"value":None,
                    "evidence_class":"UNKNOWN","source_type":"NOT_AVAILABLE",
                    "captured_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
                    "criticality":"EXECUTION_REQUIRED" if q["critical"] else "RECOMMENDATION_REQUIRED",
                    "confidence_label":"UNRATED"
                }
        return [items[k] for k in sorted(items)],rows

    def complete(self,job_id,lease_token):
        jid,token=_uuid(job_id),_uuid(lease_token)
        with self._connect() as con:
            job=self._leased(con,jid,token)
            evidence,rows=self._snapshot(con,job)
            sid=str(job["session_id"])
            # Each engine runs in its own child OS process with strict
            # versioned port; the database-capable pipeline remains the only
            # owner of the transaction and never forwards its PG credentials.
            from .isolated_engine_runner import IsolatedEngineRunner
            runner=self.engine_runner or IsolatedEngineRunner()
            consumer=job["consumer_id"]
            analysis=runner.call("ENG-04",consumer_id=consumer,session_id=sid,
                                 payload={"evidence":evidence})
            knowledge=runner.call("ENG-05",consumer_id=consumer,session_id=sid,
                                  payload={"service_id":SYNTHETIC_SERVICE,"fixture":self.fixture})
            decision=runner.call("ENG-06",consumer_id=consumer,session_id=sid,
                                 payload={"analysis":analysis,"knowledge":knowledge})
            if (analysis["session_id"]!=sid or decision["session_id"]!=sid
                or decision["service_id"]!=SYNTHETIC_SERVICE
                or any(c.get("feasibility_label")!="PROFESSIONAL_CHECK_REQUIRED"
                    for c in decision["candidates"])):
                raise DomainError(422,"eng14_synthetic_decision_boundary")
            digest=_json_digest([(str(row["evidence_id"]),row["evidence_digest"],
                                  row["aggregate_version"]) for row in rows])
            result_id=uuid.uuid5(uuid.NAMESPACE_URL,"abc:synthetic:pipeline:"+str(jid))
            con.execute("""INSERT INTO abc.eng04_06_results
                    (result_id,consumer_id,source_pipeline_job_id,tenant_id,branch_id,
                     session_id,aggregate_version,source_evidence_digest,
                     analysis_json,knowledge_json,decision_json,policy_version)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'eng14.synthetic.1')
                    ON CONFLICT DO NOTHING""",
                    (result_id,job["consumer_id"],jid,job["tenant_id"],job["branch_id"],
                     job["session_id"],job["aggregate_version"],digest,
                     json.dumps(analysis),json.dumps(knowledge),json.dumps(decision)))
            con.execute("""UPDATE abc.eng04_06_jobs SET status='ACKED',
                      lease_until=NULL,error_code=NULL,updated_at=clock_timestamp()
                      WHERE job_id=%s""",(jid,))
            return {"job_id":str(jid),"status":"ACKED",
                    "analysis_id":analysis["analysis_id"],
                    "candidate_count":len(decision["candidates"]),
                    "safety_review_required":True}

    def fail(self,job_id,lease_token,code="ANALYSIS_REJECTED"):
        jid,token=_uuid(job_id),_uuid(lease_token)
        if not isinstance(code,str) or not code.isupper() or len(code)>64:
            raise DomainError(400,"invalid_failure_code")
        with self._connect() as con:
            job=self._leased(con,jid,token)
            state="DLQ" if job["attempts"]>=3 else "QUEUED"
            con.execute("""UPDATE abc.eng04_06_jobs
              SET status=%s,lease_until=NULL,lease_token=NULL,error_code=%s,
                  next_attempt_at=clock_timestamp()+make_interval(secs=>%s),
                  updated_at=clock_timestamp() WHERE job_id=%s""",
                (state,code,min(60,2**job["attempts"]),jid))
            return state

    def run_once(self):
        job=self.claim()
        if not job: return None
        try:
            self.complete(job["job_id"],job["lease_token"])
        except DomainError:
            self.fail(job["job_id"],job["lease_token"])
            return "REJECTED"
        return "ACKED"

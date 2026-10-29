"""Dedicated synthetic ANSWER_RECORDED read-model worker.

Uses abc_answer_worker only, distinct from abc_worker, abc_app and abc_orchestrator.
Reads only admin-authorized tenant subscription, stores IDs/versions but no
answer values, images, client identity, diagnosis or inferred result.
"""
from datetime import datetime
import uuid
import psycopg
from psycopg.rows import dict_row

from .pg_outbox import OutboxDispatcher
from .store import DomainError

def _uuid(value):
    try:
        item=uuid.UUID(value)
        if str(item)!=value:
            raise ValueError()
        return item
    except (ValueError, TypeError, AttributeError):
        raise DomainError(422,"invalid_answer_event_uuid") from None


class AnswerDispatcher(OutboxDispatcher):
    def __init__(self,dsn,consumer_id):
        super().__init__(dsn)
        self._consumer(consumer_id)
        self.consumer_id=consumer_id

    def _connect(self):
        con=psycopg.connect(self.dsn,row_factory=dict_row,connect_timeout=4)
        try:
            role=con.execute("SELECT current_user AS role").fetchone()["role"]
            if role!="abc_answer_worker":
                raise DomainError(403,"dedicated_answer_worker_role_required")
            # Per-connection authorization context, not a client-supplied ID.
            # RLS checks this AND admin provisioning / event type / tenant.
            con.execute("SELECT set_config('abc.consumer_id',%s,false)",(self.consumer_id,))
            return con
        except BaseException:
            con.close()
            raise


class AnswerIndexConsumer:
    def __init__(self,dsn,consumer_id):
        self.dispatcher=AnswerDispatcher(dsn,consumer_id)
        self.consumer_id=consumer_id
        self.dsn=dsn

    def project(self,delivery):
        event=delivery.get("event")
        if not isinstance(event,dict) or event.get("event_type")!="ANSWER_RECORDED":
            raise DomainError(422,"unexpected_answer_event")
        if event.get("event_schema_version")!="1.0.0-draft" or event.get("producer_engine_id")!="ENG-02":
            raise DomainError(422,"unsupported_answer_producer")
        if type(event.get("aggregate_version")) is not int or event["aggregate_version"]<1:
            raise DomainError(422,"unsupported_answer_aggregate_version")
        payload=event.get("payload")
        if not isinstance(payload,dict) or set(payload)!={"question_id","session_id","answer_id"}:
            raise DomainError(422,"invalid_answer_payload")
        sid=_uuid(event.get("session_id"))
        eid=_uuid(event.get("event_id"))
        agg=_uuid(event.get("aggregate_id"))
        aid=_uuid(payload.get("answer_id"))
        if sid!=agg or str(sid)!=payload.get("session_id") or str(eid)!=delivery.get("event_id"):
            raise DomainError(422,"answer_event_aggregate_mismatch")
        if event.get("tenant_id")!=delivery.get("tenant_id") or delivery.get("consumer_id")!=self.consumer_id:
            raise DomainError(422,"answer_event_scope_mismatch")
        tenant,branch,qid=event.get("tenant_id"),event.get("branch_id"),payload.get("question_id")
        if any(not isinstance(v,str) or not 1<=len(v)<=128 for v in (tenant,branch,qid)):
            raise DomainError(422,"invalid_answer_event_scope")
        if not qid.startswith("synthetic:") or event.get("actor",{}).get("role")!="SPECIALIST":
            raise DomainError(422,"non_synthetic_answer_denied")
        # A projection may be written twice after a crash-before-ACK; database
        # uniqueness ensures one row. Do not mutate any ENG03/04/05/06 state.
        with self.dispatcher._connect() as con:
            con.execute("""INSERT INTO abc.answer_index_projection
                (consumer_id,event_id,tenant_id,branch_id,session_id,
                 aggregate_version,question_id,answer_id)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT DO NOTHING""",
                (self.consumer_id,eid,tenant,branch,sid,
                 event["aggregate_version"],qid,aid))
        return str(eid)

    def run_once(self):
        self.dispatcher.register(self.consumer_id)
        delivery=self.dispatcher.lease(self.consumer_id)
        if delivery is None:
            return None
        try:
            self.project(delivery)
        except DomainError:
            self.dispatcher.complete(self.consumer_id,delivery["event_id"],
                 delivery["lease_token"],succeeded=False,failure_code="INVALID_ANSWER_EVENT")
            return "REJECTED"
        # Transient DB/network failures intentionally leave the lease un-ACKed.
        self.dispatcher.complete(self.consumer_id,delivery["event_id"],
                                 delivery["lease_token"],succeeded=True)
        return "PROJECTED"

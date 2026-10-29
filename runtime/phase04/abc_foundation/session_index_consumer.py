"""Independent internal ENG-01 SESSION_CREATED projection consumer.

The only executable business effect is an idempotent non-PII read model.
Never marks a customer booking, payment, visual job or consent successful.
"""
import uuid
import psycopg

from .pg_outbox import OutboxDispatcher
from .store import DomainError


def _uuid(value):
    try:
        return uuid.UUID(str(value))
    except (TypeError,ValueError,AttributeError):
        raise DomainError(422,"invalid_event_uuid") from None


class SessionIndexConsumer:
    def __init__(self, worker_dsn, consumer_id):
        self.dispatcher=OutboxDispatcher(worker_dsn)
        self.dsn=worker_dsn
        self.consumer_id=consumer_id
        self.dispatcher._consumer(consumer_id)

    def project(self, delivery):
        """Effect persists atomically; separate ACK may be replayed after a crash."""
        e=delivery.get("event")
        if not isinstance(e,dict) or e.get("event_type")!="SESSION_CREATED":
            raise DomainError(422,"unsupported_event")
        if e.get("event_schema_version")!="1.0.0-draft" or e.get("aggregate_version")!=0:
            raise DomainError(422,"unsupported_event_version")
        p=e.get("payload")
        if not isinstance(p,dict) or set(p)!={"session_id","branch_id"}:
            raise DomainError(422,"invalid_session_event_payload")
        sid=_uuid(e.get("session_id"))
        eid=_uuid(e.get("event_id"))
        agg=_uuid(e.get("aggregate_id"))
        if (agg!=sid or str(sid)!=str(p.get("session_id"))
                or str(eid)!=str(delivery.get("event_id"))
                or e.get("tenant_id")!=delivery.get("tenant_id")
                or e.get("branch_id")!=p.get("branch_id")
                or delivery.get("consumer_id")!=self.consumer_id):
            raise DomainError(422,"event_envelope_mismatch")
        branch=p["branch_id"]
        tenant=e["tenant_id"]
        if not all(isinstance(v,str) and 0<len(v)<=128 for v in (branch,tenant)):
            raise DomainError(422,"invalid_event_scope")
        # PostgreSQL RLS enforces the admin-provisioned consumer/tenant mapping.
        with psycopg.connect(self.dsn,connect_timeout=4) as con:
            con.execute("""
                INSERT INTO abc.session_index_projection
                    (consumer_id,event_id,tenant_id,branch_id,session_id)
                VALUES(%s,%s,%s,%s,%s)
                ON CONFLICT DO NOTHING
            """,(self.consumer_id,eid,tenant,branch,sid))
        return str(sid)

    def run_once(self):
        """Reconcile arrivals, lease one and ACK only *after* durable projection."""
        self.dispatcher.register(self.consumer_id)
        item=self.dispatcher.lease(self.consumer_id)
        if item is None:
            return None
        try:
            self.project(item)
        except DomainError:
            self.dispatcher.complete(self.consumer_id,item["event_id"],
                                     item["lease_token"],succeeded=False,
                                     failure_code="INVALID_EVENT")
            return "REJECTED"
        # Unknown transient SQL/network exception leaves lease unacknowledged:
        # another worker may retry after expiration; unique event_id prevents duplicates.
        self.dispatcher.complete(self.consumer_id,item["event_id"],
                                 item["lease_token"],succeeded=True)
        return "PROJECTED"

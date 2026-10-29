"""Separate PostgreSQL outbox dispatcher with durable at-least-once delivery.

This is a worker-side library, not HTTP. ACK only after downstream effect succeeds.
External consumers must also deduplicate by consumer_id:event_id; ACK cannot give
exactly-once external side effects across system boundaries.
"""
import re
import uuid
import psycopg
from psycopg.rows import dict_row

from .store import DomainError

CONSUMER = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
FAILURE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")


class OutboxDispatcher:
    def __init__(self, dsn):
        if not isinstance(dsn, str) or not dsn:
            raise ValueError("independent worker PostgreSQL DSN required")
        self.dsn = dsn

    def _connect(self):
        return psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=4)

    @staticmethod
    def _consumer(value):
        if not isinstance(value, str) or not CONSUMER.fullmatch(value):
            raise DomainError(400, "invalid_consumer")

    def register(self, consumer_id):
        """Idempotent reconcile of SESSION_CREATED events, including late arrivals.

        The source event is in the same transaction as session creation; periodic
        registration fills delivery rows even after an interrupted worker.
        """
        self._consumer(consumer_id)
        with self._connect() as con:
            scope = con.execute("""
                SELECT tenant_id,event_type FROM abc.worker_subscriptions
                WHERE consumer_id=%s AND active=true
            """,(consumer_id,)).fetchone()
            if scope is None:
                raise DomainError(403,"consumer_not_provisioned")
            cursor = con.execute("""
                INSERT INTO abc.event_delivery(consumer_id,event_id,tenant_id)
                SELECT %s, event_id, tenant_id FROM abc.outbox
                WHERE tenant_id=%s AND event_json->>'event_type'=%s
                ON CONFLICT(consumer_id,event_id) DO NOTHING
            """, (consumer_id,scope["tenant_id"],scope["event_type"]))
            return cursor.rowcount

    def lease(self, consumer_id, *, seconds=30):
        self._consumer(consumer_id)
        if type(seconds) is not int or not 1 <= seconds <= 300:
            raise DomainError(400, "invalid_lease_duration")
        token = uuid.uuid4()
        with self._connect() as con:
            allowed = con.execute("""
                SELECT 1 FROM abc.worker_subscriptions
                WHERE consumer_id=%s AND active=true
            """,(consumer_id,)).fetchone()
            if allowed is None:
                raise DomainError(403,"consumer_not_provisioned")
            item = con.execute("""
                WITH claimed AS (
                  SELECT event_id FROM abc.event_delivery
                  WHERE consumer_id=%s AND (
                     (state='PENDING' AND next_attempt_at <= clock_timestamp()) OR
                     (state='LEASED' AND lease_until <= clock_timestamp()))
                  ORDER BY updated_at,event_id
                  FOR UPDATE SKIP LOCKED LIMIT 1
                )
                UPDATE abc.event_delivery d SET
                   state='LEASED', attempts=attempts+1, lease_token=%s,
                   lease_until=clock_timestamp()+make_interval(secs => %s),
                   updated_at=clock_timestamp()
                FROM claimed WHERE d.consumer_id=%s AND d.event_id=claimed.event_id
                RETURNING d.event_id,d.attempts,d.lease_token,d.tenant_id
            """, (consumer_id,token,seconds,consumer_id)).fetchone()
            if item is None:
                return None
            event = con.execute("SELECT event_json FROM abc.outbox WHERE event_id=%s",
                                (item["event_id"],)).fetchone()
            if event is None:
                raise DomainError(409, "outbox_event_missing")
            return {"consumer_id": consumer_id,
                    "event_id": str(item["event_id"]),
                    "lease_token": str(item["lease_token"]),
                    "attempt": item["attempts"],
                    "tenant_id": item["tenant_id"],
                    "event": event["event_json"]}

    def complete(self, consumer_id, event_id, lease_token, *, succeeded, failure_code="PROCESSING_FAILED"):
        self._consumer(consumer_id)
        if type(succeeded) is not bool:
            raise DomainError(400, "invalid_completion")
        if not isinstance(failure_code,str) or not FAILURE.fullmatch(failure_code):
            raise DomainError(400, "invalid_failure_code")
        try:
            event_uuid, token_uuid = uuid.UUID(event_id), uuid.UUID(lease_token)
        except (TypeError, ValueError):
            raise DomainError(400, "invalid_delivery_token") from None
        with self._connect() as con:
            allowed = con.execute("""
                SELECT 1 FROM abc.worker_subscriptions
                WHERE consumer_id=%s AND active=true
            """,(consumer_id,)).fetchone()
            if allowed is None:
                raise DomainError(403,"consumer_not_provisioned")
            record = con.execute("""
                SELECT state,attempts,lease_token,lease_until FROM abc.event_delivery
                WHERE consumer_id=%s AND event_id=%s FOR UPDATE
            """, (consumer_id,event_uuid)).fetchone()
            if record is None:
                raise DomainError(404, "delivery_not_found")
            if record["state"] == "ACKED" and record["lease_token"] == token_uuid and succeeded:
                return "ACKED"
            if record["state"] != "LEASED" or record["lease_token"] != token_uuid:
                raise DomainError(409, "stale_delivery_token")
            now = con.execute("SELECT clock_timestamp() AS now").fetchone()["now"]
            if record["lease_until"] <= now:
                raise DomainError(409, "lease_expired")
            if succeeded:
                state, code = "ACKED", None
                con.execute("""
                    UPDATE abc.event_delivery SET state='ACKED',lease_until=NULL,
                      error_code=NULL,updated_at=clock_timestamp()
                    WHERE consumer_id=%s AND event_id=%s
                """, (consumer_id,event_uuid))
            else:
                state="DLQ" if record["attempts"] >= 3 else "PENDING"
                code = failure_code
                # Bound retry interval; dead-letter after third failed processing.
                con.execute("""
                    UPDATE abc.event_delivery SET state=%s,lease_token=NULL,lease_until=NULL,
                      next_attempt_at=clock_timestamp()+make_interval(secs => %s),
                      error_code=%s,updated_at=clock_timestamp()
                    WHERE consumer_id=%s AND event_id=%s
                """, (state, min(60, 2 ** record["attempts"]), code, consumer_id,event_uuid))
            return state

"""SQLite-backed Phase-04 foundation slice (no client media, no real consent)."""
import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone


class DomainError(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code
        super().__init__(code)


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _nonempty(value):
    return isinstance(value, str) and 0 < len(value) <= 128 and value.strip() == value


class Store:
    def __init__(self, db_path):
        self.path = str(db_path)
        self.initialize()

    def connect(self):
        con = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA busy_timeout=10000")
        return con

    def initialize(self):
        con = self.connect()
        try:
            con.execute("PRAGMA journal_mode=WAL")
            con.executescript("""
                CREATE TABLE IF NOT EXISTS sessions(
                  session_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, branch_id TEXT NOT NULL,
                  specialist_id TEXT NOT NULL, client_id TEXT, appointment_id TEXT, service_id TEXT,
                  state TEXT NOT NULL CHECK(state IN ('CREATED','PAUSED')),
                  state_version INTEGER NOT NULL CHECK(state_version >= 0),
                  checkpoint TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                  last_event_id TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS sessions_scope ON sessions(tenant_id, branch_id);
                CREATE TABLE IF NOT EXISTS idempotency(
                  tenant_id TEXT NOT NULL, actor_id TEXT NOT NULL, operation TEXT NOT NULL,
                  request_key TEXT NOT NULL, fingerprint TEXT NOT NULL, response_json TEXT NOT NULL,
                  PRIMARY KEY(tenant_id, actor_id, operation, request_key)
                );
                CREATE TABLE IF NOT EXISTS state_audit(
                  audit_id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(session_id),
                  from_state TEXT, to_state TEXT NOT NULL, from_version INTEGER, to_version INTEGER NOT NULL,
                  actor_id TEXT NOT NULL, occurred_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS outbox(
                  event_id TEXT PRIMARY KEY, aggregate_id TEXT NOT NULL, aggregate_version INTEGER NOT NULL,
                  event_json TEXT NOT NULL, created_at TEXT NOT NULL,
                  UNIQUE(aggregate_id, aggregate_version)
                );
                CREATE TABLE IF NOT EXISTS consumer_acks(
                  consumer_id TEXT NOT NULL, event_id TEXT NOT NULL REFERENCES outbox(event_id),
                  acknowledged_at TEXT NOT NULL, PRIMARY KEY(consumer_id, event_id)
                );
                CREATE TABLE IF NOT EXISTS fixture_jobs(
                  job_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, session_id TEXT NOT NULL REFERENCES sessions(session_id),
                  status TEXT NOT NULL CHECK(status IN ('QUEUED','LEASED','SUCCEEDED','CANCELLED','DEAD_LETTER')),
                  attempts INTEGER NOT NULL DEFAULT 0, leased_by TEXT, lease_until REAL,
                  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS fixture_jobs_ready ON fixture_jobs(status,lease_until);
            """)
        finally:
            con.close()

    @staticmethod
    def _public(row):
        fields = ("session_id", "tenant_id", "branch_id", "specialist_id",
                  "client_id", "appointment_id", "service_id", "state", "state_version",
                  "created_at", "updated_at", "last_event_id")
        result = {field: row[field] for field in fields if row[field] is not None}
        result["scope"] = "IN_SALON_SHARED_SCREEN"
        return result

    @staticmethod
    def _authorize(actor, row):
        # No difference in returned status between missing and cross-tenant resources.
        if row is None or row["tenant_id"] != actor["tenant_id"] or row["branch_id"] not in actor["branch_ids"] or row["specialist_id"] != actor["sub"]:
            raise DomainError(404, "not_found")

    @staticmethod
    def _key(key):
        if not isinstance(key, str) or not 8 <= len(key) <= 128 or not all(c.isalnum() or c in "-_." for c in key):
            raise DomainError(400, "invalid_idempotency_key")

    def _replay(self, con, actor, operation, key, request):
        fingerprint = _fingerprint(request)
        row = con.execute(
            "SELECT fingerprint,response_json FROM idempotency WHERE tenant_id=? AND actor_id=? AND operation=? AND request_key=?",
            (actor["tenant_id"], actor["sub"], operation, key)).fetchone()
        if row:
            if row["fingerprint"] != fingerprint:
                raise DomainError(409, "idempotency_payload_conflict")
            return json.loads(row["response_json"]), fingerprint
        return None, fingerprint

    def _remember(self, con, actor, operation, key, fingerprint, response):
        con.execute(
            "INSERT INTO idempotency(tenant_id,actor_id,operation,request_key,fingerprint,response_json) VALUES(?,?,?,?,?,?)",
            (actor["tenant_id"], actor["sub"], operation, key, fingerprint,
             json.dumps(response, separators=(",", ":"), sort_keys=True)))

    def create(self, actor, body, key):
        self._key(key)
        if not isinstance(body, dict) or not body or set(body) - {"branch_id", "scope", "client_id", "appointment_id", "service_id"}:
            raise DomainError(400, "invalid_create_request")
        if body.get("scope") != "IN_SALON_SHARED_SCREEN" or not _nonempty(body.get("branch_id")):
            raise DomainError(400, "invalid_session_scope")
        if any(not _nonempty(v) for k, v in body.items() if k in ("client_id", "appointment_id", "service_id")):
            raise DomainError(400, "invalid_field")
        if body["branch_id"] not in actor["branch_ids"]:
            raise DomainError(403, "branch_forbidden")
        con = self.connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            existing, digest = self._replay(con, actor, "create", key, body)
            if existing is not None:
                con.execute("COMMIT")
                return existing
            sid, eid, now = str(uuid.uuid4()), str(uuid.uuid4()), _now()
            con.execute("""INSERT INTO sessions(session_id,tenant_id,branch_id,specialist_id,client_id,appointment_id,service_id,state,state_version,checkpoint,created_at,updated_at,last_event_id)
                         VALUES(?,?,?,?,?,?,?,'CREATED',0,NULL,?,?,?)""",
                        (sid, actor["tenant_id"], body["branch_id"], actor["sub"], body.get("client_id"),
                         body.get("appointment_id"), body.get("service_id"), now, now, eid))
            row = con.execute("SELECT * FROM sessions WHERE session_id=?", (sid,)).fetchone()
            response = self._public(row)
            envelope = {
                "event_id": eid, "event_type": "SESSION_CREATED", "event_schema_version": "1.0.0-draft",
                "tenant_id": actor["tenant_id"], "branch_id": body["branch_id"], "session_id": sid,
                "aggregate_id": sid, "aggregate_version": 0, "occurred_at": now,
                "correlation_id": sid, "actor": {"user_id": actor["sub"], "role": "SPECIALIST"},
                "payload": {"session_id": sid, "branch_id": body["branch_id"]},
                "producer_engine_id": "ENG-01", "trace_id": str(uuid.uuid4())
            }
            con.execute("INSERT INTO outbox(event_id,aggregate_id,aggregate_version,event_json,created_at) VALUES(?,?,?,?,?)",
                        (eid, sid, 0, json.dumps(envelope, separators=(",", ":")), now))
            con.execute("INSERT INTO state_audit VALUES(?,?,?,?,?,?,?,?)",
                        (str(uuid.uuid4()), sid, None, "CREATED", None, 0, actor["sub"], now))
            self._remember(con, actor, "create", key, digest, response)
            con.execute("COMMIT")
            return response
        except Exception:
            if con.in_transaction:
                con.execute("ROLLBACK")
            raise
        finally:
            con.close()

    def get(self, actor, session_id):
        con = self.connect()
        try:
            row = con.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone()
            self._authorize(actor, row)
            return self._public(row)
        finally:
            con.close()

    def checkpoint_command(self, actor, sid, action, expected_version, key):
        """Foundation-internal v0 route, not an accepted /v1 operation."""
        self._key(key)
        if type(expected_version) is not int or expected_version < 0:
            raise DomainError(400, "invalid_expected_version")
        if action not in ("pause", "resume"):
            raise DomainError(400, "invalid_action")
        op = action + ":" + sid
        request = {"session_id": sid, "action": action, "expected_state_version": expected_version}
        con = self.connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            # Authorize before replay, so replay never leaks after actor loses scope.
            row = con.execute("SELECT * FROM sessions WHERE session_id=?", (sid,)).fetchone()
            self._authorize(actor, row)
            prior, digest = self._replay(con, actor, op, key, request)
            if prior is not None:
                con.execute("COMMIT")
                return prior
            if row["state_version"] != expected_version:
                raise DomainError(409, "state_version_conflict")
            if action == "pause":
                if row["state"] != "CREATED":
                    raise DomainError(409, "invalid_transition")
                state, checkpoint = "PAUSED", "CREATED"
            else:
                if row["state"] != "PAUSED" or row["checkpoint"] != "CREATED":
                    raise DomainError(409, "missing_or_invalid_checkpoint")
                state, checkpoint = "CREATED", None
            now = _now()
            con.execute("UPDATE sessions SET state=?,checkpoint=?,state_version=?,updated_at=? WHERE session_id=? AND state_version=?",
                        (state, checkpoint, expected_version + 1, now, sid, expected_version))
            if con.execute("SELECT changes()").fetchone()[0] != 1:
                raise DomainError(409, "state_version_conflict")
            if action == "pause":
                # Atomically fence outstanding synthetic workers against late completion.
                con.execute("""UPDATE fixture_jobs SET status='CANCELLED',leased_by=NULL,lease_until=NULL,
                             updated_at=? WHERE session_id=? AND status IN ('QUEUED','LEASED')""", (now, sid))
            con.execute("INSERT INTO state_audit VALUES(?,?,?,?,?,?,?,?)",
                        (str(uuid.uuid4()), sid, row["state"], state, expected_version,
                         expected_version + 1, actor["sub"], now))
            response = self._public(con.execute("SELECT * FROM sessions WHERE session_id=?", (sid,)).fetchone())
            self._remember(con, actor, op, key, digest, response)
            con.execute("COMMIT")
            return response
        except Exception:
            if con.in_transaction:
                con.execute("ROLLBACK")
            raise
        finally:
            con.close()

    def pending_outbox(self, consumer_id):
        """Read-only test fixture; real consumer delivery, retry policy and DLQ not yet built."""
        if not _nonempty(consumer_id):
            raise DomainError(400, "invalid_consumer")
        con = self.connect()
        try:
            rows = con.execute("""SELECT event_json FROM outbox WHERE event_id NOT IN
                            (SELECT event_id FROM consumer_acks WHERE consumer_id=?)
                            ORDER BY created_at, event_id""", (consumer_id,)).fetchall()
            return [json.loads(x[0]) for x in rows]
        finally:
            con.close()

    def ack_outbox(self, consumer_id, event_id):
        if not _nonempty(consumer_id) or not _nonempty(event_id):
            raise DomainError(400, "invalid_consumer_or_event")
        con = self.connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            if not con.execute("SELECT 1 FROM outbox WHERE event_id=?", (event_id,)).fetchone():
                raise DomainError(404, "event_not_found")
            con.execute("INSERT OR IGNORE INTO consumer_acks VALUES(?,?,?)", (consumer_id, event_id, _now()))
            con.execute("COMMIT")
        except Exception:
            if con.in_transaction:
                con.execute("ROLLBACK")
            raise
        finally:
            con.close()


    def enqueue_fixture_job(self, actor, sid, key):
        """Synthetic scheduling fixture; never image processing or a real engine."""
        self._key(key)
        op, request = "fixture-job:" + sid, {"session_id": sid, "kind": "NO_MEDIA_TEST_FIXTURE"}
        con = self.connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM sessions WHERE session_id=?", (sid,)).fetchone()
            self._authorize(actor, row)
            if row["state"] != "CREATED":
                raise DomainError(409, "session_not_runnable")
            previous, digest = self._replay(con, actor, op, key, request)
            if previous is not None:
                con.execute("COMMIT")
                return previous
            job_id, now = str(uuid.uuid4()), _now()
            con.execute("INSERT INTO fixture_jobs(job_id,tenant_id,session_id,status,attempts,created_at,updated_at) VALUES(?,?,?,'QUEUED',0,?,?)",
                        (job_id, actor["tenant_id"], sid, now, now))
            result = {"job_id": job_id, "status": "QUEUED", "kind": "NO_MEDIA_TEST_FIXTURE"}
            self._remember(con, actor, op, key, digest, result)
            con.execute("COMMIT")
            return result
        except Exception:
            if con.in_transaction:
                con.execute("ROLLBACK")
            raise
        finally:
            con.close()

    def lease_fixture_job(self, worker, now_seconds, seconds=30):
        """Atomic lease after crash; at-most-one current worker. In-process test API only."""
        if not _nonempty(worker) or type(now_seconds) not in (int, float) or not 1 <= seconds <= 300:
            raise DomainError(400, "invalid_lease")
        con = self.connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("""SELECT * FROM fixture_jobs
                        WHERE status='QUEUED' OR (status='LEASED' AND lease_until <= ?)
                        ORDER BY created_at,job_id LIMIT 1""", (now_seconds,)).fetchone()
            if row is None:
                con.execute("COMMIT")
                return None
            # Stale lease tokens cannot succeed after another worker reacquires the job.
            lease_id = str(uuid.uuid4())
            con.execute("""UPDATE fixture_jobs SET status='LEASED',attempts=attempts+1,
                        leased_by=?,lease_until=?,updated_at=? WHERE job_id=?""",
                        (worker+":"+lease_id, now_seconds+seconds, _now(), row["job_id"]))
            result = {"job_id": row["job_id"], "lease_token": worker+":"+lease_id,
                      "attempt": row["attempts"]+1, "lease_until": now_seconds+seconds}
            con.execute("COMMIT")
            return result
        except Exception:
            if con.in_transaction:
                con.execute("ROLLBACK")
            raise
        finally:
            con.close()

    def finish_fixture_job(self, lease_token, job_id, now_seconds, success):
        """Reject stale worker success; policy failure after 3 attempts dead-letters a fixture."""
        if not _nonempty(lease_token) or not _nonempty(job_id) or type(now_seconds) not in (int, float) or type(success) is not bool:
            raise DomainError(400, "invalid_completion")
        con = self.connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM fixture_jobs WHERE job_id=?", (job_id,)).fetchone()
            if row is None:
                raise DomainError(404, "job_not_found")
            if row["status"] != "LEASED" or row["leased_by"] != lease_token or now_seconds >= row["lease_until"]:
                raise DomainError(409, "stale_lease_completion")
            next_state = "SUCCEEDED" if success else ("DEAD_LETTER" if row["attempts"] >= 3 else "QUEUED")
            con.execute("UPDATE fixture_jobs SET status=?,leased_by=NULL,lease_until=NULL,updated_at=? WHERE job_id=?",
                        (next_state, _now(), job_id))
            con.execute("COMMIT")
            return next_state
        except Exception:
            if con.in_transaction:
                con.execute("ROLLBACK")
            raise
        finally:
            con.close()

    def cancel_fixture_jobs(self, actor, sid):
        """Represents revocation/safety cancellation in a no-media local fixture."""
        con = self.connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            self._authorize(actor, con.execute("SELECT * FROM sessions WHERE session_id=?", (sid,)).fetchone())
            con.execute("""UPDATE fixture_jobs SET status='CANCELLED',leased_by=NULL,lease_until=NULL,updated_at=?
                         WHERE session_id=? AND status IN ('QUEUED','LEASED')""", (_now(), sid))
            con.execute("COMMIT")
        except Exception:
            if con.in_transaction:
                con.execute("ROLLBACK")
            raise
        finally:
            con.close()

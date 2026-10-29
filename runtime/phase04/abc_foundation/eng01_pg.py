"""ENG01 internal PostgreSQL transactional command port.

Entire command fingerprint, exact execution result and state audit share ONE
database transaction. No model has a DB credential or role authority.
"""
import hashlib
import json
import uuid
from datetime import datetime, timezone

import psycopg

from .pg_store import PostgresStore
from .store import DomainError


class ENG01PostgresCommandStore(PostgresStore):
    def execute_eng01_pause(self, principal, command):
        if command.get("input_ref")!="checkpoint:pause" or command.get("engine_id")!="ENG-01":
            raise DomainError(501,"capability_not_implemented")
        # Caller is trusted in-process gateway, but enforce all stable fields again.
        self._key(command.get("idempotency_key"))
        if command.get("idempotency_key") != command.get("command_id"):
            raise DomainError(400,"command_idempotency_binding_required")
        if type(command.get("expected_state_version")) is not int or command["expected_state_version"]<0:
            raise DomainError(400,"invalid_expected_state_version")
        try:
            cmd_id=uuid.UUID(command["command_id"])
            sid=uuid.UUID(command["session_id"])
            correlation=uuid.UUID(command["correlation_id"])
            digest=hashlib.sha256(json.dumps(command,sort_keys=True,separators=(",",":"),
                                           ensure_ascii=True,allow_nan=False).encode()).hexdigest()
        except (ValueError,TypeError,KeyError,OverflowError) as exc:
            raise DomainError(400,"invalid_engine_command") from exc
        issuer,subject=self._principal(principal)
        if (command.get("actor")!={"user_id":subject,"role":"SPECIALIST"}
                or not isinstance(command.get("tenant_id"),str)
                or not isinstance(command.get("branch_id"),str)):
            raise DomainError(403,"verified_actor_mismatch")
        tenant,branch=command["tenant_id"],command["branch_id"]
        with self._connect() as con:
            memberships=self._memberships(con,principal,branch)
            if len(memberships)!=1 or memberships[0]["tenant_id"]!=tenant:
                raise DomainError(404,"not_found")
            self._scope(con,issuer,subject,tenant,branch)
            row=con.execute("""SELECT * FROM abc.sessions
                     WHERE session_id=%s AND tenant_id=%s AND branch_id=%s
                       AND specialist_id=%s FOR UPDATE""",(sid,tenant,branch,subject)).fetchone()
            if row is None:
                raise DomainError(404,"not_found")
            # Row lock serializes same-session calls. A replay is resolved from the
            # scoped receipt first, EVEN IF the session has subsequently changed.
            previous=con.execute("""SELECT request_digest,result_json
                     FROM abc.eng01_command_receipts
                     WHERE tenant_id=%s AND command_id=%s""",(tenant,cmd_id)).fetchone()
            if previous is not None:
                if previous["request_digest"]!=digest:
                    raise DomainError(409,"idempotency_payload_conflict")
                return previous["result_json"]
            if row["state"]!="CREATED":
                raise DomainError(409,"invalid_transition")
            version=command["expected_state_version"]
            if row["state_version"]!=version:
                raise DomainError(409,"state_version_conflict")
            now=datetime.now(timezone.utc)
            # The app role no longer has SQL UPDATE permission on state.
            # Both the typed command and legacy checkpoint must converge
            # on the DB-owned transactional ENG14 broker and row trigger.
            try:
                new=con.execute("""SELECT * FROM abc.eng14_apply_pause(%s,%s)""",
                                (sid,version)).fetchone()
            except psycopg.errors.CheckViolation:
                raise DomainError(403,"eng14_workload_or_policy_denied") from None
            if new is None:
                raise DomainError(409,"state_version_conflict")
            con.execute("""INSERT INTO abc.state_audit
                    (audit_id,tenant_id,branch_id,session_id,from_state,to_state,
                     from_version,to_version,actor_id,occurred_at)
                    VALUES(%s,%s,%s,%s,'CREATED','PAUSED',%s,%s,%s,%s)""",
                    (uuid.uuid4(),tenant,branch,sid,version,version+1,subject,now))
            result={
                "engine_id":"ENG-01","state":"PAUSED","state_version":new["state_version"],
                "session_id":str(sid),"tenant_id":tenant,"branch_id":branch,
                "status":"DURABLE_CHECKPOINT_COMMITTED",
                "publication_status":"INTERNAL_SYNTHETIC_ONLY",
                "command_id":str(cmd_id),"correlation_id":str(correlation)
            }
            try:
                con.execute("""INSERT INTO abc.eng01_command_receipts
                    (command_id,tenant_id,branch_id,actor_id,session_id,
                     request_digest,correlation_id,result_json)
                     VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (cmd_id,tenant,branch,subject,sid,digest,correlation,json.dumps(result)))
            except psycopg.errors.UniqueViolation:
                # A different specialist sharing the tenant cannot read the
                # other scoped receipt under RLS. Do not surface a DB 500 or
                # leak its owner; the entire earlier state/audit is rolled back.
                raise DomainError(409,"command_id_conflict") from None
            return result

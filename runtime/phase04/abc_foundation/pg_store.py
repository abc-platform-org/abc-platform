"""PostgreSQL RLS-backed session adapter. Identity is a verified OIDC Principal.

This adapter deliberately does not expose an HTTP listener or accept client media.
Only a dedicated non-BYPASSRLS abc_app role may use this connection.
"""
import hashlib
import json
import uuid
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row

from .store import DomainError, _fingerprint, _nonempty


def _stamp(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class PostgresStore:
    def __init__(self, dsn):
        if not isinstance(dsn, str) or not dsn:
            raise ValueError("managed PostgreSQL DSN required")
        self.dsn = dsn

    def _connect(self):
        return psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=4)

    @staticmethod
    def _principal(principal):
        issuer, sub = getattr(principal, "issuer", None), getattr(principal, "subject", None)
        if not _nonempty(sub) or not isinstance(issuer, str) or not issuer.startswith("https://"):
            raise DomainError(401, "verified_oidc_identity_required")
        return issuer, sub

    @staticmethod
    def _scope(con, issuer, sub, tenant="", branch=""):
        for name, value in (("abc.issuer",issuer),("abc.subject",sub),
                            ("abc.tenant",tenant),("abc.branch",branch)):
            con.execute("SELECT set_config(%s,%s,true)", (name,value))

    def _memberships(self, con, principal, branch=None):
        issuer, sub = self._principal(principal)
        self._scope(con,issuer,sub)
        rows = con.execute("""SELECT tenant_id,branch_id FROM abc.memberships
                   WHERE issuer=%s AND subject=%s AND role='SPECIALIST' AND active
                   ORDER BY tenant_id,branch_id""", (issuer,sub)).fetchall()
        if branch is not None:
            rows = [r for r in rows if r["branch_id"]==branch]
        return rows

    @staticmethod
    def _public(row):
        fields=("session_id","tenant_id","branch_id","specialist_id","client_id",
                "appointment_id","service_id","state","state_version","created_at",
                "updated_at","last_event_id")
        return {**{k: (_stamp(row[k]) if k in ("created_at","updated_at")
                        else str(row[k]) if k in ("session_id","last_event_id")
                        else row[k])
                   for k in fields if row[k] is not None},
                "scope":"IN_SALON_SHARED_SCREEN"}

    @staticmethod
    def _key(key):
        if not isinstance(key,str) or not 8<=len(key)<=128 or not all(c.isalnum() or c in "-_." for c in key):
            raise DomainError(400,"invalid_idempotency_key")

    def create(self, principal, body, key):
        self._key(key)
        if not isinstance(body,dict) or set(body)-{"branch_id","scope","client_id","appointment_id","service_id"}:
            raise DomainError(400,"invalid_create_request")
        branch=body.get("branch_id")
        if not _nonempty(branch) or body.get("scope")!="IN_SALON_SHARED_SCREEN":
            raise DomainError(400,"invalid_session_scope")
        if any(not _nonempty(v) for k,v in body.items() if k in ("client_id","appointment_id","service_id")):
            raise DomainError(400,"invalid_field")
        issuer,sub=self._principal(principal)
        with self._connect() as con:
            permitted=self._memberships(con,principal,branch)
            if len(permitted)!=1:
                raise DomainError(403,"branch_not_authorized_or_ambiguous")
            tenant=permitted[0]["tenant_id"]
            self._scope(con,issuer,sub,tenant,branch)
            # One database-owned transaction now governs session + event +
            # idempotency receipt + create audit. The app role cannot INSERT
            # sessions or outbox rows directly after migration 0016.
            try:
                result=con.execute(
                    "SELECT abc.eng01_create_session(%s::jsonb,%s) AS response",
                    (json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False),key)
                ).fetchone()
            except psycopg.errors.UniqueViolation:
                raise DomainError(409,"idempotency_payload_conflict") from None
            except psycopg.errors.CheckViolation:
                raise DomainError(403,"eng01_creation_broker_denied") from None
            if not result or not isinstance(result.get("response"),dict):
                raise DomainError(500,"eng01_create_broker_postcondition_violation")
            response=result["response"]
            if (response.get("tenant_id")!=tenant or
                response.get("branch_id")!=branch or
                response.get("specialist_id")!=sub or
                response.get("state")!="CREATED" or
                response.get("state_version")!=0):
                raise DomainError(500,"eng01_create_broker_postcondition_violation")
            return response

    def get(self, principal, session_id):
        try:
            sid=uuid.UUID(session_id)
        except (ValueError,TypeError):
            raise DomainError(404,"not_found") from None
        issuer,sub=self._principal(principal)
        with self._connect() as con:
            scopes=self._memberships(con,principal)
            for row in scopes:
                self._scope(con,issuer,sub,row["tenant_id"],row["branch_id"])
                found=con.execute("SELECT * FROM abc.sessions WHERE session_id=%s",(sid,)).fetchone()
                if found:
                    return self._public(found)
        raise DomainError(404,"not_found")


    def has_verified_consent(self, principal, session_id, purpose):
        """Fail-closed read-only purpose check. No consent collection/issuance route.

        ACTIVE records can only be inserted by an independent approved evidence
        verifier in future. The abc_app role cannot mint or modify these records.
        """
        allowed = {"CAPTURE", "AI_PROCESSING", "PREVIEW_STORAGE", "INTERNAL_HANDOFF"}
        if purpose not in allowed:
            return False
        try:
            sid = uuid.UUID(session_id)
        except (ValueError, TypeError):
            return False
        issuer, sub = self._principal(principal)
        with self._connect() as con:
            scopes = self._memberships(con, principal)
            for scope in scopes:
                self._scope(con, issuer, sub, scope["tenant_id"], scope["branch_id"])
                # RLS additionally requires this specialist's session assignment.
                session = con.execute(
                    "SELECT client_id FROM abc.sessions WHERE session_id=%s", (sid,)
                ).fetchone()
                if not session or not session["client_id"]:
                    continue
                evidence = con.execute("""
                    SELECT consent_id FROM abc.consent_evidence
                    WHERE session_id=%s AND tenant_id=%s AND branch_id=%s
                      AND client_id=%s AND status='ACTIVE'
                      AND verified_at IS NOT NULL AND revoked_at IS NULL
                      AND valid_until IS NOT NULL AND valid_until > clock_timestamp()
                      AND evidence_digest <> '' AND retention_policy_id <> ''
                      AND %s = ANY(purpose)
                    LIMIT 1
                """, (sid, scope["tenant_id"], scope["branch_id"],
                      session["client_id"], purpose)).fetchone()
                if evidence:
                    return True
        return False


    def checkpoint_command(self, principal, session_id, action, expected_version, key):
        """Postgres-backed internal CREATED ↔ PAUSED checkpoint with CAS and replay.

        A draft internal API only, not a new approved v1 public operation/event.
        Real engine jobs are not enqueued by this adapter.
        """
        self._key(key)
        if action not in ("pause", "resume") or type(expected_version) is not int or expected_version < 0:
            raise DomainError(400, "invalid_checkpoint_command")
        # The older local checkpoint adapter previously resumed without
        # rechecking version-bound consent and ENG14 policy. Disallow that
        # legacy execution path until a transactional verified resume exists.
        if action=="resume":
            raise DomainError(501,"resume_requires_eng14_and_verified_consent")
        try:
            sid=uuid.UUID(session_id)
        except (ValueError,TypeError):
            raise DomainError(404,"not_found") from None
        issuer, sub=self._principal(principal)
        with self._connect() as con:
            scopes=self._memberships(con, principal)
            scope=None
            row=None
            for candidate in scopes:
                self._scope(con,issuer,sub,candidate["tenant_id"],candidate["branch_id"])
                row=con.execute("SELECT * FROM abc.sessions WHERE session_id=%s FOR UPDATE",(sid,)).fetchone()
                if row:
                    scope=candidate
                    break
            if not row:
                raise DomainError(404,"not_found")
            tenant,branch=scope["tenant_id"],scope["branch_id"]
            op=action+":"+str(sid)
            request={"session_id":str(sid),"action":action,"expected_state_version":expected_version}
            digest=_fingerprint(request)
            prior=con.execute("""SELECT fingerprint,response_json FROM abc.idempotency
                WHERE tenant_id=%s AND actor_id=%s AND operation=%s AND request_key=%s""",
                (tenant,sub,op,key)).fetchone()
            if prior:
                if prior["fingerprint"]!=digest:
                    raise DomainError(409,"idempotency_payload_conflict")
                return prior["response_json"]
            if row["state_version"]!=expected_version:
                raise DomainError(409,"state_version_conflict")
            if action=="pause":
                if row["state"]!="CREATED":
                    raise DomainError(409,"invalid_transition")
                state,checkpoint="PAUSED","CREATED"
            else:
                if row["state"]!="PAUSED" or row["checkpoint"]!="CREATED":
                    raise DomainError(409,"missing_or_invalid_checkpoint")
                state,checkpoint="CREATED",None
            now=datetime.now(timezone.utc)
            # The app DB role has no UPDATE(state,checkpoint) privilege.
            # A DB-owned, narrowly scoped ENG14 broker and independent
            # BEFORE UPDATE trigger must both approve this mutation.
            try:
                result=con.execute("""SELECT * FROM abc.eng14_apply_pause(%s,%s)""",
                        (sid,expected_version)).fetchone()
            except psycopg.errors.CheckViolation:
                raise DomainError(403,"eng14_workload_or_policy_denied") from None
            if result is None:
                raise DomainError(409,"state_version_conflict")
            con.execute("""INSERT INTO abc.state_audit
                (audit_id,tenant_id,branch_id,session_id,from_state,to_state,
                 from_version,to_version,actor_id,occurred_at)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (uuid.uuid4(),tenant,branch,sid,row["state"],state,
                 expected_version,expected_version+1,sub,now))
            response=self._public(result)
            con.execute("""INSERT INTO abc.idempotency
                (tenant_id,actor_id,operation,request_key,fingerprint,response_json)
                VALUES(%s,%s,%s,%s,%s,%s)""",
                (tenant,sub,op,key,digest,json.dumps(response)))
            return response

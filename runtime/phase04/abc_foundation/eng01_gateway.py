"""ENG-01 internal typed command port (synthetic-only).

Implements only a *subset* of frozen Phase02 engine-command.schema.json
and refuses unknown capabilities. The frozen schema remains unchanged.
Never use browser-provided actor/tenant/engine_id as authority.
"""
from datetime import datetime, timezone, timedelta
import uuid

from .eng01_orchestrator import OrchestrationEngine
from .store import DomainError, _nonempty


_ALLOWED_FIELDS=frozenset({
    "command_id","engine_id","contract_version","correlation_id","tenant_id",
    "branch_id","session_id","actor","input_schema_id","input_ref","idempotency_key",
    "requested_at","expected_state_version","policy_decision_id","deadline_at",
})
_REQUIRED=_ALLOWED_FIELDS-{"policy_decision_id","deadline_at"}
_ENGINE_SCHEMA="abc.internal.eng01.checkpoint.v0"


def _iso(value):
    if not isinstance(value,str) or not value or len(value)>48:
        raise DomainError(400,"invalid_command_time")
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:
        raise DomainError(400,"invalid_command_time") from None
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise DomainError(400,"invalid_command_time")
    return dt.astimezone(timezone.utc)


def _uuid(value, field):
    try:
        item=uuid.UUID(value)
    except (TypeError, ValueError, AttributeError):
        raise DomainError(400,"invalid_"+field) from None
    if str(item)!=value:
        raise DomainError(400,"invalid_"+field)
    return item


class TypedCheckpointGateway:
    def __init__(self, store, *, clock=None):
        self.orchestrator=OrchestrationEngine(store)
        self.clock=clock or (lambda:datetime.now(timezone.utc))

    def execute(self, principal, command):
        if not isinstance(command,dict) or set(command)-_ALLOWED_FIELDS or not _REQUIRED<=set(command):
            raise DomainError(400,"invalid_engine_command")
        _uuid(command["command_id"],"command_id")
        _uuid(command["correlation_id"],"correlation_id")
        _uuid(command["session_id"],"session_id")
        if (command["engine_id"]!="ENG-01" or
                command["contract_version"]!="1.0.0-draft" or
                command["input_schema_id"]!=_ENGINE_SCHEMA or
                command["input_ref"]!="checkpoint:pause"):
            raise DomainError(501,"capability_not_implemented")
        actor=command.get("actor")
        sub=getattr(principal,"subject",None)
        if (not _nonempty(sub) or not isinstance(actor,dict) or
                set(actor)!={"user_id","role"} or actor["role"]!="SPECIALIST" or
                actor["user_id"]!=sub):
            raise DomainError(403,"verified_actor_mismatch")
        if (not _nonempty(command.get("tenant_id")) or
                not _nonempty(command.get("branch_id"))):
            raise DomainError(400,"invalid_scope")
        # Until a separate durable command journal is implemented, bind each
        # command UUID to its idempotency key, preventing forged distinct
        # command IDs from sharing a successful database receipt.
        if command["idempotency_key"] != command["command_id"]:
            raise DomainError(400,"command_idempotency_binding_required")
        self.orchestrator.store._key(command["idempotency_key"])
        if "policy_decision_id" in command:
            raise DomainError(501,"policy_gate_not_connected")
        if type(command["expected_state_version"]) is not int or command["expected_state_version"]<0:
            raise DomainError(400,"invalid_expected_state_version")
        requested=_iso(command["requested_at"])
        now=self.clock()
        if now.tzinfo is None:
            raise ValueError("trusted_clock_must_be_aware")
        now=now.astimezone(timezone.utc)
        if requested>now+timedelta(seconds=120):
            raise DomainError(400,"command_from_future")
        if command.get("deadline_at") is not None:
            deadline=_iso(command["deadline_at"])
            if deadline<requested or deadline<now:
                raise DomainError(409,"command_deadline_expired")
        # Independent PostgresStore.get enforces active membership and assigned
        # specialist. Tenant/branch in command are compared, never used to query.
        scoped=self.orchestrator._authorized_session(principal,command["session_id"])
        if (scoped["tenant_id"]!=command["tenant_id"] or
                scoped["branch_id"]!=command["branch_id"]):
            raise DomainError(404,"not_found")
        # In a single DB transaction persist the FULL command digest,
        # session CAS, audit, and replay receipt; never mint a new correlation
        # ID for an existing command receipt or replay a modified command.
        writer=getattr(self.orchestrator.store,"execute_eng01_pause",None)
        if not callable(writer):
            raise DomainError(501,"atomic_command_receipt_store_required")
        return writer(principal,command)

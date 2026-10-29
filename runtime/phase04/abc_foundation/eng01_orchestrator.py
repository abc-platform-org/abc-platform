"""ENG-01: contract-derived, fail-closed durable workflow control plane.

Not a GPT prompt, free-text router, general microservice or product release.
The canonical graph remains contracts/v1/state-machines.json. This file owns
NO other engine's output, policy decisions, evidence or professional approval.

Only the already-implemented PostgresStore internal CREATED -> PAUSED commit is
executable. Other canonical edges are discoverable but remain BLOCKED until a
transactionally verified authorization + policy + evidence executor exists.
"""
from dataclasses import dataclass
import json
from pathlib import Path
import uuid

from .store import DomainError, _nonempty


_MACHINE = Path(__file__).with_name("eng01_consultation_machine.json")
_STATE_MAX = 128


@dataclass(frozen=True)
class NextAction:
    to_state: str
    actor: str
    guards: tuple[str, ...]
    readiness: str

    def as_dict(self):
        return {"to_state": self.to_state, "actor": self.actor,
                "required_guards": list(self.guards), "readiness": self.readiness}


class WorkflowMachine:
    """Validated, deterministic, immutable in-memory routing graph."""
    def __init__(self, payload):
        if payload.get("source_machine_id") != "CONSULTATION_SESSION":
            raise ValueError("unexpected_canonical_machine")
        if payload.get("source_contract_version") != "1.0.0-draft":
            raise ValueError("unsupported_canonical_machine_version")
        states=payload.get("states")
        initial=payload.get("source_initial")
        terminal=payload.get("source_terminal")
        if (not isinstance(states,list) or not states or len(set(states))!=len(states)
                or not all(_nonempty(x) for x in states)
                or initial not in states or not isinstance(terminal,list)
                or not terminal or not set(terminal)<=set(states)):
            raise ValueError("invalid_machine_states")
        edges=payload.get("transitions")
        if not isinstance(edges,list) or not edges:
            raise ValueError("empty_machine")
        index={}
        allowed_actors={"SPECIALIST"}|{f"ENG-{i:02d}" for i in range(1,20)}
        for edge in edges:
            if not isinstance(edge,dict) or set(edge)!={"from","to","actor","guards"}:
                raise ValueError("unexpected_transition_shape")
            source,target,actor,guards=(edge.get("from"),edge.get("to"),
                                        edge.get("actor"),edge.get("guards"))
            if (source not in states or target not in states or actor not in allowed_actors
                    or source in terminal or not isinstance(guards,list) or not guards
                    or not all(_nonempty(x) for x in guards)
                    or len(set(guards))!=len(guards)):
                raise ValueError("unsafe_transition_contract")
            key=(source,target)
            if key in index:
                raise ValueError("ambiguous_transition")
            index[key]=NextAction(to_state=target,actor=actor,guards=tuple(guards),
                                  readiness="POLICY_GATED_NOT_ENABLED")
        self.states=frozenset(states)
        self.terminal=frozenset(terminal)
        self.initial=initial
        self._edges=index

    @classmethod
    def load(cls):
        return cls(json.loads(_MACHINE.read_text()))

    def edges(self, from_state):
        if from_state not in self.states:
            raise DomainError(409,"unknown_workflow_state")
        return [edge for (from_,_),edge in self._edges.items() if from_==from_state]

    def edge(self, from_state, to_state):
        if from_state not in self.states or to_state not in self.states:
            raise DomainError(409,"unknown_workflow_state")
        edge=self._edges.get((from_state,to_state))
        if edge is None:
            raise DomainError(409,"transition_not_in_contract")
        return edge

    @property
    def transition_count(self):
        return len(self._edges)


class OrchestrationEngine:
    """Engine boundary over a trusted authenticated, tenant-scoped session store.

    PostgresStore.get checks OIDC issuer+subject membership, active specialist
    assignment and tenant/branch RLS. Never accept browser role/guard booleans.
    """
    ENGINE_ID="ENG-01"
    def __init__(self, session_store, machine=None):
        if session_store is None or not callable(getattr(session_store,"get",None)):
            raise ValueError("authenticated_session_store_required")
        self.store=session_store
        self.machine=machine or WorkflowMachine.load()

    def _authorized_session(self, principal, session_id):
        issuer,subject=getattr(principal,"issuer",None),getattr(principal,"subject",None)
        if (not isinstance(issuer,str) or not issuer.startswith("https://")
                or not _nonempty(subject)):
            raise DomainError(401,"verified_oidc_identity_required")
        try:
            sid=str(uuid.UUID(session_id))
        except (TypeError, ValueError, AttributeError):
            raise DomainError(404,"not_found") from None
        # This must be a server-controlled PostgresStore or compatible authoritative
        # adapter. Its get() implementation is responsible for independently checking
        # membership, branch, assigned specialist and DB-level tenant isolation.
        row=self.store.get(principal,sid)
        if (not isinstance(row,dict) or row.get("session_id")!=sid
                or row.get("specialist_id")!=subject
                or not _nonempty(row.get("tenant_id"))
                or not _nonempty(row.get("branch_id"))
                or row.get("state") not in self.machine.states
                or type(row.get("state_version")) is not int
                or row["state_version"]<0):
            raise DomainError(403,"untrusted_session_context")
        return row

    def inspect(self, principal, session_id):
        """Return contract-correct routing info, NOT authority to execute an edge."""
        row=self._authorized_session(principal,session_id)
        options=[]
        for edge in self.machine.edges(row["state"]):
            if edge.actor == "SPECIALIST":
                readiness=("INTERNAL_PAUSE_IMPLEMENTED" if
                           row["state"]=="CREATED" and edge.to_state=="PAUSED"
                           else "REQUIRES_AUTHORIZED_GUARDS_AND_IMPLEMENTATION")
            else:
                readiness="ENGINE_DEPENDENCY_UNAVAILABLE"
            options.append(NextAction(edge.to_state,edge.actor,edge.guards,
                                      readiness).as_dict())
        return {
            "engine_id":self.ENGINE_ID,
            "contract_version":"1.0.0-draft",
            "session_id":row["session_id"], "tenant_id":row["tenant_id"],
            "branch_id":row["branch_id"],
            "state":row["state"], "state_version":row["state_version"],
            "terminal":row["state"] in self.machine.terminal,
            "available_next_actions":options,
            "publication_status":"INTERNAL_SYNTHETIC_ONLY"
        }

    def perform_checkpoint(self, principal, session_id, *, target_state,
                           expected_state_version, idempotency_key):
        """Execute ONLY the real, narrow, already-implemented CREATED->PAUSED transaction.

        Replaying a successful pause with exactly the same idempotency key uses
        the existing transactional PostgresStore receipt; other keys and stale
        versions are rejected by its authoritative implementation. No media
        processing, policy acceptance or customer session is authorized here.
        """
        if target_state not in self.machine.states:
            raise DomainError(409,"unknown_workflow_state")
        if target_state != "PAUSED":
            raise DomainError(501,"capability_not_implemented")
        if type(expected_state_version) is not int or expected_state_version < 0:
            raise DomainError(400,"invalid_expected_state_version")
        if not callable(getattr(self.store,"checkpoint_command",None)):
            raise DomainError(501,"durable_checkpoint_store_required")
        self.store._key(idempotency_key)
        row=self._authorized_session(principal,session_id)
        # A replay is allowed to reach the database if the state is already
        # PAUSED+one version. Only the SQL receipt can distinguish same-key replay.
        if row["state"] not in ("CREATED","PAUSED"):
            raise DomainError(409,"invalid_transition")
        if row["state"]=="CREATED":
            edge=self.machine.edge("CREATED","PAUSED")
            if edge.actor!="SPECIALIST" or edge.guards!=("authenticated_actor","persist_checkpoint"):
                raise DomainError(501,"checkpoint_contract_changed")
            if row["state_version"]!=expected_state_version:
                raise DomainError(409,"state_version_conflict")
        else:
            if row["state_version"]!=expected_state_version+1:
                raise DomainError(409,"state_version_conflict")
        # ENG14 evaluates every edge from the frozen canonical machine;
        # only this synthetic S0 edge may proceed. PostgreSQL gate 0014
        # independently validates the state mutation inside the transaction.
        from .eng14_transition_policy import ENG14TransitionPolicy
        policy=ENG14TransitionPolicy(self.machine)
        policy.require_allowed(policy.evaluate(
            from_state="CREATED",to_state="PAUSED",actor="SPECIALIST",
            expected_version=expected_state_version))
        response=self.store.checkpoint_command(
            principal,row["session_id"],"pause",expected_state_version,idempotency_key)
        if (response.get("session_id")!=row["session_id"] or
                response.get("tenant_id")!=row["tenant_id"] or
                response.get("branch_id")!=row["branch_id"] or
                response.get("specialist_id")!=row["specialist_id"] or
                response.get("state")!="PAUSED" or
                response.get("state_version")!=expected_state_version+1):
            raise DomainError(500,"checkpoint_postcondition_violation")
        return {
            "engine_id":self.ENGINE_ID,"state":"PAUSED",
            "state_version":response["state_version"],
            "session_id":response["session_id"],
            "tenant_id":response["tenant_id"],"branch_id":response["branch_id"],
            "status":"DURABLE_CHECKPOINT_COMMITTED",
            "publication_status":"INTERNAL_SYNTHETIC_ONLY"
        }

"""Shared consultation state machine compiled from the frozen v1 contract."""

from dataclasses import dataclass
import json
from pathlib import Path

from .store import DomainError, _nonempty


_MACHINE = Path(__file__).with_name("eng01_consultation_machine.json")


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

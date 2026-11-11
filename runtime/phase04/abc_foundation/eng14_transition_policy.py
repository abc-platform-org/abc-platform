"""ENG14 deterministic consultation transition policy, fail-closed registry.

This is a machine-wide *coverage and block* policy, not product S0-S3 approval.
All 102 canonical transitions get a decision; only synthetic S0 pause can ALLOW.
Decision in Python is not the security authority: PostgreSQL trigger is a
separate atomic validation against the authenticated specialist and CAS.
"""
from .consultation_workflow import WorkflowMachine
from .store import DomainError


class ENG14TransitionPolicy:
    VERSION="eng14.state.synthetic.1"
    def __init__(self,machine=None):
        self.machine=machine or WorkflowMachine.load()
        if self.machine.transition_count!=102 or len(self.machine.states)!=20:
            raise ValueError("unreviewed_canonical_transition_set")

    def evaluate(self,*,from_state,to_state,actor,expected_version):
        if type(expected_version) is not int or expected_version<0:
            raise DomainError(400,"invalid_expected_state_version")
        edge=self.machine.edge(from_state,to_state)
        if edge.actor!=actor:
            return self._decision("BLOCK","ACTOR_NOT_OWNER",from_state,to_state)
        if (from_state,to_state)==("CREATED","PAUSED") and actor=="SPECIALIST":
            if edge.guards!=("authenticated_actor","persist_checkpoint"):
                return self._decision("BLOCK","CONTRACT_GUARDS_CHANGED",from_state,to_state)
            return self._decision("ALLOW","SYNTHETIC_S0_CHECKPOINT_ONLY",from_state,to_state)
        return self._decision("BLOCK","POLICY_AND_EXECUTOR_NOT_APPROVED",from_state,to_state)

    def _decision(self,decision,reason,source,target):
        return {
            "engine_id":"ENG-14","policy_version":self.VERSION,
            "source_state":source,"target_state":target,
            "decision":decision,"risk_class":"S0" if decision=="ALLOW" else "UNREVIEWED",
            "reason":reason,"approval_scope":"SYNTHETIC_LOCAL_ONLY"
        }

    def require_allowed(self,decision):
        if (not isinstance(decision,dict) or decision.get("decision")!="ALLOW"
            or decision.get("policy_version")!=self.VERSION
            or decision.get("engine_id")!="ENG-14"
            or decision.get("approval_scope")!="SYNTHETIC_LOCAL_ONLY"
            or decision.get("risk_class")!="S0"
            or set(decision)!={"engine_id","policy_version","source_state",
                                  "target_state","decision","risk_class",
                                  "reason","approval_scope"}
            or decision.get("reason")!="SYNTHETIC_S0_CHECKPOINT_ONLY"
            or (decision.get("source_state"),decision.get("target_state"))!=("CREATED","PAUSED")):
            raise DomainError(403,"eng14_transition_denied")

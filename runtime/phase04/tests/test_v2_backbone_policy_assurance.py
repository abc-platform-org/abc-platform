"""ENG01/02/03/14 existing security backbone remains deny-first under v2 design."""
import unittest

from abc_foundation.eng01_orchestrator import WorkflowMachine
from abc_foundation.eng14_transition_policy import ENG14TransitionPolicy
from abc_foundation.eng14_professional_gate import ProfessionalGate
from abc_foundation.engine_v2_contracts import stub_response
from abc_foundation.store import DomainError


class V2BackbonePolicyAssuranceTests(unittest.TestCase):
    def test_eng14_denies_all_unimplemented_canonical_edges(self):
        machine=WorkflowMachine.load()
        gate=ENG14TransitionPolicy(machine)
        self.assertEqual(machine.transition_count,102)
        allowed=[]
        denied=[]
        for source in machine.states:
            for action in machine.edges(source):
                verdict=gate.evaluate(from_state=source,to_state=action.to_state,
                    actor=action.actor,expected_version=0)
                key=(source,action.to_state)
                if verdict["decision"]=="ALLOW":
                    allowed.append(key)
                else:
                    denied.append(key)
        self.assertEqual(allowed,[("CREATED","PAUSED")])
        self.assertEqual(len(denied),101)
        self.assertTrue(all(key!=("CREATED","PAUSED") for key in denied))

    def test_professional_s1_s3_classifier_never_issues_approval(self):
        policy=ProfessionalGate()
        for service in (
            "HAIRCUT","HAIR_COLOR","BEARD","MAKEUP","NAILS","SKIN",
            "EXTENSIONS","KERATIN","CORRECTIVE"
        ):
            verdict=policy.assess(service=service,evidence=None,
                tenant_id="synthetic-tenant",session_id="synthetic-session",
                specialist_id="synthetic-specialist",state_version=1)
            with self.subTest(service=service):
                self.assertEqual(verdict["decision"],"BLOCK")
                self.assertFalse(verdict["execution_approved"])
                self.assertFalse(verdict["state_transition_approved"])
                self.assertFalse(verdict["human_approval_verified"])
                self.assertFalse(verdict["consent_verified"])

    def test_no_v2_engine_can_be_dispatched_through_legacy_v1(self):
        import abc_foundation.isolated_engine_service as old
        for engine in old.ENGINES:
            self.assertEqual(old.VERSION,"abc.internal.engine.synthetic.v1")
        # v2 schema admission is not an authentication, endorsement or
        # dispatch capability. There is deliberately no run/v2 route.
        import abc_foundation.engine_v2_contracts as v2
        self.assertNotIn("dispatch",v2.__dict__)
        self.assertTrue(callable(stub_response))


if __name__=="__main__":
    unittest.main()

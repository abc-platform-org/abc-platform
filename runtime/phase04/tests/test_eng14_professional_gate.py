"""ENG14 S1–S3 specialist evidence never self-authorizes treatment."""
import unittest
from abc_foundation.eng14_professional_gate import ProfessionalGate, _REQUIREMENTS
from abc_foundation.eng14_transition_policy import ENG14TransitionPolicy
from abc_foundation.eng01_orchestrator import WorkflowMachine


class ProfessionalPolicyTests(unittest.TestCase):
    def setUp(self):
        self.gate=ProfessionalGate()
        self.kw={"service":"HAIR_COLOR","tenant_id":"tenant-test",
                 "session_id":"session-test","specialist_id":"staff-test",
                 "state_version":3}

    def test_all_professional_services_are_blocked_pending_human_governance(self):
        for service in _REQUIREMENTS:
            with self.subTest(service=service):
                result=self.gate.assess(**{**self.kw,"service":service},evidence={})
                self.assertEqual(result["decision"],"BLOCK")
                self.assertFalse(result["state_transition_approved"])
                self.assertFalse(result["execution_approved"])
                self.assertTrue(result["required_evidence"])

    def test_completely_recorded_evidence_is_still_not_a_qualification(self):
        evidence={key:{"tenant_id":"tenant-test","session_id":"session-test",
                       "state_version":3,"source_ref":"internal:snapshot:1",
                       "digest":"f"*64,"review_status":"RECORDED_NOT_APPROVED"}
                  for key in _REQUIREMENTS["HAIR_COLOR"]}
        result=self.gate.assess(**self.kw,evidence=evidence,
            consent_proof={"approved":True},sop_approval={"approved":True})
        self.assertTrue(result["evidence_complete_for_review"])
        self.assertEqual(result["decision"],"BLOCK")
        self.assertEqual(result["reason"],
            "AWAITING_INDEPENDENT_PROFESSIONAL_AND_CONSENT_APPROVAL")
        self.assertFalse(result["human_approval_verified"])
        self.assertFalse(result["consent_verified"])

    def test_wrong_tenant_or_version_provenance_blocks(self):
        k=_REQUIREMENTS["HAIR_COLOR"][0]
        item={"tenant_id":"other-tenant","session_id":"session-test",
              "state_version":3,"source_ref":"test:1","digest":"f"*64,
              "review_status":"RECORDED_NOT_APPROVED"}
        result=self.gate.assess(**self.kw,evidence={k:item})
        self.assertEqual(result["reason"],"EVIDENCE_SCOPE_OR_PROVENANCE_INVALID")

    def test_unknown_real_service_does_not_fallback_to_s0(self):
        self.assertEqual(self.gate.assess(**{**self.kw,"service":"synthetic:hair-color"},
                              evidence={})["decision"],"BLOCK")

    def test_canonical_edges_remain_fail_closed(self):
        machine=WorkflowMachine.load()
        policy=ENG14TransitionPolicy(machine)
        allowed=0
        for source in machine.states:
            for edge in machine.edges(source):
                d=policy.evaluate(from_state=source,to_state=edge.to_state,
                                  actor=edge.actor,expected_version=0)
                allowed+=d["decision"]=="ALLOW"
        self.assertEqual(allowed,1)

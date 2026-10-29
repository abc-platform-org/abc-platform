"""No engine gets COMPLETE from a CI fixture, self-assertion, or score."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts.validate_engine_quality import verify,POLICY,REGISTRY


class EngineQualityGovernanceTests(unittest.TestCase):
    def setUp(self):
        self.policy=json.loads(POLICY.read_text())
        self.registry=json.loads(REGISTRY.read_text())

    def test_baseline_seven_engines_and_seventy_missing_evidence_gates(self):
        result=verify(self.policy,self.registry)
        self.assertEqual(result["engine_count"],7)
        self.assertEqual(result["mandatory_gates_per_engine"],10)
        self.assertEqual(result["open_engine_gate_slots"],70)
        self.assertEqual(result["complete"],0)
        self.assertFalse(result["product_release_approved"])

    def test_fake_complete_without_external_evidence_fails(self):
        for mutation in (
            {"current_state":"COMPLETE"},
            {"completion_claim":True},
            {"real_customer_ready":True},
            {"critical_blockers":[]},
            {"gate_evidence":{"G10_INDEPENDENT_SIGNOFF":"PASS"}},
        ):
            with self.subTest(mutation=mutation):
                data=copy.deepcopy(self.registry)
                data["engines"][0].update(mutation)
                with self.assertRaises(AssertionError):
                    verify(self.policy,data)

    def test_partial_engine_inventory_and_policy_drift_fail(self):
        for mutate in (
            lambda reg:reg["engines"].pop(),
            lambda reg:reg["engines"][4].update(id="ENG-04"),
            lambda reg:reg["engines"][3].update(
                target_architecture_role="ENG-05 duplicate role"),
        ):
            data=copy.deepcopy(self.registry)
            mutate(data)
            with self.assertRaises(AssertionError):
                verify(self.policy,data)
        data=copy.deepcopy(self.policy)
        data["mandatory_gates"].pop()
        with self.assertRaises(AssertionError):
            verify(data,self.registry)

    def test_target_engine_id_migration_is_not_silently_marked_complete(self):
        e={item["id"]:item for item in self.registry["engines"]}
        for eid in ("ENG-04","ENG-05","ENG-06"):
            blockers=" ".join(e[eid]["critical_blockers"]).lower()
            self.assertIn("current runtime implementation",blockers)
            self.assertEqual(e[eid]["observed_maturity"],
                             "SYNTHETIC_PROCESS_CI_TESTED")

    def test_all_gates_have_independent_evidence_and_acceptance_criteria(self):
        for gate in self.policy["mandatory_gates"]:
            self.assertGreaterEqual(len(gate["acceptance"]),3)
            self.assertGreaterEqual(len(gate["evidence"]),3)
        self.assertTrue(self.policy["release_separate_from_engine_complete"])


if __name__=="__main__":
    unittest.main()

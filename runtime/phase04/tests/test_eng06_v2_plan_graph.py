"""ENG06 technical plan workflow is an architectural contract, never runtime permission."""
import json
import unittest
from pathlib import Path

from abc_foundation.engine_v2_contracts import ROOT


class ENG06V2StateGraphTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads((ROOT/"eng06.plan-workflow.v2.json").read_text())

    def test_plan_graph_is_specialist_gated_and_all_edges_disabled(self):
        p=self.config
        self.assertEqual(p["engine_id"],"ENG-06")
        self.assertEqual(p["initial"],"LOOK_SELECTED")
        self.assertIn("OPERATIONAL_HANDOFF",p["terminal"])
        self.assertEqual(len(p["states"]),13)
        edges=p["transitions"]
        self.assertEqual(len(edges),15)
        self.assertTrue(all(e["currently_executable"] is False for e in edges))
        self.assertTrue(all(e["from"] in p["states"] and e["to"] in p["states"]
                            for e in edges))
        self.assertEqual(len({(e["from"],e["to"]) for e in edges}),len(edges))
        final=[e for e in edges if e["to"]=="OPERATIONAL_HANDOFF"]
        self.assertEqual(len(final),1)
        self.assertEqual(final[0]["from"],"VALIDATED")
        self.assertIn("signed_operator_release",final[0]["guard"])

    def test_cannot_skip_look_lock_policy_or_specialist_review(self):
        edges=self.config["transitions"]
        pairs={(e["from"],e["to"]) for e in edges}
        for shortcut in (("LOOK_SELECTED","PLAN_DRAFTED"),
                         ("EVIDENCE_CHECK","VALIDATED"),
                         ("PLAN_DRAFTED","OPERATIONAL_HANDOFF"),
                         ("SPECIALIST_REVIEW","OPERATIONAL_HANDOFF"),
                         ("REJECTED","OPERATIONAL_HANDOFF")):
            self.assertNotIn(shortcut,pairs)
        self.assertIn(("EVIDENCE_CHECK","MISSING_REQUIRED_EVIDENCE"),pairs)
        self.assertIn(("PLAN_DRAFTED","SPECIALIST_REVIEW"),pairs)

    def test_engine_legacy_v1_not_used_to_approve_plan(self):
        import abc_foundation.isolated_engine_service as legacy
        self.assertEqual(legacy.VERSION,"abc.internal.engine.synthetic.v1")
        self.assertFalse(self.config["transitions"][0]["currently_executable"])


if __name__=="__main__":
    unittest.main()

"""Independent Phase04 release gating must reject fabricated READY values."""
import copy
import json
import unittest
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts.validate_phase04_readiness import FILE,validate


class Phase04ReadinessPolicyTests(unittest.TestCase):
    def setUp(self):
        self.manifest=json.loads(FILE.read_text())

    def test_ten_unclosed_external_acceptance_gates(self):
        status=validate(self.manifest)
        self.assertEqual(status["required_gate_count"],10)
        self.assertEqual(status["unverified_gate_count"],10)
        self.assertFalse(status["phase04_complete"])
        self.assertFalse(status["release_approved"])

    def test_no_fabricated_phase_complete_or_partial_signoff(self):
        for transform in (
            lambda d:d.update(status="COMPLETE"),
            lambda d:d.update(phase04_complete=True),
            lambda d:d.update(release_status="APPROVED"),
            lambda d:d.update(production_release_approved=True),
            lambda d:d.update(managed_private_deployment_verified=True),
            lambda d:d["required_gates"][0].update(status="PASS"),
            lambda d:d["required_gates"][0]["signed_independent_approvals"].append(
                {"signed_by":"AI"}),
            lambda d:d["required_gates"].pop(),
        ):
            data=copy.deepcopy(self.manifest)
            transform(data)
            with self.subTest(transform=transform),self.assertRaises(AssertionError):
                validate(data)


if __name__=="__main__":
    unittest.main()

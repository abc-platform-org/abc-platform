"""Mutation tests: architecture mapping must fail closed under tampering.

No database or professional authority required; these tests verify audit
controls only, not execution of canonical v3 workflow.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"scripts"))
import validate_abc_engine_completion_audit as audit


class CanonicalAuditMutationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.gov=Path(self.tmp.name)
        for name in ("abc_engine_registry_19.v0.review.json",
                     "abc_workflow_19.v0.review.json",
                     "abc_v2_to_19_adapters.v0.review.json",
                     "abc_engine_quality_19.v0.review.json",
                     "abc_legacy_namespace_reconciliation.v1.json"):
            (self.gov/name).write_bytes((audit.GOV/name).read_bytes())
        self.patcher=patch.object(audit,"GOV",self.gov)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def mutate(self,name,change):
        path=self.gov/name
        obj=json.loads(path.read_text())
        change(obj)
        path.write_text(json.dumps(obj))
        with self.assertRaises(AssertionError):
            audit.validate()

    def test_untampered_review_baseline_passes(self):
        result=audit.validate()
        self.assertFalse(result["customer_release_approved"])
        self.assertEqual(result["open_quality_gates"],190)

    def test_eng19_review_transport_cannot_claim_canonical_owner(self):
        self.mutate("abc_legacy_namespace_reconciliation.v1.json",
                    lambda x:x["entries"][-1].update(canonical_owner="ENG-19"))

    def test_eng06_technical_plan_cannot_claim_decision_owner(self):
        self.mutate("abc_legacy_namespace_reconciliation.v1.json",
                    lambda x:next(e for e in x["entries"] if e["module"]=="eng06_technical_plan_v2.py").update(canonical_owner="ENG-06"))

    def test_unreviewed_adapter_cannot_dispatch(self):
        self.mutate("abc_v2_to_19_adapters.v0.review.json",
                    lambda x:x.update(live_dispatch_enabled=True))

    def test_unknown_adapter_cannot_be_silently_added(self):
        self.mutate("abc_legacy_namespace_reconciliation.v1.json",
                    lambda x:x["entries"][0].update(adapter="UNREGISTERED"))

    def test_canonical_workflow_cannot_claim_live(self):
        self.mutate("abc_workflow_19.v0.review.json",
                    lambda x:x["ordered_stages"][0].update(execution_status="LIVE"))

    def test_professional_gate_cannot_be_skipped(self):
        self.mutate("abc_workflow_19.v0.review.json",
                    lambda x:x["required_policy_gates"][0].update(skip_allowed=True))

    def test_unsigned_engine_cannot_claim_completion(self):
        self.mutate("abc_engine_quality_19.v0.review.json",
                    lambda x:x["engines"][0].update(completion_signed=True))

    def test_release_cannot_be_enabled_by_mapping(self):
        self.mutate("abc_legacy_namespace_reconciliation.v1.json",
                    lambda x:x.update(customer_release_approved=True))


if __name__=="__main__":
    unittest.main()

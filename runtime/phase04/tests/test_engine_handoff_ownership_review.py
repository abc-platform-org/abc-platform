"""Check the proposed ownership map and exercise the existing review boundary."""
import json
import os
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from abc_foundation.engine19_handoff_preflight import preflight_candidate_handoff
from abc_foundation.isolated_engine_service import ENGINES, dispatch
from abc_foundation.store import DomainError


ROOT = Path(__file__).resolve().parents[3]


def governance(name):
    return json.loads((ROOT / "governance" / (name + ".json")).read_text())


class EngineHandoffOwnershipReviewTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"ABC_ENV": "LOCAL_INTEGRATION_ONLY"}))
        self.review = governance("abc_engine_handoff_ownership.v0.review")

    def test_proposed_owners_and_legacy_bindings_match_registries(self):
        review = self.review
        registry = governance("abc_engine_registry_19.v0.review")
        legacy = governance("abc_legacy_namespace_reconciliation.v1")
        self.assertEqual(review["status"], "PROPOSED_FOR_ARCHITECTURE_OWNER_REVIEW")
        self.assertIsNone(review["architecture_owner_approval"])
        self.assertIs(review["live_dispatch_enabled"], False)
        self.assertIs(review["customer_release_approved"], False)
        self.assertEqual(set(review["ownership"]), {"ENG-06", "ENG-15", "ENG-19"})
        for entry in registry["engines"]:
            mapped = review["ownership"].get(entry["engine_id"])
            if mapped:
                self.assertEqual(mapped, {key: entry[key] for key in mapped})
        self.assertEqual(review["legacy_bindings"], legacy["entries"])
        for binding in review["physical_bindings"]:
            self.assertTrue((ROOT / "runtime/phase04/abc_foundation" / binding["module"]).is_file())
            migration_dir = ROOT / "runtime/phase04/migrations"
            sql = "\n".join(path.read_text() for prefix in binding["migrations"]
                            for path in migration_dir.glob(prefix + "_*.sql"))
            for identifier in binding["objects"] + binding["roles"]:
                with self.subTest(identifier=identifier):
                    self.assertIn(identifier, sql)
        self.assertEqual(ENGINES, ("ENG-04", "ENG-05", "ENG-06"))

    def test_technical_plan_adapter_is_versioned_review_only(self):
        adapter = self.review["technical_plan_adapter"]
        registry = governance("abc_v2_to_19_adapters.v0.review")
        entry = next(item for item in registry["adapters"] if item["adapter_id"] == adapter["adapter_id"])
        self.assertEqual((entry["source_engine"], entry["target_engine"]),
                         (adapter["source_identity"], adapter["target_owner"]))
        self.assertEqual(entry["target_engine"], "ENG-15")
        self.assertEqual(entry["migration_status"], "UNMIGRATED")
        self.assertIs(entry["runtime_enabled"], False)
        self.assertIs(adapter["runtime_enabled"], False)
        self.assertIs(adapter["implicit_routing"], False)
        for field in ("source_protocol", "target_protocol"):
            self.assertEqual(adapter[field], registry[field])
        self.assertEqual(adapter["projection_protocol"], registry["protocol"])
        self.assertEqual(adapter["output_status"], "REVIEW_ONLY_UNWIRED")

    def candidate(self, edge):
        return {
            "handoff_id": str(uuid.uuid4()), "session_id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()), "state_version": 1,
            "tenant_id": "tenant-test", "branch_id": "branch-test",
            "from_engine": edge["from"], "to_engine": edge["to"],
            "contract_version": edge["contract_version"], "artifact_kind": edge["artifact"],
            "artifact_sha256": "a" * 64, "evidence_refs": ["synthetic:review"],
            "policy_proof_ref": "synthetic:review", "status": self.review["eng07_boundary"]["candidate_status"],
            "execution_authorized": False, "customer_release_approved": False,
        }

    def test_three_declared_edges_pass_preflight_only(self):
        graph = governance("abc_workflow_19.v0.review")
        routes = [("ENG-04", "ENG-05"), ("ENG-05", "ENG-06"), ("ENG-06", "ENG-07")]
        actual = {(item["from"], item["to"]): item for item in graph["handoffs"]}
        edges = self.review["review_handoffs"]
        self.assertEqual(edges, [actual[route] for route in routes])
        for edge in edges:
            with self.subTest(edge=(edge["from"], edge["to"])):
                self.assertEqual(edge["status"], "SPEC_ONLY_UNWIRED")
                receipt = preflight_candidate_handoff(self.candidate(edge))
                self.assertEqual(receipt["status"], "CONTRACT_PREFLIGHT_ONLY")
                self.assertIs(receipt["runtime_dispatch_authorized"], False)
                self.assertIs(receipt["customer_release_approved"], False)

    def test_eng07_denies_blocked_review_only_and_version_mutations(self):
        edge = self.review["review_handoffs"][-1]
        policy = self.review["eng07_boundary"]
        self.assertIs(policy["runtime_dispatch_authorized"], False)
        self.assertEqual(policy["unknown_version"], "REJECT")
        self.assertEqual(policy["legacy_v2_projection"], "REJECT")
        self.assertEqual(set(policy["rejected_statuses"]), {"BLOCKED", "REVIEW_ONLY", "REVIEW_ONLY_UNWIRED"})
        mutations = [("status", status) for status in policy["rejected_statuses"]]
        mutations += [
            ("contract_version", "abc.internal.capability.v999"),
            ("contract_version", self.review["technical_plan_adapter"]["projection_protocol"]),
            ("from_engine", "ENG-15"),
            ("artifact_kind", "SPECIALIST_REVIEWABLE_TECHNICAL_PLAN"),
            ("execution_authorized", True),
            ("customer_release_approved", True),
        ]
        candidate = self.candidate(edge)
        for key, value in mutations:
            with self.subTest(key=key, value=value), self.assertRaises(DomainError):
                preflight_candidate_handoff({**candidate, key: value})
        with self.assertRaises(DomainError) as denied:
            dispatch(candidate, "ENG-07")
        self.assertEqual(denied.exception.code, "unknown_engine_process")

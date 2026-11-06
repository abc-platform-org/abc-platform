"""A2 ADR-ENG-005: static predeployment trust-registry consistency checks.

These tests examine candidate metadata and source guards only. They do not
attest an external issuer, managed PostgreSQL, independent review or release.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TRUST = ROOT / "governance/abc_w1_workload_trust_boundaries.v0.review.json"
ENGINE_IDENTITY = ROOT / "runtime/phase04/abc_foundation/service_mesh_identity.py"
PG_ATOMIC = ROOT / "runtime/phase04/migrations/0034_a2_private_spiffe_atomic_ingress.sql"

ENGINES = ("ENG-01", "ENG-02", "ENG-03", "ENG-04",
           "ENG-05", "ENG-06", "ENG-14")


class ADR005CandidateConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.trust = json.loads(TRUST.read_text(encoding="utf-8"))

    def test_issuer_ttl_matches_runtime_and_sql_cap(self):
        self.assertEqual(
            self.trust["credential_requirements"][
                "maximum_proposed_assertion_ttl_seconds"], 120)
        self.assertIn("exp-iat>120", ENGINE_IDENTITY.read_text(encoding="utf-8"))
        self.assertIn(
            "interval '120 seconds'", PG_ATOMIC.read_text(encoding="utf-8"))

    def test_seven_canonical_engine_principals_are_distinct_and_unissued(self):
        workloads = self.trust["workloads"]
        self.assertEqual(tuple(w["engine_id"] for w in workloads), ENGINES)
        expected = [
            "spiffe://abc.internal/staging/" + engine.lower()
            for engine in ENGINES
        ]
        actual = [w["proposed_spiffe_id"] for w in workloads]
        self.assertEqual(actual, expected)
        self.assertEqual(len(set(actual)), 7)
        for w in workloads:
            self.assertIs(w["verified_attestation"], False)
            self.assertIs(w["workload_deployed"], False)

    def test_unreviewed_routes_and_operator_proofs_remain_denied(self):
        self.assertEqual(len(self.trust["candidate_routes"]), 11)
        self.assertTrue(all(
            route["approved_for_transport"] is False
            and route["externally_verified"] is False
            and route["authorization_mode"] ==
                "EXPLICIT_DENY_PENDING_INDEPENDENT_APPROVAL"
            for route in self.trust["candidate_routes"]))
        self.assertEqual(len(self.trust["operator_evidence_slots"]), 10)
        self.assertTrue(all(
            proof["status"] == "MISSING"
            for proof in self.trust["operator_evidence_slots"]))
        for flag in (
            "private_network_attested",
            "externally_managed_issuer_attested",
            "external_private_postgres_verified",
            "technical_cost_approval_received",
            "independent_architecture_signoff",
            "independent_security_signoff",
            "independent_sre_signoff",
            "live_v3_routing_allowed",
            "eng05_outbox_release_allowed",
            "customer_release_approved",
        ):
            self.assertIs(self.trust[flag], False)


if __name__ == "__main__":
    unittest.main()

"""ENG06 parallel-development policy: engineering can proceed, release cannot.

Tests run offline and are independent of professional external sources.
"""
import os
import unittest
import uuid
from unittest.mock import patch

from abc_foundation.eng06_review_worker import SyntheticEng06ReviewWorker
from abc_foundation.eng06_decision import SyntheticDecisionEngine
from abc_foundation.eng02_consultation import SYNTHETIC_SERVICE
from abc_foundation.store import DomainError


class DenyConnectStore:
    def _connect(self):
        raise AssertionError("Hosted mode must be denied before DB connection")


class Eng06DeferredReleasePolicyTests(unittest.TestCase):
    def test_hosted_execution_rejected_before_any_database_io(self):
        worker = SyntheticEng06ReviewWorker(
            store=DenyConnectStore(), consumer_id="ci-engineering")
        for mode in ("PRODUCTION", "STAGING", "DEVELOPMENT", ""):
            with self.subTest(mode=mode), patch.dict(
                os.environ, {"ABC_ENV": mode}
            ):
                with self.assertRaises(DomainError):
                    worker.claim()

    def test_synthetic_engine_without_professional_source_never_releases(self):
        sid = str(uuid.uuid4())
        keys = ("prior_treatment", "sensitivity_flag", "goal", "maintenance")
        evidence_ids = ["synthetic:evidence:" + k for k in keys]
        analysis = {
            "session_id": sid,
            "service_id": SYNTHETIC_SERVICE,
            "evidence_ids": evidence_ids,
            "attributes": [
                {
                    "key": key,
                    "value": value,
                    "evidence_class": "USER_REPORTED",
                    "source_evidence_id": evidence_ids[i],
                }
                for i, (key, value) in enumerate(zip(
                    keys, ("NO", "NO", "SUBTLE", "LOW")
                ))
            ],
        }
        knowledge = {
            "service_id": SYNTHETIC_SERVICE,
            "retrieval_sources": [],
            "grounded_facts": [],
            "unknowns": ["SOURCE_UNVERIFIED"],
        }
        decision = SyntheticDecisionEngine().decide(
            analysis=analysis, knowledge=knowledge)
        self.assertEqual(decision["candidates"], [])
        self.assertEqual(
            {item["reason"] for item in decision["excluded_options"]},
            {"UNVERIFIED_KNOWLEDGE_SOURCE"},
        )
        self.assertEqual(len(decision["excluded_options"]), 2)


if __name__ == "__main__":
    unittest.main()

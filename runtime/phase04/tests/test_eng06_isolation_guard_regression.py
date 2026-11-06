"""Isolated ENG06 guard regression tests."""
import os
import unittest
from unittest.mock import patch
from abc_foundation.eng06_review_worker import SyntheticEng06ReviewWorker
from abc_foundation.store import DomainError

class DummyStore:
    def _connect(self):
        raise AssertionError("database must not be accessed")

class Eng06IsolationTests(unittest.TestCase):
    def setUp(self):
        self.worker = SyntheticEng06ReviewWorker(store=DummyStore(), consumer_id="ci-review")

    def test_non_local_mode_rejected(self):
        with patch.dict(os.environ, {"ABC_ENV":"STAGING"}):
            with self.assertRaises(DomainError):
                self.worker.decide_blocked({})

    def test_untrusted_claim_rejected(self):
        with patch.dict(os.environ, {"ABC_ENV":"LOCAL_INTEGRATION_ONLY"}):
            with self.assertRaises(DomainError):
                self.worker.decide_blocked({"engine_id":"ENG-06"})

if __name__ == "__main__":
    unittest.main()

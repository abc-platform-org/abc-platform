"""ENG05 authority-gate security regression tests; no real credentials."""
import unittest
from datetime import datetime, timezone
from abc_foundation.eng05_external_authority_gate import evaluate_external_authority
from abc_foundation.eng05_professional_sources import SourceGovernanceError

class GateNegativeTests(unittest.TestCase):
    def test_registry_unavailable(self):
        with self.assertRaises(SourceGovernanceError):
            evaluate_external_authority([],[],registry=None,revoked=lambda _:False,legal_receipts={})
    def test_revoked_or_unknown(self):
        for result in (True,None):
            with self.subTest(result=result), self.assertRaises(SourceGovernanceError):
                evaluate_external_authority([], [{"credential_id":"test"}],
                    registry=lambda _:{"authority_attested":True},
                    revoked=lambda _:result,legal_receipts={})
    def test_missing_anchor(self):
        with self.assertRaises(SourceGovernanceError):
            evaluate_external_authority([], [{"credential_id":"test"}],
                registry=lambda _:None,revoked=lambda _:False,legal_receipts={})
    def test_no_legal_evidence(self):
        with self.assertRaises(SourceGovernanceError):
            evaluate_external_authority([], [],registry=lambda _:None,
                revoked=lambda _:False,legal_receipts=None)
    def test_empty_dossier_rejected(self):
        with self.assertRaises(SourceGovernanceError):
            evaluate_external_authority([], [],registry=lambda _:None,
                revoked=lambda _:False,legal_receipts={})
    def test_explicit_no_release_in_source(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[1]/"abc_foundation"/
                "eng05_external_authority_gate.py").read_text()
        for field in ("eng05_ingestion_authorized", "eng06_dispatch_authorized",
                      "customer_release_authorized"):
            self.assertIn('"'+field+'": False',source)

if __name__=="__main__":
    unittest.main()

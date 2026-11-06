"""Regression: revocation must be checked again after signature adjudication."""
import unittest
from unittest.mock import patch
from abc_foundation.eng05_external_authority_gate import evaluate_external_authority
from abc_foundation.eng05_professional_sources import SourceGovernanceError

class RevocationRaceTests(unittest.TestCase):
    def test_revoked_while_adjudicating_fails_closed(self):
        calls=[]
        def revoked(_):
            calls.append(True)
            return len(calls)>1
        with patch("abc_foundation.eng05_external_authority_gate.adjudicate",
                   return_value={"review_gate":"REVIEWED_NON_EXECUTABLE"}):
            with self.assertRaisesRegex(SourceGovernanceError,
                                        "credential_revoked_during_adjudication"):
                evaluate_external_authority(
                    [{"source_id":"ci","version":"1.0.0","jurisdiction":"DE"}],
                    [{"credential_id":"ci-credential"}],
                    registry=lambda _:{"authority_attested":True},
                    revoked=revoked,legal_receipts={})
        self.assertEqual(len(calls),2)

if __name__=="__main__":
    unittest.main()

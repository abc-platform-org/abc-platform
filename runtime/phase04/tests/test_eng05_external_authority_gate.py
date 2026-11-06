"""Adversarial contract tests; no external signatures or rights are simulated as approvals."""
import unittest
from abc_foundation.eng05_external_authority_gate import evaluate_external_authority
from abc_foundation.eng05_professional_sources import SourceGovernanceError

class ExternalAuthorityNegativeTests(unittest.TestCase):
    def test_unknown_registry_fails_closed(self):
        with self.assertRaises(SourceGovernanceError):
            evaluate_external_authority([], [], registry=None, revoked=lambda _: False, legal_receipts={})

    def test_revoked_credential_fails_closed(self):
        with self.assertRaisesRegex(SourceGovernanceError, "credential_revoked_or_unknown"):
            evaluate_external_authority([], [{"credential_id":"revoked"}],
                registry=lambda _: {"authority_attested": True},
                revoked=lambda _: True, legal_receipts={})

    def test_revocation_lookup_failure_fails_closed(self):
        with self.assertRaisesRegex(SourceGovernanceError, "credential_revoked_or_unknown"):
            evaluate_external_authority([], [{"credential_id":"unknown"}],
                registry=lambda _: {"authority_attested": True},
                revoked=lambda _: None, legal_receipts={})

    def test_untrusted_credential_fails_closed(self):
        with self.assertRaisesRegex(SourceGovernanceError, "credential_not_independently_attested"):
            evaluate_external_authority([], [{"credential_id":"unknown"}],
                registry=lambda _: None, revoked=lambda _: False, legal_receipts={})

    def test_missing_legal_receipts_fails_closed(self):
        with self.assertRaisesRegex(SourceGovernanceError, "legal_evidence_missing"):
            evaluate_external_authority([], [], registry=lambda _: None,
                revoked=lambda _: False, legal_receipts=None)

    def test_empty_dossier_cannot_be_approved(self):
        with self.assertRaises(SourceGovernanceError):
            evaluate_external_authority([], [], registry=lambda _: None,
                revoked=lambda _: False, legal_receipts={})

if __name__ == "__main__":
    unittest.main()

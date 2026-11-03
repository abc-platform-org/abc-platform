"""PostgreSQL fault-injection acceptance for synthetic ENG05 -> ENG06 handoff.

Exercises durable lease fencing, replay, consent withdrawal, and independent
failure containment using the disposable CI database. No customer release.
"""
import unittest

from test_eng06_pg_positive_e2e import Eng06PositivePostgresTests


class Eng06FaultInjectionAcceptance(Eng06PositivePostgresTests):
    """Reuses exact real-PostgreSQL fixture and asserts safety under faults."""

    def test_fault_expired_lease_recovery_fences_stale_worker(self):
        super().test_expired_lease_reclaim_fences_old_ack()

    def test_fault_duplicate_ack_is_rejected_after_durable_commit(self):
        super().test_real_claim_ack_persist_and_replay_denied()

    def test_fault_concurrent_workers_cannot_double_claim(self):
        super().test_concurrent_claim_only_one_wins()

    def test_fault_consent_revocation_between_claim_and_commit(self):
        super().test_revoked_consent_between_claim_and_ack_denied()


if __name__=="__main__":
    unittest.main()

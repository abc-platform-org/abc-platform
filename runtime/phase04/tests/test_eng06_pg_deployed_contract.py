"""ENG06 durable PostgreSQL contract tests for lease, replay and consent fencing.

These assertions inspect the deployed database functions, not a mock or
untrusted copy of migration text. Positive processing needs an upstream
ENG05 fixture and remains a separate release prerequisite.
"""
import os
import unittest

class Eng06DeployedContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getenv("ABC_ENV") != "LOCAL_INTEGRATION_ONLY":
            raise unittest.SkipTest("disposable CI only")
        cls.dsn = os.getenv("ABC_TEST_PG_ADMIN_DSN")
        if not cls.dsn:
            raise unittest.SkipTest("PostgreSQL fixture missing")

    def test_claim_lease_and_retry_fencing_are_deployed(self):
        import psycopg
        with psycopg.connect(self.dsn) as con:
            sql = con.execute(
                "SELECT pg_get_functiondef('abc.eng06_ci_claim(text,integer)'::regprocedure)"
            ).fetchone()[0]
        for guard in ("FOR UPDATE OF job SKIP LOCKED", "job.attempts<3",
                      "job.lease_until<v_now", "expired.attempts>=3",
                      "lease_token=v_lease", "status='DLQ'"):
            with self.subTest(guard=guard):
                self.assertIn(guard, sql)

    def test_ack_enforces_lease_consent_provenance_and_no_release(self):
        import psycopg
        with psycopg.connect(self.dsn) as con:
            sql = con.execute(
                "SELECT pg_get_functiondef('abc.eng06_ci_ack(uuid,uuid,text,text,bytea)'::regprocedure)"
            ).fetchone()[0]
        for guard in ("FOR UPDATE", "j.lease_token IS DISTINCT FROM p_lease",
                      "j.lease_until<=v_now", "ce.revoked_at IS NULL",
                      "ce.status='ACTIVE'", "o.status='BLOCKED_PENDING_AUTHORITY'",
                      "encode(sha256(src.source_bytes),'hex')",
                      "BLOCKED_PROFESSIONAL_SOURCE", "customer_release_approved",
                      "downstream_dispatch_authorized", "ACKED_BLOCKED_REVIEW_ONLY"):
            with self.subTest(guard=guard):
                self.assertIn(guard, sql)

    def test_failure_path_is_fenced_and_retries_are_bounded(self):
        import psycopg
        with psycopg.connect(self.dsn) as con:
            sql = con.execute(
                "SELECT pg_get_functiondef('abc.eng06_ci_fail(uuid,uuid,text)'::regprocedure)"
            ).fetchone()[0]
        for guard in ("FOR UPDATE", "j.lease_token IS DISTINCT FROM p_lease",
                      "j.lease_until<=clock_timestamp()", "j.attempts>=3",
                      "'DLQ'", "'QUEUED'"):
            with self.subTest(guard=guard):
                self.assertIn(guard, sql)

if __name__ == "__main__":
    unittest.main()

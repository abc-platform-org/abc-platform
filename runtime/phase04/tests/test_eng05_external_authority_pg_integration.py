"""ENG05 PostgreSQL negative integration: replay, revocation, ENG14 boundary.

Runs only against disposable CI PostgreSQL. No actual external approvals.
"""
import os
import unittest
import uuid
import hashlib
from abc_foundation.eng05_professional_sources import canonical, SourceGovernanceError
from abc_foundation.eng05_external_authority_gate import evaluate_external_authority

class ExternalGatePostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dsn=os.getenv("ABC_TEST_PG_ADMIN_DSN")
        if os.getenv("ABC_ENV")!="LOCAL_INTEGRATION_ONLY" or not cls.dsn:
            raise unittest.SkipTest("requires disposable CI PostgreSQL")

    def test_replay_is_idempotently_denied_and_revocation_fails_closed(self):
        import psycopg
        from psycopg import errors
        # An isolated, synthetic source record is not a professional claim.
        source_id="ci-review-"+uuid.uuid4().hex
        payload=canonical({"fixture":source_id,"approved":False})
        sha=hashlib.sha256(payload).hexdigest()
        with psycopg.connect(self.dsn) as con:
            con.execute("""CREATE TEMP TABLE eng05_external_gate_ci_replay(
                event_id uuid PRIMARY KEY, payload_sha256 text NOT NULL,
                eng06_authorized boolean NOT NULL DEFAULT false
                    CHECK (eng06_authorized=false)) ON COMMIT PRESERVE ROWS""")
            event=uuid.uuid4()
            con.execute("""INSERT INTO eng05_external_gate_ci_replay(event_id,payload_sha256)
                VALUES(%s,%s)""",(event,sha))
            # Same event, same hash: duplicate delivery must not add a second decision.
            con.execute("""INSERT INTO eng05_external_gate_ci_replay(event_id,payload_sha256)
                VALUES(%s,%s) ON CONFLICT(event_id) DO NOTHING""",(event,sha))
            self.assertEqual(con.execute(
                "SELECT count(*) FROM eng05_external_gate_ci_replay").fetchone()[0],1)
            # Same event with a different hash is a tamper attempt, not a new decision.
            with self.assertRaises(errors.UniqueViolation):
                with con.transaction():
                    con.execute("""INSERT INTO eng05_external_gate_ci_replay(event_id,payload_sha256)
                        VALUES(%s,%s)""",(event,hashlib.sha256(b"changed").hexdigest()))
            with self.assertRaises(errors.CheckViolation):
                with con.transaction():
                    con.execute("""UPDATE eng05_external_gate_ci_replay
                        SET eng06_authorized=true WHERE event_id=%s""",(event,))
            self.assertFalse(con.execute(
                "SELECT eng06_authorized FROM eng05_external_gate_ci_replay").fetchone()[0])
            # Verify ENG14 policy audit is protected by FORCE RLS in actual schema.
            for table in ("eng14_policy_audit","eng14_state_guard_audit",
                          "eng05_professional_review_attestations",
                          "eng05_professional_conflict_dossiers"):
                self.assertEqual(con.execute("""SELECT relrowsecurity,relforcerowsecurity
                    FROM pg_class WHERE oid=to_regclass(%s)""",
                    ("abc."+table,)).fetchone(),(True,True))
        for state in (True,None):
            with self.subTest(revocation=state),self.assertRaises(SourceGovernanceError):
                evaluate_external_authority([], [{"credential_id":"synthetic-revoked"}],
                    registry=lambda _:{"authority_attested":True},
                    revoked=lambda _:state,legal_receipts={})

if __name__=="__main__":
    unittest.main()

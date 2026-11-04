"""A1 six-adapter disposable PostgreSQL acceptance; never a live migration."""
import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from a1_legacy_adapter_quarantine import IDS, build_review_only_canonical_envelope


class SixAdapterShadowTests(unittest.TestCase):
    def test_six_adapter_shadow_idempotency_and_rollback(self):
        self.assertEqual(len(IDS), 6)
        self.assertEqual(os.environ.get("ABC_ENV"), "LOCAL_INTEGRATION_ONLY")
        dsn = os.environ["ABC_TEST_PG_ADMIN_DSN"]
        import psycopg
        with psycopg.connect(dsn, autocommit=True) as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute("""CREATE TEMP TABLE a1_adapter_shadow (
                        adapter_id text PRIMARY KEY,
                        digest text NOT NULL,
                        projection jsonb NOT NULL,
                        CHECK (projection->>'authority'='UNVERIFIED_REVIEW_ONLY'),
                        CHECK (projection->>'dispatch_authorized'='false'),
                        CHECK (projection->>'customer_release_approved'='false')
                    ) ON COMMIT DROP""")
                    for adapter_id in sorted(IDS):
                        artifact = {"synthetic": True, "adapter_id": adapter_id}
                        digest = hashlib.sha256(json.dumps(artifact, sort_keys=True,
                            separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
                        envelope = {
                            "tenant_id": "synthetic-tenant",
                            "branch_id": "synthetic-branch",
                            "session_id": "synthetic-session",
                            "source_sha256": digest,
                            "consent_decision_id": "synthetic-consent",
                            "policy_decision_id": "synthetic-policy",
                            "artifact_version": "abc.internal.engine.v2.draft",
                            "artifact": artifact,
                            "customer_release_approved": False,
                            "downstream_dispatch_authorized": False,
                        }
                        projection = build_review_only_canonical_envelope(adapter_id, envelope)
                        for _ in range(2):
                            cur.execute("""INSERT INTO a1_adapter_shadow
                                (adapter_id, digest, projection) VALUES (%s,%s,%s::jsonb)
                                ON CONFLICT (adapter_id) DO NOTHING""",
                                (adapter_id, digest, json.dumps(projection)))
                    cur.execute("""SELECT count(*),
                        bool_and(digest=projection->>'source_sha256'),
                        bool_and(projection->>'tenant_id'='synthetic-tenant')
                        FROM a1_adapter_shadow""")
                    self.assertEqual(cur.fetchone(), (6, True, True))
                    cur.execute("SAVEPOINT before_delete")
                    cur.execute("DELETE FROM a1_adapter_shadow")
                    cur.execute("SELECT count(*) FROM a1_adapter_shadow")
                    self.assertEqual(cur.fetchone()[0], 0)
                    cur.execute("ROLLBACK TO SAVEPOINT before_delete")
                    cur.execute("SELECT count(*) FROM a1_adapter_shadow")
                    self.assertEqual(cur.fetchone()[0], 6)
            with conn.cursor() as cur:
                cur.execute("SELECT to_regclass('pg_temp.a1_adapter_shadow')")
                self.assertIsNone(cur.fetchone()[0])


if __name__ == "__main__":
    unittest.main()

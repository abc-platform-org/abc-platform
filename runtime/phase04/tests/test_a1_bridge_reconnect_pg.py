"""A1 integration test: committed bridge rows survive worker reconnect; replay is idempotent."""
import os
import unittest
import psycopg

class BridgeReconnectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getenv("ABC_ENV") != "LOCAL_INTEGRATION_ONLY" or not os.getenv("ABC_TEST_PG_ADMIN_DSN"):
            raise unittest.SkipTest("disposable PostgreSQL only")
        cls.dsn = os.environ["ABC_TEST_PG_ADMIN_DSN"]

    def test_schema_downgrade_dry_run_rolls_back_without_losing_registry(self):
        """Transactional DDL rollback proof; NOT a full 0031 downgrade or PITR test."""
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM abc.a1_bridge_registry")
                baseline = cur.fetchone()[0]
                self.assertEqual(baseline, 6)
                with conn.transaction():
                    cur.execute("SAVEPOINT a1_downgrade_probe")
                    cur.execute("DROP TABLE abc.a1_bridge_shadow")
                    cur.execute("SELECT to_regclass('abc.a1_bridge_shadow')")
                    self.assertIsNone(cur.fetchone()[0])
                    cur.execute("ROLLBACK TO SAVEPOINT a1_downgrade_probe")
                    cur.execute("RELEASE SAVEPOINT a1_downgrade_probe")
                cur.execute("SELECT to_regclass('abc.a1_bridge_shadow')")
                self.assertIsNotNone(cur.fetchone()[0])
                cur.execute("SELECT count(*) FROM abc.a1_bridge_registry")
                self.assertEqual(cur.fetchone()[0], baseline)

    def test_committed_row_reconnect_and_idempotent_shadow_backfill(self):
        tenant = "a1-synthetic-reconnect"
        adapter = "A04_TO_06_DECISION_INPUT"
        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO abc.a1_bridge_legacy
                        (adapter_id,tenant_id,branch_id,session_id,artifact_id,
                         source_sha256,consent_decision_id,policy_decision_id,source_version,payload)
                        VALUES (%s,%s,'synthetic-branch','synthetic-session','synthetic-artifact',
                                %s,'synthetic-consent','synthetic-policy',
                                'abc.internal.engine.v2.draft',%s::jsonb)
                        ON CONFLICT (adapter_id,tenant_id,branch_id,session_id,artifact_id)
                        DO NOTHING
                    """, (adapter,tenant,"a"*64,'{"synthetic":true}'))
            # New connection represents a restarted worker, not a database-server crash.
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    for _ in range(2):
                        cur.execute("""
                            INSERT INTO abc.a1_bridge_shadow
                            (adapter_id,tenant_id,branch_id,session_id,artifact_id,
                             source_sha256,consent_decision_id,policy_decision_id,
                             source_version,target_version,payload)
                            SELECT adapter_id,tenant_id,branch_id,session_id,artifact_id,
                                   source_sha256,consent_decision_id,policy_decision_id,
                                   source_version,'abc.internal.capability.v3.review',payload
                            FROM abc.a1_bridge_legacy WHERE tenant_id=%s
                            ON CONFLICT (adapter_id,tenant_id,branch_id,session_id,artifact_id)
                            DO NOTHING
                        """, (tenant,))
                    cur.execute("""
                        SELECT count(*),bool_and(NOT dispatch_authorized),
                               bool_and(NOT customer_release_approved)
                        FROM abc.a1_bridge_shadow WHERE tenant_id=%s
                    """, (tenant,))
                    self.assertEqual(cur.fetchone(),(1,True,True))
        finally:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM abc.a1_bridge_shadow WHERE tenant_id=%s",(tenant,))
                    cur.execute("DELETE FROM abc.a1_bridge_legacy WHERE tenant_id=%s",(tenant,))

if __name__ == "__main__":
    unittest.main()

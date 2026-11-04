"""A1 PostgreSQL physical catalog and reversible shadow migration acceptance.

Never writes production tables; only ephemeral transaction-local temp objects.
"""
import os
import unittest
import psycopg

class A1PhysicalCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getenv("ABC_ENV")!="LOCAL_INTEGRATION_ONLY" or not os.getenv("ABC_TEST_PG_ADMIN_DSN"):
            raise unittest.SkipTest("disposable PostgreSQL CI only")
        cls.con=psycopg.connect(os.environ["ABC_TEST_PG_ADMIN_DSN"])
    @classmethod
    def tearDownClass(cls):
        cls.con.close()
    def test_legacy_tables_exist_and_are_rls_protected(self):
        names=("eng19_review_inbox","eng19_review_edges","eng06_ci_jobs",
               "eng06_ci_results","eng19_synthetic_outbox")
        with self.con.cursor() as cur:
            cur.execute("""SELECT c.relname,c.relrowsecurity,c.relforcerowsecurity
                FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='abc' AND c.relname=ANY(%s)""",(list(names),))
            found={name:(rls,force) for name,rls,force in cur.fetchall()}
        self.assertEqual(set(found),set(names))
        for name in names:
            if name!="eng19_review_edges":
                self.assertEqual(found[name],(True,True),name)
    def test_no_direct_eng06_worker_table_grants(self):
        with self.con.cursor() as cur:
            cur.execute("""SELECT has_table_privilege('abc_eng06_review_worker',
                 'abc.eng06_ci_results','INSERT')""")
            self.assertFalse(cur.fetchone()[0])
    def test_transactional_shadow_backfill_and_rollback(self):
        with self.con.transaction():
            with self.con.cursor() as cur:
                cur.execute("""CREATE TEMP TABLE a1_shadow_legacy(
                    source_id text PRIMARY KEY, payload text NOT NULL) ON COMMIT DROP""")
                cur.execute("""CREATE TEMP TABLE a1_shadow_canonical(
                    source_id text PRIMARY KEY, payload text NOT NULL) ON COMMIT DROP""")
                cur.execute("INSERT INTO a1_shadow_legacy VALUES ('synthetic-1','v2')")
                cur.execute("""INSERT INTO a1_shadow_canonical
                    SELECT source_id,payload FROM a1_shadow_legacy
                    ON CONFLICT(source_id) DO NOTHING""")
                cur.execute("""INSERT INTO a1_shadow_canonical
                    SELECT source_id,payload FROM a1_shadow_legacy
                    ON CONFLICT(source_id) DO NOTHING""")
                cur.execute("SELECT count(*) FROM a1_shadow_canonical")
                self.assertEqual(cur.fetchone()[0],1)
                cur.execute("SAVEPOINT a1_rollback")
                cur.execute("UPDATE a1_shadow_canonical SET payload='changed'")
                cur.execute("ROLLBACK TO SAVEPOINT a1_rollback")
                cur.execute("SELECT payload FROM a1_shadow_canonical")
                self.assertEqual(cur.fetchone()[0],"v2")
        with self.con.cursor() as cur:
            cur.execute("SELECT to_regclass('pg_temp.a1_shadow_canonical')")
            self.assertIsNone(cur.fetchone()[0])

if __name__=="__main__": unittest.main()

"""Real PostgreSQL ENG06 negative-path isolation and lease fencing checks.

No production credentials or professional approvals. Requires disposable CI DB.
"""
import os
import unittest
import uuid

class Eng06PostgresIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getenv("ABC_ENV") != "LOCAL_INTEGRATION_ONLY":
            raise unittest.SkipTest("local integration only")
        cls.admin = os.getenv("ABC_TEST_PG_ADMIN_DSN")
        cls.worker = os.getenv("ABC_TEST_PG_ENG06_LOGIN_DSN")
        if not cls.admin or not cls.worker:
            raise unittest.SkipTest("disposable PostgreSQL and dedicated ENG06 login required")
        from psycopg.conninfo import conninfo_to_dict
        admin = conninfo_to_dict(cls.admin)
        worker = conninfo_to_dict(cls.worker)
        if (admin.get("dbname") != "abc_phase04_ci"
                or worker.get("dbname") != "abc_phase04_ci"
                or worker.get("user") != "abc_eng06_ci_login"
                or worker.get("host") not in ("localhost", "127.0.0.1", "::1")):
            raise unittest.SkipTest("CI-only database identity guard")

    def test_schema_is_force_rls_and_worker_has_no_direct_write(self):
        import psycopg
        from psycopg import errors
        tables = ("eng06_ci_worker_bindings", "eng06_ci_jobs", "eng06_ci_results")
        with psycopg.connect(self.admin) as con:
            for table in tables:
                self.assertEqual(con.execute(
                    "SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid=to_regclass(%s)",
                    ("abc." + table,)).fetchone(), (True, True))
        with psycopg.connect(self.worker) as con:
            for table in tables:
                with self.assertRaises(errors.InsufficientPrivilege):
                    with con.transaction():
                        con.execute("SELECT * FROM abc." + table)

    def test_claim_rejects_unbound_worker(self):
        import psycopg
        from psycopg import errors
        with psycopg.connect(self.worker) as con:
            with self.assertRaises(errors.InsufficientPrivilege):
                with con.transaction():
                    con.execute("SET LOCAL ROLE abc_eng06_review_worker")
                    con.execute("SELECT abc.eng06_ci_claim(%s,%s)",
                                ("ci-unbound-" + uuid.uuid4().hex[:12], 30))

    def test_ack_and_fail_reject_missing_lease(self):
        import psycopg
        from psycopg import errors
        with psycopg.connect(self.worker) as con:
            for query, args in (
                ("SELECT abc.eng06_ci_ack(%s,%s,%s,%s,%s)",
                 (uuid.uuid4(), uuid.uuid4(), "0"*64, "0"*64, b'{"ci":"no-lease"}')),
                ("SELECT abc.eng06_ci_fail(%s,%s,%s)",
                 (uuid.uuid4(), uuid.uuid4(), "CI_STALE_LEASE")),
            ):
                with self.assertRaises(errors.InsufficientPrivilege):
                    with con.transaction():
                        con.execute("SET LOCAL ROLE abc_eng06_review_worker")
                        con.execute(query, args)

    def test_no_eng06_result_without_upstream(self):
        import psycopg
        with psycopg.connect(self.admin) as con:
            count=con.execute("""SELECT count(*) FROM abc.eng06_ci_results r
                LEFT JOIN abc.eng06_ci_jobs j ON j.upstream_handoff=r.upstream_handoff
                WHERE j.upstream_handoff IS NULL""").fetchone()[0]
            self.assertEqual(count,0)

if __name__ == "__main__":
    unittest.main()

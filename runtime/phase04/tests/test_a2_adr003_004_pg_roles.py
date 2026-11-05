"""A2 ADR-003/004: live *disposable* PostgreSQL privilege regression.

Uses ephemeral PostgreSQL16 provisioned by CI. No managed issuer, private
staging, professional authority or external security approval is inferred.
"""
import os
import unittest

import psycopg


class ADRPredeploymentSQLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dsn=os.environ["ABC_TEST_PG_ADMIN_DSN"]

    def q(self,sql,args=()):
        with psycopg.connect(self.dsn,autocommit=True) as con:
            return con.execute(sql,args).fetchall()

    def test_01_separate_worker_groups_are_nologin_noinherit_no_bypass(self):
        roles=("abc_eng03_worker","abc_eng04_worker","abc_eng05_worker",
               "abc_eng06_review_worker","abc_pipeline_worker")
        rows=self.q("""SELECT rolname,rolcanlogin,rolinherit,rolbypassrls,
                             rolsuper,rolcreaterole
                       FROM pg_roles WHERE rolname=ANY(%s)""",(list(roles),))
        self.assertEqual({r[0] for r in rows},set(roles))
        for row in rows:
            with self.subTest(role=row[0]):
                self.assertEqual(row[1:],(False,False,False,False,False))

    def test_02_force_rls_on_synthetic_sensitive_tables(self):
        names=("eng05_worker_bindings","eng06_ci_worker_bindings",
               "eng06_ci_jobs","eng06_ci_results","eng14_v2_replay_ledger",
               "g05_synthetic_cert_grants")
        rows=self.q("""SELECT c.relname,c.relrowsecurity,c.relforcerowsecurity
                       FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                       WHERE n.nspname='abc' AND c.relname=ANY(%s)""",
                    (list(names),))
        self.assertEqual({r[0] for r in rows},set(names))
        self.assertTrue(all(r[1] is True and r[2] is True for r in rows))

    def test_03_eng04_cannot_take_eng05_private_review_lease(self):
        self.assertFalse(self.q("""SELECT has_function_privilege(
           'abc_eng04_worker','abc.eng19_claim_synthetic(text,integer)','EXECUTE')""")[0][0])
        self.assertTrue(self.q("""SELECT has_function_privilege(
           'abc_eng05_worker','abc.eng19_claim_synthetic(text,integer)','EXECUTE')""")[0][0])

    def test_04_eng06_worker_lease_not_executable_by_eng04_or_eng05(self):
        for role in ("abc_eng04_worker","abc_eng05_worker",
                     "abc_pipeline_worker","abc_app"):
            with self.subTest(role=role):
                self.assertFalse(self.q("""SELECT has_function_privilege(
                    %s,'abc.eng06_ci_claim(text,integer)','EXECUTE')""",
                   (role,))[0][0])
        self.assertTrue(self.q("""SELECT has_function_privilege(
           'abc_eng06_review_worker','abc.eng06_ci_claim(text,integer)',
           'EXECUTE')""")[0][0])

    def test_05_old_unbound_eng14_g05_entrypoint_revoked(self):
        sig=("abc.eng14_g05_admit_and_claim(text,text,uuid,integer,text,"
             "text,text,text,text,text,text,uuid,timestamptz)")
        self.assertFalse(self.q("SELECT has_function_privilege('abc_app',%s,'EXECUTE')",
                                (sig,))[0][0])
        sig2=("abc.eng14_g05_cert_bound_admit_and_claim(text,text,uuid,"
              "integer,text,text,text,text,text,text,text,uuid,timestamptz,text)")
        self.assertTrue(self.q("SELECT has_function_privilege('abc_app',%s,'EXECUTE')",
                               (sig2,))[0][0])

    def test_06_replay_and_cert_registry_cannot_be_read_by_runtime_roles(self):
        for role in ("abc_app","abc_eng04_worker","abc_eng05_worker",
                     "abc_eng06_review_worker","abc_pipeline_worker"):
            for table in ("eng14_v2_replay_ledger","g05_synthetic_cert_grants",
                          "eng06_ci_results"):
                with self.subTest(role=role,table=table):
                    self.assertFalse(self.q("SELECT has_table_privilege(%s,%s,'SELECT')",
                        (role,"abc."+table))[0][0])

    def test_07_actual_wrong_role_read_eng06_results_is_denied(self):
        with psycopg.connect(self.dsn) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                with con.transaction():
                    con.execute("SET LOCAL ROLE abc_eng04_worker")
                    con.execute("SELECT * FROM abc.eng06_ci_results LIMIT 1")

    def test_08_actual_abc_app_cannot_read_operator_cert_grants(self):
        with psycopg.connect(self.dsn) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                with con.transaction():
                    con.execute("SET LOCAL ROLE abc_app")
                    con.execute("SELECT * FROM abc.g05_synthetic_cert_grants LIMIT 1")

    def test_09_operator_only_managed_tenant_mode_mutations(self):
        for role in ("abc_app","abc_eng04_worker","abc_eng05_worker"):
            with self.subTest(role=role):
                self.assertFalse(self.q("SELECT has_table_privilege(%s,"
                        "'abc.eng14_tenant_workload_mode','UPDATE')",
                        (role,))[0][0])

    def test_10_runtime_roles_have_no_direct_insert_into_eng06_jobs(self):
        for role in ("abc_app","abc_eng04_worker","abc_eng05_worker",
                     "abc_eng06_review_worker"):
            with self.subTest(role=role):
                self.assertFalse(self.q("SELECT has_table_privilege(%s,"
                        "'abc.eng06_ci_jobs','INSERT')",(role,))[0][0])


if __name__=="__main__":
    unittest.main()

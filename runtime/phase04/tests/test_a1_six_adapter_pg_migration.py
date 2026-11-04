"""A1 six-adapter real PostgreSQL backfill/dual-read/rollback acceptance.
All writes are disposable test-only, rolled back in one outer transaction.
"""
import hashlib
import json
import os
import unittest
import psycopg

IDS=("A04_TO_06_DECISION_INPUT","A04_TO_07_LOOK_SPEC_INPUT",
     "A05_TO_06_DECISION_EVIDENCE","A06_TO_15_PLAN_CANDIDATE",
     "A04_PIXEL_TO_11_QA_EVIDENCE","A06_SOURCE_TO_16_REVIEW_EVIDENCE")
class RollbackProbe(Exception): pass

class A1BridgePostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getenv("ABC_ENV")!="LOCAL_INTEGRATION_ONLY" or not os.getenv("ABC_TEST_PG_ADMIN_DSN"):
            raise unittest.SkipTest("disposable PostgreSQL only")
        cls.dsn=os.environ["ABC_TEST_PG_ADMIN_DSN"]

    def test_six_adapters_backfill_dual_read_idempotency_and_rollback(self):
        tenant="a1-synthetic-test-only"
        with psycopg.connect(self.dsn) as con:
            with con.cursor() as cur:
                cur.execute("SELECT adapter_id,enabled,customer_release_approved FROM abc.a1_bridge_registry")
                rows=cur.fetchall()
                self.assertEqual({r[0] for r in rows},set(IDS))
                self.assertTrue(all(not r[1] and not r[2] for r in rows))
            try:
                with con.transaction():
                    with con.cursor() as cur:
                        for idx,adapter in enumerate(IDS):
                            payload={"synthetic":True,"adapter":adapter}
                            digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
                            cur.execute("""INSERT INTO abc.a1_bridge_legacy(
                              adapter_id,tenant_id,branch_id,session_id,artifact_id,
                              source_sha256,consent_decision_id,policy_decision_id,
                              source_version,payload)
                              VALUES(%s,%s,'test-branch','test-session',%s,%s,
                              'consent-test','policy-test','abc.internal.engine.v2.draft',%s::jsonb)""",
                              (adapter,tenant,str(idx),digest,json.dumps(payload)))
                        backfill="""INSERT INTO abc.a1_bridge_shadow(
                          adapter_id,tenant_id,branch_id,session_id,artifact_id,
                          source_sha256,consent_decision_id,policy_decision_id,
                          source_version,target_version,payload)
                          SELECT adapter_id,tenant_id,branch_id,session_id,artifact_id,
                          source_sha256,consent_decision_id,policy_decision_id,
                          source_version,'abc.internal.capability.v3.review',payload
                          FROM abc.a1_bridge_legacy WHERE tenant_id=%s
                          ON CONFLICT(adapter_id,tenant_id,branch_id,session_id,artifact_id)
                          DO NOTHING"""
                        cur.execute(backfill,(tenant,))
                        cur.execute(backfill,(tenant,))
                        cur.execute("""SELECT l.adapter_id,l.source_sha256,s.source_sha256,
                          l.payload=s.payload,s.dispatch_authorized,s.customer_release_approved
                          FROM abc.a1_bridge_legacy l JOIN abc.a1_bridge_shadow s
                          USING(adapter_id,tenant_id,branch_id,session_id,artifact_id)
                          WHERE l.tenant_id=%s""",(tenant,))
                        compared=cur.fetchall()
                        self.assertEqual(len(compared),6)
                        self.assertTrue(all(a==b and same and not dispatch and not release
                            for _,a,b,same,dispatch,release in compared))
                        cur.execute("SELECT count(*) FROM abc.a1_bridge_shadow WHERE tenant_id=%s",(tenant,))
                        self.assertEqual(cur.fetchone()[0],6)
                        raise RollbackProbe()
            except RollbackProbe:
                pass
            with con.cursor() as cur:
                for table in ("a1_bridge_legacy","a1_bridge_shadow"):
                    cur.execute("SELECT count(*) FROM abc."+table+" WHERE tenant_id=%s",(tenant,))
                    self.assertEqual(cur.fetchone()[0],0)

    def test_runtime_roles_have_no_bridge_table_access(self):
        with psycopg.connect(self.dsn) as con:
            with con.cursor() as cur:
                for role in ("abc_eng04_worker","abc_eng05_worker","abc_eng06_review_worker"):
                    cur.execute("""SELECT has_table_privilege(%s,'abc.a1_bridge_shadow','SELECT'),
                        has_table_privilege(%s,'abc.a1_bridge_shadow','INSERT')""",(role,role))
                    self.assertEqual(cur.fetchone(),(False,False))

if __name__=="__main__":
    unittest.main()

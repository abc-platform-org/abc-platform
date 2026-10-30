"""Real PostgreSQL16 multi-connection and multi-thread replay safety tests.

Only disposable CI tenants/tokens. Tests never issue real JWTs or certificates.
"""
import os
import uuid
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone

import psycopg
from psycopg.rows import dict_row

from abc_foundation.distributed_replay import PostgresReplayLedger
from abc_foundation.pg_store import PostgresStore
from abc_foundation.store import DomainError


class DurableReplayLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=os.environ.get("ABC_TEST_PG_DSN")
        cls.admin=os.environ.get("ABC_TEST_PG_ADMIN_DSN")
        if not (cls.app and cls.admin and os.environ.get("ABC_ENV")=="LOCAL_INTEGRATION_ONLY"):
            raise unittest.SkipTest("CI-only PostgreSQL16 test fixture required")
        cls.tenant="replay-"+uuid.uuid4().hex
        cls.other="replay-"+uuid.uuid4().hex
        with psycopg.connect(cls.admin,autocommit=True) as con:
            for tenant in (cls.tenant,cls.other):
                con.execute("INSERT INTO abc.tenants(tenant_id) VALUES(%s)",(tenant,))
        cls.ledger=PostgresReplayLedger(PostgresStore(cls.app))
        cls.exp=datetime.now(timezone.utc)+timedelta(seconds=110)

    def claim(self,*,tenant=None,jti=None,expires=None):
        return self.ledger.claim(tenant_id=tenant or self.tenant,
             issuer="https://oidc.abc.example.test",
             audience="abc-engine-v2",
             jti=jti or str(uuid.uuid4()),
             expires_at=expires or self.exp)

    def test_first_token_passes_second_same_token_rejected(self):
        jti=str(uuid.uuid4())
        self.assertTrue(self.claim(jti=jti)["admitted"])
        with self.assertRaises(DomainError) as ctx:
            self.claim(jti=jti)
        self.assertEqual(ctx.exception.code,"distributed_replay_detected")

    def test_atomic_eight_distinct_database_connections(self):
        jti=str(uuid.uuid4())
        def run(_i):
            try:
                return self.claim(jti=jti)["admitted"]
            except DomainError as e:
                return e.code
        with ThreadPoolExecutor(max_workers=8) as executor:
            results=list(executor.map(run,range(8)))
        self.assertEqual(results.count(True),1,results)
        self.assertEqual(results.count("distributed_replay_detected"),7,results)

    def test_replay_across_tenant_boundaries_rejected(self):
        jti=str(uuid.uuid4())
        self.assertTrue(self.claim(tenant=self.tenant,jti=jti)["admitted"])
        with self.assertRaises(DomainError) as ctx:
            self.claim(tenant=self.other,jti=jti)
        self.assertEqual(ctx.exception.code,"distributed_replay_detected")

    def test_expiry_invalid_uuid_and_scope_rejected(self):
        for expiry in (datetime.now(timezone.utc)-timedelta(seconds=2),
                       datetime.now(timezone.utc)+timedelta(hours=2)):
            with self.assertRaises(DomainError):
                self.claim(expires=expiry)
        for jti in ("",str(uuid.uuid1()),"not-a-uuid"):
            with self.assertRaises(DomainError):
                self.claim(jti=jti)
        with self.assertRaises(DomainError):
            self.ledger.claim(tenant_id=self.tenant,issuer="http://bad.local",
                audience="abc-engine-v2",jti=str(uuid.uuid4()),
                expires_at=self.exp)

    def test_untrusted_tenant_claim_and_direct_dml_rejected(self):
        # The function additionally checks the transaction-scoped active
        # authenticated tenant. A direct execution without tenant GUC fails.
        with psycopg.connect(self.app,row_factory=dict_row) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("SELECT abc.eng14_claim_v2_jti(%s,%s,%s,%s,%s)",
                    (self.tenant,"https://oidc.abc.example.test",
                     "abc-engine-v2",uuid.uuid4(),self.exp))
        with psycopg.connect(self.app,row_factory=dict_row) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("SELECT * FROM abc.eng14_v2_replay_ledger")
        with psycopg.connect(self.app,row_factory=dict_row) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("""INSERT INTO abc.eng14_v2_replay_ledger
                   (replay_digest,tenant_id,issuer,audience,issued_jti,expires_at)
                   VALUES(%s,%s,%s,%s,%s,%s)""",(
                     "a"*64,self.tenant,"https://oidc.abc.example.test",
                     "abc-engine-v2",uuid.uuid4(),self.exp))

    def test_managed_tenant_rejects_password_login_without_physical_client_cert(self):
        with psycopg.connect(self.admin,autocommit=True) as con:
            con.execute("""INSERT INTO abc.eng14_tenant_workload_mode
                 (tenant_id,managed_required,activated_at,activated_by)
                 VALUES(%s,true,clock_timestamp(),'CI_TEST_ONLY')""",(self.other,))
        with self.assertRaises(DomainError) as ctx:
            self.claim(tenant=self.other,jti=str(uuid.uuid4()))
        self.assertEqual(ctx.exception.code,"distributed_replay_ledger_unavailable")

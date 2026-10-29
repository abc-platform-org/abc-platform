"""Real PostgreSQL ENG01 command receipt: atomic fingerprint, CAS, RLS and retry."""
import os
import uuid
import unittest
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor

import psycopg

from abc_foundation.eng01_gateway import TypedCheckpointGateway
from abc_foundation.eng01_pg import ENG01PostgresCommandStore
from abc_foundation.oidc import Principal
from abc_foundation.store import DomainError

ISS="https://identity.example.test/realms/abc"
PG=os.getenv("ABC_TEST_PG_DSN")
ADMIN=os.getenv("ABC_TEST_PG_ADMIN_DSN")
WORKER=os.getenv("ABC_TEST_PG_WORKER_DSN")


@unittest.skipUnless(PG and ADMIN and WORKER,"disposable PostgreSQL required")
class AtomicCommandPortTests(unittest.TestCase):
    def setUp(self):
        suffix=uuid.uuid4().hex[:12]
        self.tenant="egw-tenant-"+suffix
        self.branch="egw-branch-"+suffix
        self.subject="egw-subject-"+suffix
        self.p=Principal(self.subject,ISS)
        self.store=ENG01PostgresCommandStore(PG)
        self.gateway=TypedCheckpointGateway(self.store)
        with psycopg.connect(ADMIN) as con:
            con.execute("INSERT INTO abc.tenants VALUES(%s)",(self.tenant,))
            con.execute("INSERT INTO abc.branches VALUES(%s,%s)",(self.tenant,self.branch))
            con.execute("""INSERT INTO abc.memberships(issuer,subject,tenant_id,branch_id,role,active)
                           VALUES(%s,%s,%s,%s,'SPECIALIST',true)""",
                        (ISS,self.subject,self.tenant,self.branch))
        session=self.store.create(self.p,{"branch_id":self.branch,
                    "scope":"IN_SALON_SHARED_SCREEN"},"egw-create-"+suffix)
        self.sid=session["session_id"]
        self.command_id=str(uuid.uuid4())
        self.cmd={
            "command_id":self.command_id,"engine_id":"ENG-01",
            "contract_version":"1.0.0-draft","correlation_id":str(uuid.uuid4()),
            "tenant_id":self.tenant,"branch_id":self.branch,
            "session_id":self.sid,
            "actor":{"user_id":self.subject,"role":"SPECIALIST"},
            "input_schema_id":"abc.internal.eng01.checkpoint.v0",
            "input_ref":"checkpoint:pause",
            "idempotency_key":self.command_id,
            "requested_at":datetime.now(timezone.utc).isoformat(),
            "expected_state_version":0
        }

    def execute(self,patch=None,principal=None):
        return self.gateway.execute(principal or self.p,{**self.cmd,**(patch or {})})

    def test_atomic_create_receipt_audit_and_replay(self):
        a=self.execute()
        self.assertEqual(a,self.execute())
        with psycopg.connect(ADMIN) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM abc.eng01_command_receipts WHERE session_id=%s",(self.sid,)).fetchone()[0],1)
            self.assertEqual(con.execute("SELECT count(*) FROM abc.state_audit WHERE session_id=%s",(self.sid,)).fetchone()[0],1)
            self.assertEqual(con.execute("SELECT state,checkpoint,state_version FROM abc.sessions WHERE session_id=%s",(self.sid,)).fetchone(),("PAUSED","CREATED",1))

    def test_same_command_changed_metadata_never_replays(self):
        self.execute()
        for patch in (
            {"correlation_id":str(uuid.uuid4())},
            {"deadline_at":(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()},
            {"requested_at":(datetime.now(timezone.utc)-timedelta(seconds=2)).isoformat()},
        ):
            with self.subTest(patch=patch),self.assertRaises(DomainError) as ctx:
                self.execute(patch)
            self.assertEqual(ctx.exception.status,409)

    def test_parallel_single_commit(self):
        with ThreadPoolExecutor(max_workers=6) as executor:
            outcomes=list(executor.map(lambda _:self.execute(),range(6)))
        self.assertEqual(len(outcomes),6)
        self.assertTrue(all(r==outcomes[0] for r in outcomes))
        with psycopg.connect(ADMIN) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM abc.eng01_command_receipts WHERE session_id=%s",(self.sid,)).fetchone()[0],1)

    def test_stale_key_cannot_apply_second_pause(self):
        self.execute()
        cmd=str(uuid.uuid4())
        with self.assertRaises(DomainError) as ctx:
            self.execute({"command_id":cmd,"idempotency_key":cmd})
        self.assertEqual(ctx.exception.status,409)

    def test_revoked_membership_denied_even_to_old_receipt(self):
        self.execute()
        with psycopg.connect(ADMIN) as con:
            con.execute("UPDATE abc.memberships SET active=false WHERE subject=%s",(self.subject,))
        with self.assertRaises(DomainError) as ctx:
            self.execute()
        self.assertIn(ctx.exception.status,(403,404))

    def test_worker_cannot_read_engine_command_receipts(self):
        with psycopg.connect(WORKER) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("SELECT * FROM abc.eng01_command_receipts LIMIT 1")

    def test_engine_receipts_rls_denies_unscoped_read(self):
        self.execute()
        with psycopg.connect(PG) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM abc.eng01_command_receipts").fetchone()[0],0)

"""Against disposable PostgreSQL 16 CI service. Not a deployed provider test."""
import os
import uuid
import json
import unittest
from concurrent.futures import ThreadPoolExecutor

import psycopg
from abc_foundation.oidc import Principal
from abc_foundation.pg_store import PostgresStore
from abc_foundation.store import DomainError

ISS="https://identity.example.test/realms/abc"
DSN=os.getenv("ABC_TEST_PG_DSN")
ADMIN=os.getenv("ABC_TEST_PG_ADMIN_DSN")
SCOPE="IN_SALON_SHARED_SCREEN"

@unittest.skipUnless(DSN and ADMIN,"requires disposable Postgres service")
class PostgresRuntimeTests(unittest.TestCase):
    def setUp(self):
        identifier=uuid.uuid4().hex[:14]
        self.tenant="tenant-"+identifier
        self.branch="branch-"+identifier
        self.subject="staff-"+identifier
        self.principal=Principal(self.subject,ISS)
        self.store=PostgresStore(DSN)
        with psycopg.connect(ADMIN) as con:
            con.execute("INSERT INTO abc.tenants VALUES(%s)",(self.tenant,))
            con.execute("INSERT INTO abc.branches VALUES(%s,%s)",(self.tenant,self.branch))
            con.execute("""INSERT INTO abc.memberships
                (issuer,subject,tenant_id,branch_id,role,active,verified_qualification)
                VALUES(%s,%s,%s,%s,'SPECIALIST',true,false)""",
                (ISS,self.subject,self.tenant,self.branch))

    def body(self): return {"branch_id":self.branch,"scope":SCOPE}
    def create(self,key="intent-0001"): return self.store.create(self.principal,self.body(),key)

    def test_pg_session_creation_reads_in_exact_scope(self):
        result=self.create()
        self.assertEqual(result["tenant_id"],self.tenant)
        self.assertEqual(result["specialist_id"],self.subject)
        self.assertEqual(result["state_version"],0)
        self.assertEqual(self.store.get(self.principal,result["session_id"]),result)

    def test_pg_idempotent_replay_is_exact_and_outbox_once(self):
        a=self.create();b=self.create()
        self.assertEqual(a,b)
        with psycopg.connect(ADMIN) as con:
            count=con.execute("SELECT count(*) FROM abc.outbox WHERE aggregate_id=%s",(a["session_id"],)).fetchone()[0]
        self.assertEqual(count,1)

    def test_pg_same_key_changed_payload_conflicts(self):
        self.create()
        with self.assertRaises(DomainError) as e:
            self.store.create(self.principal,{**self.body(),"service_id":"different"},"intent-0001")
        self.assertEqual(e.exception.status,409)

    def test_pg_unassigned_subject_cannot_create_or_read(self):
        bad=Principal("other-subject",ISS)
        sid=self.create()["session_id"]
        with self.assertRaises(DomainError) as e:
            self.store.create(bad,self.body(),"intent-bad")
        self.assertEqual(e.exception.status,403)
        with self.assertRaises(DomainError) as e:
            self.store.get(bad,sid)
        self.assertEqual(e.exception.status,404)

    def test_pg_wrong_issuer_cannot_access(self):
        bad=Principal(self.subject,"https://other-issuer.example.test/")
        sid=self.create()["session_id"]
        with self.assertRaises(DomainError):
            self.store.get(bad,sid)

    def test_pg_revoked_membership_blocks_future_reads_and_create(self):
        sid=self.create()["session_id"]
        with psycopg.connect(ADMIN) as con:
            con.execute("UPDATE abc.memberships SET active=false WHERE subject=%s",(self.subject,))
        with self.assertRaises(DomainError) as e:
            self.store.get(self.principal,sid)
        self.assertEqual(e.exception.status,404)
        with self.assertRaises(DomainError) as e:
            self.store.create(self.principal,self.body(),"intent-revoked")
        self.assertEqual(e.exception.status,403)

    def test_pg_non_specialist_role_not_authorized_by_job_title(self):
        with psycopg.connect(ADMIN) as con:
            con.execute("UPDATE abc.memberships SET role='SALON_MANAGER' WHERE subject=%s",(self.subject,))
        with self.assertRaises(DomainError) as e:
            self.store.create(self.principal,self.body(),"intent-manager")
        self.assertEqual(e.exception.status,403)

    def test_pg_rls_denies_no_context_even_to_authenticated_db_role(self):
        sid=self.create()["session_id"]
        with psycopg.connect(DSN) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM abc.sessions WHERE session_id=%s",(sid,)).fetchone()[0],0)
            self.assertEqual(con.execute("SELECT count(*) FROM abc.memberships WHERE subject=%s",(self.subject,)).fetchone()[0],0)
            con.execute("SELECT set_config('abc.tenant',%s,true)",("wrong-tenant",))
            con.execute("SELECT set_config('abc.branch',%s,true)",(self.branch,))
            con.execute("SELECT set_config('abc.subject',%s,true)",(self.subject,))
            self.assertEqual(con.execute("SELECT count(*) FROM abc.sessions WHERE session_id=%s",(sid,)).fetchone()[0],0)

    def test_pg_consent_evidence_writable_only_by_future_verification_service(self):
        with psycopg.connect(DSN) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("""INSERT INTO abc.consent_evidence
                    (consent_id,tenant_id,branch_id,session_id,client_id,status,purpose,
                    evidence_digest,disclosure_version,retention_policy_id)
                    VALUES(%s,%s,%s,%s,%s,'PENDING_VERIFICATION',%s,%s,%s,%s)""",
                    (uuid.uuid4(),self.tenant,self.branch,uuid.uuid4(),"client-1",
                     ["AI_PROCESSING"],"fake","v1","retention-1"))

    def test_pg_same_intent_concurrency_returns_one_session(self):
        def call(_): return self.create("race-intent-key")
        with ThreadPoolExecutor(max_workers=5) as pool:
            results=list(pool.map(call,range(5)))
        self.assertTrue(all(r==results[0] for r in results))
        with psycopg.connect(ADMIN) as con:
            count=con.execute("SELECT count(*) FROM abc.sessions WHERE tenant_id=%s",(self.tenant,)).fetchone()[0]
        self.assertEqual(count,1)

    def test_pg_event_conforms_to_canonical_base_envelope(self):
        sid=self.create()["session_id"]
        with psycopg.connect(ADMIN) as con:
            doc=con.execute("SELECT event_json FROM abc.outbox WHERE aggregate_id=%s",(sid,)).fetchone()[0]
        self.assertEqual(doc["event_type"],"SESSION_CREATED")
        self.assertEqual(doc["producer_engine_id"],"ENG-01")
        self.assertEqual(doc["tenant_id"],self.tenant)
        self.assertEqual(doc["aggregate_version"],0)
        self.assertEqual(doc["payload"]["branch_id"],self.branch)

"""PostgreSQL outbox worker delivery and isolation test matrix, synthetic events only."""
import os
import uuid
import unittest
from concurrent.futures import ThreadPoolExecutor

import psycopg

from abc_foundation.pg_outbox import OutboxDispatcher
from abc_foundation.pg_store import PostgresStore
from abc_foundation.oidc import Principal
from abc_foundation.store import DomainError

ISS = "https://identity.example.test/realms/abc"
ADMIN = os.getenv("ABC_TEST_PG_ADMIN_DSN")
APP = os.getenv("ABC_TEST_PG_DSN")
WORKER = os.getenv("ABC_TEST_PG_WORKER_DSN")


@unittest.skipUnless(ADMIN and APP and WORKER, "needs ephemeral PostgreSQL worker role")
class OutboxIntegrationTests(unittest.TestCase):
    def setUp(self):
        suffix = uuid.uuid4().hex[:12]
        self.tenant, self.branch, self.subject = "tenant-"+suffix, "branch-"+suffix, "specialist-"+suffix
        self.principal = Principal(self.subject, ISS)
        self.pg = PostgresStore(APP)
        self.worker = OutboxDispatcher(WORKER)
        self.consumer = "fixture-consumer-"+suffix
        with psycopg.connect(ADMIN) as con:
            con.execute("INSERT INTO abc.tenants VALUES (%s)", (self.tenant,))
            con.execute("INSERT INTO abc.branches VALUES (%s,%s)", (self.tenant,self.branch))
            con.execute("""INSERT INTO abc.memberships(issuer,subject,tenant_id,branch_id,role,active)
                VALUES (%s,%s,%s,%s,'SPECIALIST',true)""",
                (ISS,self.subject,self.tenant,self.branch))
            con.execute("""INSERT INTO abc.worker_subscriptions
                (consumer_id,tenant_id,event_type,active)
                VALUES(%s,%s,'SESSION_CREATED',true)""",
                (self.consumer,self.tenant))

    def create(self,key):
        return self.pg.create(self.principal,{"branch_id":self.branch,"scope":"IN_SALON_SHARED_SCREEN"},key)

    def test_worker_registers_once_and_replays_only_one_event(self):
        session=self.create("create-"+uuid.uuid4().hex)
        self.assertEqual(self.worker.register(self.consumer),1)
        self.assertEqual(self.worker.register(self.consumer),0)
        leased=self.worker.lease(self.consumer)
        self.assertEqual(leased["event"]["event_type"],"SESSION_CREATED")
        self.assertEqual(leased["event"]["session_id"],session["session_id"])
        self.assertEqual(self.worker.complete(self.consumer,leased["event_id"],leased["lease_token"],succeeded=True),"ACKED")
        self.assertIsNone(self.worker.lease(self.consumer))
        self.assertEqual(self.worker.register(self.consumer),0)

    def test_ack_is_idempotent_only_for_original_token(self):
        self.create("create-"+uuid.uuid4().hex)
        self.worker.register(self.consumer)
        leased=self.worker.lease(self.consumer)
        self.worker.complete(self.consumer,leased["event_id"],leased["lease_token"],succeeded=True)
        self.assertEqual(self.worker.complete(self.consumer,leased["event_id"],leased["lease_token"],succeeded=True),"ACKED")
        with self.assertRaises(DomainError) as exc:
            self.worker.complete(self.consumer,leased["event_id"],str(uuid.uuid4()),succeeded=True)
        self.assertEqual(exc.exception.status,409)

    def test_crashed_lease_recovered_but_old_worker_cannot_ack(self):
        self.create("create-"+uuid.uuid4().hex)
        self.worker.register(self.consumer)
        first=self.worker.lease(self.consumer)
        self.assertIsNone(self.worker.lease(self.consumer))
        with psycopg.connect(ADMIN) as con:
            con.execute("""UPDATE abc.event_delivery SET lease_until=clock_timestamp()-interval '1 second'
                WHERE consumer_id=%s AND event_id=%s""",(self.consumer,first["event_id"]))
        restarted=OutboxDispatcher(WORKER)
        second=restarted.lease(self.consumer)
        self.assertEqual(second["attempt"],2)
        self.assertNotEqual(first["lease_token"],second["lease_token"])
        with self.assertRaises(DomainError) as exc:
            restarted.complete(self.consumer,first["event_id"],first["lease_token"],succeeded=True)
        self.assertEqual(exc.exception.status,409)
        restarted.complete(self.consumer,second["event_id"],second["lease_token"],succeeded=True)
        self.assertIsNone(restarted.lease(self.consumer))

    def test_three_failures_dead_letter_without_indefinite_retry(self):
        self.create("create-"+uuid.uuid4().hex)
        self.worker.register(self.consumer)
        for i in range(3):
            leased=self.worker.lease(self.consumer)
            self.assertEqual(leased["attempt"],i+1)
            state=self.worker.complete(self.consumer,leased["event_id"],leased["lease_token"],
                                       succeeded=False,failure_code="RETRYABLE_FIXTURE")
            self.assertEqual(state,"DLQ" if i==2 else "PENDING")
            with psycopg.connect(ADMIN) as con:
                con.execute("""UPDATE abc.event_delivery SET next_attempt_at=clock_timestamp()-interval '1 second'
                      WHERE consumer_id=%s AND event_id=%s""",(self.consumer,leased["event_id"]))
        self.assertIsNone(self.worker.lease(self.consumer))
        with psycopg.connect(ADMIN) as con:
            record=con.execute("""SELECT state,attempts,error_code FROM abc.event_delivery
                WHERE consumer_id=%s""",(self.consumer,)).fetchone()
        self.assertEqual(record,("DLQ",3,"RETRYABLE_FIXTURE"))

    def test_two_workers_cannot_lease_same_event_concurrently(self):
        self.create("create-"+uuid.uuid4().hex)
        self.worker.register(self.consumer)
        with ThreadPoolExecutor(max_workers=8) as pool:
            claims=list(pool.map(lambda _:OutboxDispatcher(WORKER).lease(self.consumer),range(8)))
        self.assertEqual(sum(x is not None for x in claims),1)

    def test_different_consumer_receives_independent_ack(self):
        self.create("create-"+uuid.uuid4().hex)
        second=self.consumer+"-2"
        with psycopg.connect(ADMIN) as con:
            con.execute("""INSERT INTO abc.worker_subscriptions
                    (consumer_id,tenant_id,event_type,active)
                    VALUES(%s,%s,'SESSION_CREATED',true)""",(second,self.tenant))
        self.worker.register(self.consumer)
        self.worker.register(second)
        first=self.worker.lease(self.consumer)
        self.worker.complete(self.consumer,first["event_id"],first["lease_token"],succeeded=True)
        alternative=self.worker.lease(second)
        self.assertEqual(first["event_id"],alternative["event_id"])
        self.worker.complete(second,alternative["event_id"],alternative["lease_token"],succeeded=True)
        self.assertIsNone(self.worker.lease(second))

    def test_late_event_creation_is_discovered_by_reconciliation(self):
        self.assertEqual(self.worker.register(self.consumer),0)
        self.create("create-"+uuid.uuid4().hex)
        self.assertEqual(self.worker.register(self.consumer),1)

    def test_invalid_consumer_and_worker_token_fail_closed(self):
        with self.assertRaises(DomainError):
            self.worker.register("../unauthorized")
        with self.assertRaises(DomainError):
            self.worker.lease(self.consumer,seconds=0)
        with self.assertRaises(DomainError):
            self.worker.complete(self.consumer,str(uuid.uuid4()),str(uuid.uuid4()),succeeded=True)

    def test_worker_has_no_session_or_consent_access(self):
        with psycopg.connect(WORKER) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("SELECT * FROM abc.sessions LIMIT 1")
        with psycopg.connect(WORKER) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("SELECT * FROM abc.consent_evidence LIMIT 1")

    def test_http_role_cannot_read_delivery_or_outbox(self):
        with psycopg.connect(APP) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("SELECT * FROM abc.event_delivery LIMIT 1")
        with psycopg.connect(APP) as con:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                con.execute("SELECT * FROM abc.outbox LIMIT 1")


# Additional tenant-boundary adversarial tests without client images.
def _test_outbox_tenant_cross_event_never_delivered(self):
    sid=self.create("event-"+uuid.uuid4().hex)
    # Unrelated tenant creates a second event with a different active specialist.
    other=uuid.uuid4().hex[:12]
    t,b,u="tenant-"+other,"branch-"+other,"specialist-"+other
    with psycopg.connect(ADMIN) as con:
        con.execute("INSERT INTO abc.tenants VALUES(%s)",(t,))
        con.execute("INSERT INTO abc.branches VALUES(%s,%s)",(t,b))
        con.execute("""INSERT INTO abc.memberships(issuer,subject,tenant_id,branch_id,role,active)
            VALUES(%s,%s,%s,%s,'SPECIALIST',true)""",(ISS,u,t,b))
    another=PostgresStore(APP).create(Principal(u,ISS),
        {"branch_id":b,"scope":"IN_SALON_SHARED_SCREEN"},"isolation-"+other)
    self.assertEqual(self.worker.register(self.consumer),1)
    leased=self.worker.lease(self.consumer)
    self.assertEqual(leased["tenant_id"],self.tenant)
    self.assertEqual(leased["event"]["session_id"],sid["session_id"])
    self.assertNotEqual(leased["event"]["session_id"],another["session_id"])
    self.worker.complete(self.consumer,leased["event_id"],leased["lease_token"],succeeded=True)
    self.assertIsNone(self.worker.lease(self.consumer))

def _test_outbox_subscription_revocation_fences_completion(self):
    self.create("event-"+uuid.uuid4().hex)
    self.worker.register(self.consumer)
    first=self.worker.lease(self.consumer)
    with psycopg.connect(ADMIN) as con:
        con.execute("UPDATE abc.worker_subscriptions SET active=false WHERE consumer_id=%s",(self.consumer,))
    with self.assertRaises(DomainError) as ex:
        self.worker.complete(self.consumer,first["event_id"],first["lease_token"],succeeded=True)
    self.assertEqual(ex.exception.status,403)
    with self.assertRaises(DomainError):
        self.worker.register(self.consumer)
    with self.assertRaises(DomainError):
        self.worker.lease(self.consumer)

OutboxIntegrationTests.test_outbox_tenant_cross_event_never_delivered=_test_outbox_tenant_cross_event_never_delivered
OutboxIntegrationTests.test_outbox_subscription_revocation_fences_completion=_test_outbox_subscription_revocation_fences_completion

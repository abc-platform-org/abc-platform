"""A2-G06 real PostgreSQL resilience acceptance for the independent ENG06 review worker.

Uses the actual SQL Claim/Lease/ACK/Fail brokers and the fixture's real
ENG05 result -> blocked ENG06 review boundary. No automated professional
release, paid inference, hosted workloads or real client information.

G06-01..06 cover durable queue, lease fencing, process crash, bounded retry,
concurrent workers, revocation, fail-closed storage unavailability, and
digest/outbox immutability. G06-07 DB restart runs in its own CI probe.
"""
import hashlib
import json
import os
import subprocess
import sys
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import psycopg

from abc_foundation.eng06_review_worker import SyntheticEng06ReviewWorker
from abc_foundation.pg_store import PostgresStore
from abc_foundation.eng05_review_worker import canonical_bytes
from abc_foundation.store import DomainError
from test_eng06_pg_positive_e2e import Eng06PositivePostgresTests


class G06DurableRecovery(Eng06PositivePostgresTests):
    def _row(self):
        with psycopg.connect(self.admin_dsn()) as con:
            return con.execute("""SELECT status,attempts,lease_token,
                     lease_until,available_at,failure_code
                     FROM abc.eng06_ci_jobs WHERE upstream_handoff=%s""",
                               (self.handoff,)).fetchone()

    @staticmethod
    def admin_dsn():
        return os.environ["ABC_TEST_PG_ADMIN_DSN"]

    @staticmethod
    def worker_dsn():
        return os.environ["ABC_TEST_PG_ENG06_LOGIN_DSN"]

    def _expire(self):
        with psycopg.connect(self.admin_dsn()) as con:
            con.execute("""UPDATE abc.eng06_ci_jobs
                   SET lease_until=clock_timestamp()-interval '1 second'
                   WHERE upstream_handoff=%s AND status='LEASED'""",
                        (self.handoff,))

    def _make_due(self):
        with psycopg.connect(self.admin_dsn()) as con:
            con.execute("""UPDATE abc.eng06_ci_jobs
                   SET available_at=clock_timestamp()-interval '1 second'
                   WHERE upstream_handoff=%s AND status='QUEUED'""",
                        (self.handoff,))

    def _count(self):
        with psycopg.connect(self.admin_dsn()) as con:
            return con.execute("""SELECT count(*)
                   FROM abc.eng06_ci_results WHERE upstream_handoff=%s""",
                               (self.handoff,)).fetchone()[0]

    def _outbox(self):
        with psycopg.connect(self.admin_dsn()) as con:
            return con.execute("""SELECT status,artifact_sha256
                    FROM abc.eng19_synthetic_outbox WHERE handoff_id=%s""",
                               (self.handoff,)).fetchone()

    def test_g06_01_durable_claim_is_fenced_by_consumer_and_scope(self):
        claim=self.worker.claim()
        self.assertEqual(claim["consumer_id"],self.consumer)
        self.assertEqual(claim["tenant_id"],self.tenant)
        self.assertEqual(claim["branch_id"],self.branch)
        self.assertEqual(claim["analysis_sha256"],self.asha)
        self.assertEqual(claim["knowledge_sha256"],self.ksha)
        state=self._row()
        self.assertEqual((state[0],state[1]),("LEASED",1))
        self.assertEqual(str(state[2]),claim["lease_token"])
        self.assertEqual(self._count(),0)
        self.assertFalse(self.worker.claim())
        with self.assertRaises(DomainError):
            SyntheticEng06ReviewWorker(store=PostgresStore(self.worker_dsn()),
                consumer_id="unbound-g06-consumer").claim()

    def test_g06_02_actual_worker_process_crash_then_fenced_reclaim(self):
        # Child commits a real SQL lease, flushes token to stdout, then dies
        # with os._exit (no Python cleanup, no ACK and no FAIL receipt).
        code=(
            "import os,sys;"
            "from abc_foundation.eng06_review_worker import SyntheticEng06ReviewWorker;"
            "from abc_foundation.pg_store import PostgresStore;"
            "w=SyntheticEng06ReviewWorker(store=PostgresStore("
            "os.environ['ABC_TEST_PG_ENG06_LOGIN_DSN']),"
            "consumer_id=sys.argv[1]);"
            "c=w.claim();print(c['lease_token'],flush=True);os._exit(75)"
        )
        p=subprocess.run(
            [sys.executable,"-c",code,self.consumer],
            cwd=os.path.dirname(__file__)+"/..",env=os.environ.copy(),
            capture_output=True,text=True,timeout=15,check=False,
        )
        self.assertEqual(p.returncode,75,p.stderr)
        old_token=p.stdout.strip()
        self.assertEqual(str(uuid.UUID(old_token)),old_token)
        self.assertEqual(self._row()[0:2],("LEASED",1))
        self.assertEqual(self._count(),0)
        self._expire()  # controlled clock advancement; no arbitrary sleep
        fresh=self.worker.claim()
        self.assertEqual(fresh["attempt"],2)
        self.assertNotEqual(old_token,fresh["lease_token"])
        stale={**fresh,"lease_token":old_token}
        with self.assertRaises(DomainError):
            self.worker.ack(stale,self.worker.decide_blocked(fresh))
        receipt=self.worker.ack(fresh,self.worker.decide_blocked(fresh))
        self.assertEqual(receipt["status"],"ACKED_BLOCKED_REVIEW_ONLY")
        self.assertEqual(self._count(),1)
        self.assertEqual(self._outbox()[0],"BLOCKED_PENDING_AUTHORITY")

    def test_g06_03_retry_backoff_then_unique_ack(self):
        first=self.worker.claim()
        self.assertEqual(self.worker.fail(first,"CI_TRANSIENT_NETWORK"),"QUEUED")
        with psycopg.connect(self.admin_dsn()) as con:
            ready=con.execute("""SELECT available_at>clock_timestamp()
                    FROM abc.eng06_ci_jobs WHERE upstream_handoff=%s""",
                    (self.handoff,)).fetchone()[0]
        self.assertTrue(ready)
        self.assertIsNone(self.worker.claim())
        self._make_due()
        second=self.worker.claim()
        self.assertEqual(second["attempt"],2)
        with self.assertRaises(DomainError):
            self.worker.ack(first,self.worker.decide_blocked(first))
        self.assertEqual(self.worker.ack(second,self.worker.decide_blocked(second))
                         ["status"],"ACKED_BLOCKED_REVIEW_ONLY")
        self.assertEqual(self._count(),1)

    def test_g06_04_exhausted_crashed_leases_transition_to_dlq(self):
        for attempt in (1,2,3):
            claim=self.worker.claim()
            self.assertEqual(claim["attempt"],attempt)
            self._expire()
        self.assertIsNone(self.worker.claim())
        state=self._row()
        self.assertEqual((state[0],state[1],state[5]),
                         ("DLQ",3,"CI_LEASE_EXHAUSTED"))
        self.assertEqual(self._count(),0)
        self.assertEqual(self._outbox()[0],"BLOCKED_PENDING_AUTHORITY")

    def test_g06_05_real_postgres_connection_outage_fails_closed_then_recovers(self):
        with patch.object(self.worker.store,"_connect",
                          side_effect=psycopg.OperationalError("CI network cut")):
            with self.assertRaises(DomainError) as ctx:
                self.worker.claim()
            self.assertEqual(ctx.exception.code,
                             "eng06_claim_identity_or_scope_denied")
        self.assertEqual(self._row()[0:2],("QUEUED",0))
        result=self.worker.process_once()
        self.assertEqual(result["status"],"ACKED_BLOCKED_REVIEW_ONLY")
        self.assertFalse(result["downstream_dispatched"])
        self.assertEqual(self._count(),1)

    def test_g06_06_eight_independent_connections_have_one_claim_winner(self):
        def claim(_):
            return SyntheticEng06ReviewWorker(
                store=PostgresStore(self.worker_dsn()),
                consumer_id=self.consumer).claim()
        with ThreadPoolExecutor(max_workers=8) as pool:
            claims=list(pool.map(claim,range(8)))
        accepted=[c for c in claims if c is not None]
        self.assertEqual(len(accepted),1,claims)
        winner=accepted[0]
        self.assertEqual(winner["attempt"],1)
        receipt=self.worker.ack(winner,self.worker.decide_blocked(winner))
        self.assertFalse(receipt["downstream_dispatched"])
        self.assertEqual(self._count(),1)
        self.assertIsNone(self.worker.claim())

    def test_g06_07_revocation_between_fail_retry_prevents_new_claim(self):
        claim=self.worker.claim()
        self.assertEqual(self.worker.fail(claim,"CI_TRANSIENT_NETWORK"),"QUEUED")
        with psycopg.connect(self.admin_dsn()) as con:
            con.execute("""UPDATE abc.consent_evidence
                 SET status='WITHDRAWN',revoked_at=clock_timestamp()
                 WHERE consent_id=%s""",(self.consent,))
        self._make_due()
        self.assertIsNone(self.worker.claim())
        self.assertEqual(self._row()[0],"QUEUED")  # retained, not executed
        self.assertEqual(self._count(),0)
        self.assertEqual(self._outbox()[0],"BLOCKED_PENDING_AUTHORITY")

    def test_g06_08_stale_session_version_fences_ack_and_retry(self):
        claim=self.worker.claim()
        with psycopg.connect(self.admin_dsn()) as con:
            con.execute("""UPDATE abc.sessions
                  SET state_version=state_version+1
                  WHERE session_id=%s""",(self.sid,))
        with self.assertRaises(DomainError):
            self.worker.ack(claim,self.worker.decide_blocked(claim))
        self._expire()
        self.assertIsNone(self.worker.claim())
        self.assertEqual(self._count(),0)

    def test_g06_09_revoked_physical_worker_binding_fences_claim_and_ack(self):
        claim=self.worker.claim()
        with psycopg.connect(self.admin_dsn()) as con:
            con.execute("""UPDATE abc.eng06_ci_worker_bindings
                 SET active=false WHERE login_name='abc_eng06_ci_login'
                   AND consumer_id=%s""",(self.consumer,))
        with self.assertRaises(DomainError):
            self.worker.ack(claim,self.worker.decide_blocked(claim))
        with self.assertRaises(DomainError):
            self.worker.claim()
        self.assertEqual(self._count(),0)

    def test_g06_10_ack_rejection_rolls_back_all_side_effects(self):
        claim=self.worker.claim()
        safe=self.worker.decide_blocked(claim)
        forged={**safe,"customer_release_approved":True}
        with self.assertRaises(DomainError):
            self.worker.ack(claim,forged)
        self.assertEqual(self._count(),0)
        self.assertEqual(self._row()[0],"LEASED")
        self.assertEqual(self._outbox()[0],"BLOCKED_PENDING_AUTHORITY")
        valid=self.worker.ack(claim,safe)
        self.assertEqual(valid["status"],"ACKED_BLOCKED_REVIEW_ONLY")
        self.assertEqual(self._count(),1)

    def test_g06_11_durable_sha256_provenance_and_nonrelease(self):
        claim=self.worker.claim()
        receipt=self.worker.ack(claim,self.worker.decide_blocked(claim))
        with psycopg.connect(self.admin_dsn()) as con:
            rows=con.execute("""SELECT j.status,r.status,r.output_bytes,
                 r.output_sha256,r.analysis_sha256,r.knowledge_sha256,
                 o.artifact_sha256,o.status
                 FROM abc.eng06_ci_jobs j
                 JOIN abc.eng06_ci_results r USING(upstream_handoff)
                 JOIN abc.eng19_synthetic_outbox o
                   ON o.handoff_id=j.upstream_handoff
                 WHERE j.upstream_handoff=%s""",(self.handoff,)).fetchall()
        self.assertEqual(len(rows),1)
        jstatus,rstatus,blob,digest,analysis,knowledge,outsha,ostatus=rows[0]
        self.assertEqual((jstatus,rstatus),
                         ("ACKED","BLOCKED_PROFESSIONAL_SOURCE"))
        self.assertEqual(hashlib.sha256(blob).hexdigest(),digest)
        self.assertEqual((analysis,knowledge),(self.asha,self.ksha))
        self.assertEqual(outsha,self.ksha)
        self.assertEqual(ostatus,"BLOCKED_PENDING_AUTHORITY")
        self.assertEqual(digest,receipt["output_sha256"])
        self.assertFalse(json.loads(blob)["customer_release_approved"])
        self.assertFalse(json.loads(blob)["downstream_dispatch_authorized"])

    def test_g06_12_wrong_worker_lease_token_cannot_fail_or_ack(self):
        claim=self.worker.claim()
        forged={**claim,"lease_token":str(uuid.uuid4())}
        with self.assertRaises(DomainError):
            self.worker.fail(forged,"CI_TRANSIENT_NETWORK")
        with self.assertRaises(DomainError):
            self.worker.ack(forged,self.worker.decide_blocked(claim))
        self.assertEqual(self._row()[0:2],("LEASED",1))
        self.assertEqual(self._count(),0)
        self.assertEqual(self.worker.fail(claim,"CI_TRANSIENT_NETWORK"),"QUEUED")


def load_tests(loader,_suite,_pattern):
    # Only the G06-specific tests, not the parent fixture's inherited tests.
    suite=unittest.TestSuite()
    names=sorted(n for n in vars(G06DurableRecovery) if n.startswith("test_g06_"))
    if len(names)!=12:
        raise AssertionError("G06 acceptance inventory changed; update CI contract")
    for name in names:
        suite.addTest(G06DurableRecovery(name))
    return suite


if __name__=="__main__":
    unittest.main()

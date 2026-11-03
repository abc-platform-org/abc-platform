"""ENG06 synthetic worker receipt regression without PostgreSQL privileges.

A deterministic in-memory connection double exercises the actual worker
claim -> blocked decision -> ACK call chain. PostgreSQL integration is separate.
"""
import os
import unittest
import uuid
from unittest.mock import patch
from abc_foundation.eng06_review_worker import SyntheticEng06ReviewWorker
from abc_foundation.store import DomainError

class FakeConnection:
    def __init__(self, responses):
        self.responses=responses
        self.queries=[]
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def execute(self, sql, args=None):
        self.queries.append((sql,args))
        return self
    def fetchone(self):
        return self.responses.pop(0)

class FakeStore:
    def __init__(self, responses):
        self.conn=FakeConnection(responses)
    def _connect(self):
        return self.conn

class Eng06WorkerReceiptTests(unittest.TestCase):
    def test_empty_queue_returns_none_without_dispatch(self):
        store=FakeStore([{"job":None}])
        worker=SyntheticEng06ReviewWorker(store=store,consumer_id="ci-worker")
        with patch.dict(os.environ,{"ABC_ENV":"LOCAL_INTEGRATION_ONLY"}):
            self.assertIsNone(worker.process_once())
        self.assertTrue(any("eng06_ci_claim" in sql for sql,_ in store.conn.queries))
        self.assertFalse(any("eng06_ci_ack" in sql for sql,_ in store.conn.queries))

    def test_invalid_claim_cannot_be_acknowledged(self):
        store=FakeStore([])
        worker=SyntheticEng06ReviewWorker(store=store,consumer_id="ci-worker")
        with patch.dict(os.environ,{"ABC_ENV":"LOCAL_INTEGRATION_ONLY"}):
            with self.assertRaises(DomainError):
                worker.ack({"engine_id":"ENG-06"},{"status":"BLOCKED_PROFESSIONAL_SOURCE"})
        self.assertEqual(store.conn.queries,[])

if __name__=="__main__":
    unittest.main()

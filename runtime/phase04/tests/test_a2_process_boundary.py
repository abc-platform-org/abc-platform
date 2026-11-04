"""A2: actual isolated engine entrypoint process boundary, synthetic-only.

Not proof of independent deployment, database authorization, or production readiness.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]


class A2RealEngineBoundaryTests(unittest.TestCase):
    def _invoke(self, engine, payload):
        env = dict(os.environ, PYTHONPATH=str(ROOT))
        return subprocess.run(
            [sys.executable, "-m", "abc_foundation.isolated_engine_service", engine],
            input=json.dumps(payload), text=True, capture_output=True,
            cwd=str(ROOT), env=env, timeout=20,
        )

    def test_actual_engine_entrypoints_reject_cross_engine_contracts(self):
        for engine in ("ENG-04", "ENG-05", "ENG-06"):
            with self.subTest(engine=engine):
                result = self._invoke(engine, {
                    "request_id": str(uuid.uuid4()),
                    "engine_id": "ENG-99",
                    "contract_version": "abc.internal.engine.synthetic.v1",
                    "consumer_id": "a2-synthetic",
                    "session_id": str(uuid.uuid4()),
                    "payload": {},
                })
                self.assertEqual(result.returncode, 3, result.stderr)
                response = json.loads(result.stdout)
                self.assertEqual(response["error"], "invalid_engine_service_contract")
                self.assertIs(response["release_approved"], False)

    def test_actual_engine_entrypoints_reject_unapproved_release(self):
        for engine in ("ENG-04", "ENG-05", "ENG-06"):
            with self.subTest(engine=engine):
                result = self._invoke(engine, {
                    "request_id": str(uuid.uuid4()),
                    "engine_id": engine,
                    "contract_version": "abc.internal.engine.synthetic.v1",
                    "consumer_id": "a2-synthetic",
                    "session_id": str(uuid.uuid4()),
                    "payload": {"release_approved": True},
                })
                self.assertEqual(result.returncode, 3, result.stderr)
                response = json.loads(result.stdout)
                self.assertIs(response["release_approved"], False)

    def test_killing_real_engine_process_does_not_kill_other_engine_processes(self):
        env = dict(os.environ, PYTHONPATH=str(ROOT))
        workers = []
        try:
            for engine in ("ENG-04", "ENG-05", "ENG-06"):
                proc = subprocess.Popen(
                    [sys.executable, "-m", "abc_foundation.isolated_engine_service", engine],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, text=True, cwd=str(ROOT), env=env,
                )
                workers.append((engine, proc))
            self.assertEqual(len({proc.pid for _, proc in workers}), 3)
            for _, proc in workers:
                self.assertIsNone(proc.poll(), "real engine process failed to start")
            victim = workers[1][1]
            victim.kill()
            victim.wait(timeout=5)
            self.assertNotEqual(victim.returncode, 0)
            for engine, proc in (workers[0], workers[2]):
                self.assertIsNone(proc.poll(), engine + " died with ENG-05")
                request = {
                    "request_id": str(uuid.uuid4()), "engine_id": engine,
                    "contract_version": "abc.internal.engine.synthetic.v1",
                    "consumer_id": "a2-synthetic", "session_id": str(uuid.uuid4()),
                    "payload": {"release_approved": True},
                }
                out, err = proc.communicate(json.dumps(request), timeout=20)
                self.assertEqual(proc.returncode, 3, err)
                self.assertIs(json.loads(out)["release_approved"], False)
        finally:
            for _, proc in workers:
                if proc.poll() is None:
                    proc.kill()
                proc.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main()

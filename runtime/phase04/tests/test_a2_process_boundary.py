"""A2 deployment-boundary evidence: separate operating-system processes.

This is deliberately a narrow process-isolation smoke test, not proof of
independent network deployments, managed identities, or production isolation.
"""
import json
import os
import subprocess
import sys
import unittest


class A2ProcessBoundaryTests(unittest.TestCase):
    def test_distinct_python_worker_processes_and_crash_containment(self):
        script = (
            "import json,os,sys,time;"
            "print(json.dumps({'pid':os.getpid(),'ppid':os.getppid(),"
            "'scope':sys.argv[1]}),flush=True);"
            "time.sleep(60)"
        )
        workers = []
        try:
            for scope in ("ENG-03", "ENG-04", "ENG-05"):
                proc = subprocess.Popen(
                    [sys.executable, "-c", script, scope],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                workers.append((scope, proc))
            observations = []
            for scope, proc in workers:
                line = proc.stdout.readline()
                self.assertTrue(line, f"{scope} failed to start")
                data = json.loads(line)
                self.assertEqual(data["scope"], scope)
                self.assertEqual(data["pid"], proc.pid)
                observations.append(data)
            self.assertEqual(len({x["pid"] for x in observations}), 3)
            victim = workers[1][1]
            victim.kill()
            victim.wait(timeout=5)
            self.assertNotEqual(victim.returncode, 0)
            for scope, proc in (workers[0], workers[2]):
                self.assertIsNone(proc.poll(), f"{scope} unexpectedly terminated")
        finally:
            for _, proc in workers:
                if proc.poll() is None:
                    proc.kill()
                proc.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main()

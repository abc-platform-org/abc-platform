"""Isolated session-index worker process (no inbound port, synthetic/staging only).

Production supervision, distributed workload identity, retries and telemetry are
independent operational gates. This process cannot enable visual/consent/finance.
"""
import os
import signal
import time

from .session_index_consumer import SessionIndexConsumer


def main():
    if os.getenv("ABC_ENV") != "OIDC_PG_LOOPBACK_INTEGRATION":
        raise SystemExit("worker restricted to isolated OIDC/Pg integration environment")
    dsn, consumer = os.getenv("ABC_WORKER_DSN"), os.getenv("ABC_CONSUMER_ID")
    if not dsn or not consumer:
        raise SystemExit("Dedicated worker DB credential and provisioned consumer_id required")
    every = int(os.getenv("ABC_WORKER_POLL_SECONDS", "2"))
    if not 1 <= every <= 30:
        raise SystemExit("invalid polling interval")
    service=SessionIndexConsumer(dsn,consumer)
    stop = [False]
    def request_shutdown(_signum, _frame):
        stop[0]=True
    signal.signal(signal.SIGINT,request_shutdown)
    signal.signal(signal.SIGTERM,request_shutdown)
    print("ABC session-index integration worker started (no public listener)",flush=True)
    while not stop[0]:
        # Unknown DB failure intentionally crashes the process and preserves
        # the lease for recovery, rather than claiming an event was delivered.
        service.run_once()
        if not stop[0]:
            time.sleep(every)


if __name__ == "__main__":
    main()

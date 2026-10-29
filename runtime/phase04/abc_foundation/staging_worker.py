"""Managed private staging background worker. No listener and no real client data."""
import os
import signal
import time

from .pg_outbox import OutboxDispatcher
from .session_index_consumer import SessionIndexConsumer
from .staging_api import validate_staging_dsn, assert_staging_database


def configure_worker(env=None):
    env = os.environ if env is None else env
    if env.get("ABC_ENV") != "STAGING_PRIVATE" or env.get("ABC_STAGING_PURPOSE") != "SYNTHETIC_NO_CLIENT_DATA":
        raise ValueError("private_staging_gate_not_approved")
    if env.get("ABC_NETWORK_BOUNDARY") != "RENDER_BACKGROUND_WORKER":
        raise ValueError("worker_network_boundary_not_declared")
    dsn = env.get("ABC_WORKER_DSN")
    validate_staging_dsn(dsn, "abc_worker")
    consumer = env.get("ABC_CONSUMER_ID")
    OutboxDispatcher._consumer(consumer)
    service=SessionIndexConsumer(dsn,consumer)
    assert_staging_database(service.dispatcher, "abc_worker", [
        "abc.event_delivery", "abc.worker_subscriptions", "abc.session_index_projection"])
    with service.dispatcher._connect() as con:
        active = con.execute("""
            SELECT 1 FROM abc.worker_subscriptions
            WHERE consumer_id=%s AND active=true AND event_type='SESSION_CREATED'
        """,(consumer,)).fetchone()
        if active is None:
            raise ValueError("worker_subscription_not_provisioned")
    every = int(env.get("ABC_WORKER_POLL_SECONDS","2"))
    if not 1 <= every <= 30:
        raise ValueError("invalid_worker_poll")
    return service, every


def main():
    service,every=configure_worker()
    stop=[False]
    def shutdown(_signum,_frame):
        stop[0]=True
    signal.signal(signal.SIGINT,shutdown)
    signal.signal(signal.SIGTERM,shutdown)
    print("ABC staging worker running private synthetic-only session index",flush=True)
    while not stop[0]:
        service.run_once()
        if not stop[0]:
            time.sleep(every)


if __name__=="__main__":
    main()

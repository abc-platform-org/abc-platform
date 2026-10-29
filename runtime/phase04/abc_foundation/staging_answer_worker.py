"""Separate ANSWER_RECORDED worker process; no HTTP listener or API keys.

Package only: no Render service, database or paid resource is deployed.
"""
import os
import signal
import time

from .answer_index_consumer import AnswerIndexConsumer,AnswerDispatcher
from .staging_api import validate_staging_dsn, assert_staging_database


def configure_answer_worker(env=None):
    env=os.environ if env is None else env
    if (env.get("ABC_ENV")!="STAGING_PRIVATE"
        or env.get("ABC_STAGING_PURPOSE")!="SYNTHETIC_NO_CLIENT_DATA"
        or env.get("ABC_NETWORK_BOUNDARY")!="RENDER_BACKGROUND_WORKER"):
        raise ValueError("private_synthetic_answer_worker_only")
    dsn=env.get("ABC_ANSWER_WORKER_DSN")
    validate_staging_dsn(dsn,"abc_answer_worker")
    consumer_id=env.get("ABC_ANSWER_CONSUMER_ID")
    AnswerDispatcher._consumer(consumer_id)
    service=AnswerIndexConsumer(dsn,consumer_id)
    assert_staging_database(service.dispatcher,"abc_answer_worker",[
        "abc.worker_subscriptions","abc.event_delivery",
        "abc.outbox","abc.answer_index_projection","abc.eng03_input_jobs"])
    with service.dispatcher._connect() as con:
        active=con.execute("""SELECT 1 FROM abc.worker_subscriptions
            WHERE consumer_id=%s AND event_type='ANSWER_RECORDED'
              AND active=true""",(consumer_id,)).fetchone()
        if active is None:
            raise ValueError("answer_worker_subscription_not_provisioned")
    try:
        every=int(env.get("ABC_ANSWER_POLL_SECONDS","2"))
    except (TypeError,ValueError):
        raise ValueError("invalid_answer_worker_poll") from None
    if not 1<=every<=30:
        raise ValueError("invalid_answer_worker_poll")
    return service,every


def main():
    service,every=configure_answer_worker()
    stop=[False]
    def shutdown(*_):
        stop[0]=True
    signal.signal(signal.SIGTERM,shutdown)
    signal.signal(signal.SIGINT,shutdown)
    print("ABC synthetic-only answer projection worker: private",flush=True)
    while not stop[0]:
        service.run_once()
        if not stop[0]:
            time.sleep(every)


if __name__=="__main__":
    main()

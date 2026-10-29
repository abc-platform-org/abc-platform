"""Private, synthetic-only no-listener ENG03 and ENG04/05/06 worker launchers.

This is a deployment candidate, NOT an existing Render service. Config-only
preflight refuses real-client input and nonprivate staging. Each worker has a
distinct constrained database principal and an admin-active binding.
"""
import os
import re
import signal
import time

from .eng03_executor import ENG03Executor
from .eng04_06_pipeline import SyntheticAnalysisPipeline
from .pg_outbox import CONSUMER
from .staging_api import validate_staging_dsn,assert_staging_database


def configure_engine_worker(kind,env=None):
    env=os.environ if env is None else env
    if (env.get("ABC_ENV")!="STAGING_PRIVATE"
        or env.get("ABC_STAGING_PURPOSE")!="SYNTHETIC_NO_CLIENT_DATA"
        or env.get("ABC_NETWORK_BOUNDARY")!="RENDER_BACKGROUND_WORKER"):
        raise ValueError("synthetic_private_workers_only")
    if kind not in ("ENG03","PIPELINE"):
        raise ValueError("unknown_engine_worker")
    consumer=env.get("ABC_ENGINE_CONSUMER_ID")
    tenant=env.get("ABC_ENGINE_TENANT_ID")
    if (not isinstance(consumer,str) or not CONSUMER.fullmatch(consumer)
        or not isinstance(tenant,str) or not 1<=len(tenant)<=128):
        raise ValueError("explicit_admin_bound_consumer_tenant_required")
    role="abc_eng03_worker" if kind=="ENG03" else "abc_pipeline_worker"
    dsn=env.get("ABC_ENGINE_DSN")
    expected_login=env.get("ABC_ENGINE_WORKLOAD_LOGIN")
    login_pattern=r"abc_e3_[0-9a-f]{14,24}" if kind=="ENG03" else r"abc_p6_[0-9a-f]{14,24}"
    if not isinstance(expected_login,str) or not re.fullmatch(login_pattern,expected_login):
        raise ValueError("per_consumer_database_login_required")
    validate_staging_dsn(dsn,expected_login)
    worker=ENG03Executor(dsn,consumer) if kind=="ENG03" else SyntheticAnalysisPipeline(dsn,consumer)
    tables=["abc.eng03_worker_bindings","abc.eng03_input_jobs","abc.eng03_evidence_ledger",
            "abc.eng04_06_jobs","abc.eng04_06_results","abc.worker_login_bindings"]
    assert_staging_database(worker,role,tables)
    with worker._connect() as con:
        allowed=con.execute("""SELECT 1 FROM abc.eng03_worker_bindings
                WHERE worker_role=current_user AND consumer_id=%s
                  AND tenant_id=%s AND active=true""",(consumer,tenant)).fetchone()
        if not allowed:
            raise ValueError("admin_engine_worker_binding_not_active")
    try:
        seconds=int(env.get("ABC_ENGINE_POLL_SECONDS","2"))
    except (TypeError,ValueError):
        raise ValueError("invalid_engine_poll") from None
    if not 1<=seconds<=30:
        raise ValueError("invalid_engine_poll")
    return worker,seconds


def main(kind):
    worker,every=configure_engine_worker(kind)
    stop=[False]
    def shutdown(*_):stop[0]=True
    signal.signal(signal.SIGTERM,shutdown)
    signal.signal(signal.SIGINT,shutdown)
    print("ABC synthetic-only "+kind+" private worker",flush=True)
    while not stop[0]:
        worker.run_once()
        if not stop[0]:
            time.sleep(every)


if __name__=="__main__":
    requested=os.environ.get("ABC_ENGINE_KIND")
    main(requested)

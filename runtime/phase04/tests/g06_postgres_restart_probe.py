"""G06-07 two-stage restart acceptance for the actual CI PostgreSQL service.

prepare: commit one ACKED review output and leave another real LEASED job
         in-flight, then write only identifiers/digests to the evidence file.
verify:  after Docker restarts the Postgres service, show committed data and
         source hashes survived, expire original lease, fence it, reclaim
         with a new worker and acknowledge *once*. Never dispatch ENG07.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import uuid

import psycopg
from psycopg.conninfo import conninfo_to_dict

ROOT=Path(__file__).resolve().parents[3]
STATE=ROOT/"a2"/"g06"/"postgres-restart-state.json"

if os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
    raise SystemExit("G06 restart probe requires synthetic CI")
ADMIN=os.environ.get("ABC_TEST_PG_ADMIN_DSN")
WORKER=os.environ.get("ABC_TEST_PG_ENG06_LOGIN_DSN")
if not ADMIN or not WORKER or conninfo_to_dict(ADMIN).get("dbname")!="abc_phase04_ci" or (
    conninfo_to_dict(WORKER).get("user")!="abc_eng06_ci_login" or
    conninfo_to_dict(WORKER).get("dbname")!="abc_phase04_ci"):
    raise SystemExit("G06 restart probe rejects any non-fixture database")
if len(sys.argv)!=2 or sys.argv[1] not in ("prepare","verify"):
    raise SystemExit("usage: prepare|verify")

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_eng06_pg_positive_e2e import Eng06PositivePostgresTests
from abc_foundation.eng06_review_worker import SyntheticEng06ReviewWorker
from abc_foundation.pg_store import PostgresStore
from abc_foundation.store import DomainError


def connection():
    for i in range(30):
        try:
            return psycopg.connect(ADMIN)
        except psycopg.OperationalError:
            if i==29:
                raise
            time.sleep(.5)


if sys.argv[1]=="prepare":
    first=Eng06PositivePostgresTests("test_real_claim_ack_persist_and_replay_denied")
    first.setUp()
    claim1=first.worker.claim()
    receipt1=first.worker.ack(claim1,first.worker.decide_blocked(claim1))
    assert receipt1["status"]=="ACKED_BLOCKED_REVIEW_ONLY"
    second=Eng06PositivePostgresTests("test_expired_lease_reclaim_fences_old_ack")
    second.setUp()
    claim2=second.worker.claim()
    assert claim2["attempt"]==1
    with connection() as con:
        completed=con.execute("""SELECT j.status,r.output_sha256,r.output_bytes,
                  o.status,src.source_sha256
                  FROM abc.eng06_ci_jobs j
                  JOIN abc.eng06_ci_results r USING(upstream_handoff)
                  JOIN abc.eng19_synthetic_outbox o
                     ON o.handoff_id=j.upstream_handoff
                  JOIN abc.eng19_synthetic_jobs src
                     ON src.handoff_id=j.upstream_handoff
                  WHERE j.upstream_handoff=%s""",(first.handoff,)).fetchone()
        assert completed and completed[0]=="ACKED"
        assert hashlib.sha256(completed[2]).hexdigest()==completed[1]
        assert completed[3]=="BLOCKED_PENDING_AUTHORITY"
        pending=con.execute("""SELECT status,attempts FROM abc.eng06_ci_jobs
                  WHERE upstream_handoff=%s""",(second.handoff,)).fetchone()
        assert pending==("LEASED",1)
    STATE.parent.mkdir(parents=True,exist_ok=True)
    state={
        "status":"PREPARED_COMMITTED_AND_INFLIGHT",
        "completed_handoff":str(first.handoff),
        "completed_output_sha256":completed[1],
        "completed_source_sha256":completed[4],
        "inflight_handoff":str(second.handoff),
        "inflight_consumer":second.consumer,
        "inflight_old_lease":claim2["lease_token"],
        "managed_staging_proven":False,
        "eng06_release_approved":False,
    }
    STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+"\n")
    print("G06 prepared durable ACKED result and one LEASED recovery job")
else:
    state=json.loads(STATE.read_text())
    assert state["status"]=="PREPARED_COMMITTED_AND_INFLIGHT"
    with connection() as con:
        rows=con.execute("""SELECT j.status,r.output_sha256,r.output_bytes,
                 o.status,src.source_sha256
                 FROM abc.eng06_ci_jobs j
                 JOIN abc.eng06_ci_results r USING(upstream_handoff)
                 JOIN abc.eng19_synthetic_outbox o
                    ON o.handoff_id=j.upstream_handoff
                 JOIN abc.eng19_synthetic_jobs src
                    ON src.handoff_id=j.upstream_handoff
                 WHERE j.upstream_handoff=%s""",
                 (uuid.UUID(state["completed_handoff"]),)).fetchall()
        assert len(rows)==1
        status,sha,blob,outbox,source_sha=rows[0]
        assert (status,sha,outbox,source_sha)==(
            "ACKED",state["completed_output_sha256"],
            "BLOCKED_PENDING_AUTHORITY",state["completed_source_sha256"])
        assert hashlib.sha256(blob).hexdigest()==sha
        inflight=con.execute("""SELECT status,attempts,lease_token
                 FROM abc.eng06_ci_jobs WHERE upstream_handoff=%s""",
                 (uuid.UUID(state["inflight_handoff"]),)).fetchone()
        assert inflight and inflight[0]=="LEASED" and inflight[1]==1
        assert str(inflight[2])==state["inflight_old_lease"]
        con.execute("""UPDATE abc.eng06_ci_jobs SET
                 lease_until=clock_timestamp()-interval '1 second'
                 WHERE upstream_handoff=%s""",
                 (uuid.UUID(state["inflight_handoff"]),))
    worker=SyntheticEng06ReviewWorker(
        store=PostgresStore(WORKER),
        consumer_id=state["inflight_consumer"])
    fresh=worker.claim()
    assert fresh and fresh["attempt"]==2
    assert fresh["lease_token"]!=state["inflight_old_lease"]
    try:
        worker.ack({**fresh,"lease_token":state["inflight_old_lease"]},
                   worker.decide_blocked(fresh))
        raise AssertionError("stale pre-restart lease accepted")
    except DomainError:
        pass
    receipt=worker.ack(fresh,worker.decide_blocked(fresh))
    assert receipt["status"]=="ACKED_BLOCKED_REVIEW_ONLY"
    with connection() as con:
        n=con.execute("""SELECT count(*) FROM abc.eng06_ci_results
             WHERE upstream_handoff=%s""",
             (uuid.UUID(state["inflight_handoff"]),)).fetchone()[0]
        blocked=con.execute("""SELECT status FROM abc.eng19_synthetic_outbox
             WHERE handoff_id=%s""",
             (uuid.UUID(state["inflight_handoff"]),)).fetchone()
        assert n==1 and blocked==("BLOCKED_PENDING_AUTHORITY",)
    state.pop("inflight_old_lease",None) # don't retain lease in final artifact
    state["status"]="PASS"
    state["postgres_service_restart_recovery"]=True
    state["committed_sha256_preserved"]=True
    state["inflight_lease_survived_restart"]=True
    state["stale_pre_restart_ack_rejected"]=True
    state["post_restart_reclaim_and_ack_once"]=True
    state["eng06_release_approved"]=False
    STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+"\n")
    print("PASS: durable PG restart + stale lease fenced + single blocked result")

"""CI-only committed-write recovery probe across PostgreSQL container restart.
Usage: prepare | verify | cleanup. Synthetic tenant only.
"""
import os
import sys
import time
import psycopg

TENANT="a1-ci-restart-probe"
ADAPTER="A04_TO_06_DECISION_INPUT"
DSN=os.getenv("ABC_TEST_PG_ADMIN_DSN")
if os.getenv("ABC_ENV")!="LOCAL_INTEGRATION_ONLY" or not DSN:
    raise SystemExit("disposable CI database only")
if len(sys.argv)!=2 or sys.argv[1] not in ("prepare","verify","cleanup"):
    raise SystemExit("usage: prepare|verify|cleanup")

def connect():
    last=None
    for _ in range(30):
        try:
            return psycopg.connect(DSN)
        except psycopg.OperationalError as exc:
            last=exc
            time.sleep(2)
    raise last

with connect() as con:
    with con.cursor() as cur:
        if sys.argv[1]=="prepare":
            cur.execute("""INSERT INTO abc.a1_bridge_legacy(
                adapter_id,tenant_id,branch_id,session_id,artifact_id,
                source_sha256,consent_decision_id,policy_decision_id,source_version,payload)
                VALUES (%s,%s,'ci-only','ci-only','durable-restart',
                %s,'ci-consent','ci-policy','abc.internal.engine.v2.draft',
                '{"synthetic":true}'::jsonb)
                ON CONFLICT(adapter_id,tenant_id,branch_id,session_id,artifact_id)
                DO NOTHING""",(ADAPTER,TENANT,"b"*64))
            cur.execute("""INSERT INTO abc.a1_bridge_shadow(
                adapter_id,tenant_id,branch_id,session_id,artifact_id,
                source_sha256,consent_decision_id,policy_decision_id,
                source_version,target_version,payload)
                SELECT adapter_id,tenant_id,branch_id,session_id,artifact_id,
                source_sha256,consent_decision_id,policy_decision_id,
                source_version,'abc.internal.capability.v3.review',payload
                FROM abc.a1_bridge_legacy WHERE tenant_id=%s
                ON CONFLICT(adapter_id,tenant_id,branch_id,session_id,artifact_id)
                DO NOTHING""",(TENANT,))
            print("Prepared committed synthetic legacy/shadow rows")
        elif sys.argv[1]=="verify":
            cur.execute("""SELECT l.source_sha256=s.source_sha256,
                l.payload=s.payload,s.dispatch_authorized,s.customer_release_approved
                FROM abc.a1_bridge_legacy l JOIN abc.a1_bridge_shadow s
                USING(adapter_id,tenant_id,branch_id,session_id,artifact_id)
                WHERE l.tenant_id=%s""",(TENANT,))
            assert cur.fetchall()==[(True,True,False,False)],"durable recovery invariant failed"
            print("PASS: committed bridge survives PostgreSQL restart, release remains denied")
        else:
            cur.execute("DELETE FROM abc.a1_bridge_shadow WHERE tenant_id=%s",(TENANT,))
            cur.execute("DELETE FROM abc.a1_bridge_legacy WHERE tenant_id=%s",(TENANT,))
            print("Cleaned synthetic recovery probe")

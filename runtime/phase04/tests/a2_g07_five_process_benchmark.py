"""Measured G07 local-only five-OS-process performance candidate, no hosted SLO.

Executes real ENG02->ENG03->ENG04->ENG05->ENG06 synthetic non-media
operations. Every measured chain launches five fresh OS processes, one per
engine. Monotonic wall-clock times include process startup and IPC. Runs N=100
with max 4 concurrent sessions and 3 warmups, with fail-closed percentiles
and a separately measured throughput. These are CI runner baseline metrics,
NOT production latency promises or an SRE signature.
"""
import concurrent.futures
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
import uuid

# Standalone python tests/*.py uses tests/ (not phase04/) as sys.path[0].
# Resolve the module root exactly as unittest discover does.
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import test_eng02_eng06_five_process_chain as five

ROOT=Path(__file__).resolve().parents[3]
POLICY_PATH=ROOT/"governance/ABC_A2_G07_G09_SYNTHETIC_ACCEPTANCE_v1.review.json"
STAGES=("ENG-02","ENG-03","ENG-04","ENG-05","ENG-06")


def policy():
    doc=json.loads(POLICY_PATH.read_text())
    if (doc["schema_version"]!="a2.g07-g09.synthetic.v1"
        or doc["decision_status"]!="ENGINEERING_CI_CANDIDATE_UNRATIFIED"
        or doc["scope"]!="LOCAL_INTEGRATION_ONLY"
        or tuple(doc["workflow"])!=STAGES
        or doc["operational_deferred"]["a2_operational_closed"] is not False
        or doc["operational_deferred"]["eng06_customer_release_approved"] is not False):
        raise ValueError("unsafe_a2_performance_policy")
    return doc


def nearest_rank(values,percent):
    """No interpolation/averaging of sample tails or misleading p99 on n<100."""
    if not values or not 0 < percent <= 1:
        raise ValueError("invalid_quantile")
    vals=sorted(values)
    return round(vals[math.ceil(len(vals)*percent)-1],6)


def evaluate_alerts(*,error_count,p95_seconds,restart_seconds,release_count,doc):
    """Offline dry-run of alert rules, NOT proof of delivered pager alert."""
    rules=doc["gate_g09"]["simulated_alert_rules"]
    expected=("CHAIN_ERROR_RATE","P95_LATENCY","RESTART_BUDGET",
              "CONSENT_OR_RELEASE_VIOLATION")
    if tuple(r["code"] for r in rules)!=expected:
        raise ValueError("unreviewed_alert_rule_set")
    limit=doc["gate_g07"]["thresholds"]["end_to_end_seconds"]["p95_max"]
    rto=doc["gate_g09"]["thresholds"]["local_process_recovery_seconds_max"]
    checks=(error_count>0,p95_seconds>limit,restart_seconds>rto,
            release_count>0)
    return [{"code":rule["code"],"severity":rule["severity"]}
            for rule,active in zip(rules,checks) if active]


def _one_chain(_n):
    case=five.FiveIndependentProcessSyntheticChain(
        "test_01_full_five_process_chain_is_synthetic_only")
    case.setUp()
    # Parallel startup can delay child queue-feeder teardown after the reply
    # is received. Still bound the actual exit; never fake a successful join.
    case.exit_timeout_seconds=10
    measurements={}
    stage=case.stage

    def timed(engine,**parameters):
        started=time.perf_counter_ns()
        response=stage(engine,**parameters)
        measurements[engine]=(time.perf_counter_ns()-started)/1e9
        if ("error" in response or response.get("release_approved") is not False
            or response.get("engine_id")!=engine):
            raise AssertionError("engine_rejected_or_release_unexpected:"+engine)
        return response

    case.stage=timed
    started=time.perf_counter_ns()
    try:
        result=case.complete()
        elapsed=(time.perf_counter_ns()-started)/1e9
        if (set(measurements)!=set(STAGES) or
            result[0]["result"]["readiness"]!="READY_FOR_RECOMMENDATION" or
            result[0]["result"]["policy_evaluations"]!=4 or
            result[0]["result"]["media_received"] is not False or
            result[-1]["result"]["release_approved"] is not False or
            result[-1]["result"]["result"]["session_id"]!=case.cfg["session_id"] or
            len(result[-1]["result"]["result"]["candidates"])!=1 or
            result[-1]["result"]["result"]["candidates"][0]
              ["feasibility_label"]!="PROFESSIONAL_CHECK_REQUIRED"):
            raise AssertionError("synthetic_chain_postcondition_failed")
        return {"seconds":elapsed,"stages_seconds":measurements,
                "release_approved":False}
    finally:
        case.doCleanups()


def bench():
    if os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
        raise RuntimeError("local_synthetic_benchmark_only")
    doc=policy()
    g=doc["gate_g07"]
    method=g["methodology"]
    n=g["thresholds"]["measured_runs_min"]
    if (n<100 or method["measured_runs_min"]!=n or method["warmup_runs"]<3
        or method["concurrency"]!=4):
        raise RuntimeError("insufficient_sample_or_unreviewed_parallelism")
    for i in range(method["warmup_runs"]):
        _one_chain(-i-1)
    start=time.perf_counter_ns()
    with concurrent.futures.ThreadPoolExecutor(
            max_workers=method["concurrency"]) as pool:
        observations=list(pool.map(_one_chain,range(n)))
    wall=(time.perf_counter_ns()-start)/1e9
    times=[x["seconds"] for x in observations]
    stats={k:nearest_rank(times,p) for k,p in
            (("p50",.5),("p95",.95),("p99",.99),("max",1.0))}
    stages={engine:{k:nearest_rank(
        [obs["stages_seconds"][engine] for obs in observations],p)
        for k,p in (("p50",.5),("p95",.95),("p99",.99))}
        for engine in STAGES}
    release_count=sum(x["release_approved"] for x in observations)
    limits=g["thresholds"]["end_to_end_seconds"]
    if not (stats["p50"]<=limits["p50_max"] and
            stats["p95"]<=limits["p95_max"] and
            stats["p99"]<=limits["p99_max"] and
            stats["max"]<=limits["max_max"] and
            n/wall>=g["thresholds"]["throughput_chains_per_second_min"] and
            release_count==0):
        raise AssertionError("g07_ci_performance_threshold_not_met")
    alerts=evaluate_alerts(error_count=0,p95_seconds=stats["p95"],
         restart_seconds=0,release_count=release_count,doc=doc)
    if alerts:
        raise AssertionError("unexpected_ci_alert")
    report={
        "gate":"G07_SYNTHETIC_PERFORMANCE_CI",
        "result":"CI_ACCEPTANCE_PASS_NOT_OPERATIONAL_SIGNOFF",
        "sample_size":n,"warmup_runs":method["warmup_runs"],
        "concurrency":method["concurrency"],
        "end_to_end_seconds":stats,"per_engine_process_seconds":stages,
        "measurement_wall_seconds":round(wall,6),
        "throughput_chains_per_second":round(n/wall,6),
        "failed_chains":0,"customer_release_count":release_count,
        "alerts":alerts,"runner":{
            "os":platform.platform(),"python":sys.version.split()[0],
            "cpu_count":os.cpu_count(),
            "hosted_instance_class":"GITHUB_RUNNER_UNPINNED"},
        "policy_sha256":hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "source_commit":os.environ.get("GITHUB_SHA","UNVERIFIED_LOCAL"),
        "run_id":os.environ.get("GITHUB_RUN_ID","UNVERIFIED_LOCAL"),
        "a2_operational_closed":False,"eng06_release_approved":False
    }
    target=Path(os.environ.get("ABC_A2_G07_REPORT",
                              "/tmp/abc-a2-g07-ci-report.json"))
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps(report,sort_keys=True))
    return report


if __name__=="__main__":
    bench()

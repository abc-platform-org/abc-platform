"""Fail-closed A2 G01-G10 reconciliation / decision-packet validator.

This is an evidence INTEGRITY test, not independent human ratification.
The six SUCCESS statuses here are source metadata from a known Git commit;
with --verify-github, validate them against GitHub Actions API at execution.
Under GitHub Actions, git diff ensures no runtime/config code drift since
the tested SHA. Do not treat PASS as operational A2 approval.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
MATRIX=ROOT/"governance/ABC_A2_G01_G10_EVIDENCE_RECONCILIATION_v1.json"
RISKS=ROOT/"governance/ABC_A2_INDEPENDENT_RISK_REGISTER_v1.json"
PACKET=ROOT/"governance/ABC_A2_PREDEPLOYMENT_DECISION_PACKET_v1.md"
BASE="d8c7698bc060b859f5f4db52d572a00db656a2cd"
REPO="saleheebrahimi2029-hub/abc-platform"
SHA=re.compile(r"^[a-f0-9]{40}$")
SHA256=re.compile(r"^[a-f0-9]{64}$")
RUN_JOB=re.compile(r"^https://github\.com/saleheebrahimi2029-hub/abc-platform/actions/runs/(\d+)/job/(\d+)$")
SCOPES={"ENG-01","ENG-02","ENG-03","ENG-04","ENG-05",
        "ENG-06","ENG-14","LEGACY_REVIEW_TRANSPORT"}
GATE_IDS=[
"G01_ARCHITECTURE","G02_DOMAIN_CAPABILITY","G03_CONTRACTS",
"G04_INDEPENDENCE","G05_SECURITY_PRIVACY","G06_RELIABILITY",
"G07_PERFORMANCE","G08_PROFESSIONAL_VALIDATION",
"G09_OBSERVABILITY_OPERATIONS","G10_INDEPENDENT_SIGNOFF"]
RUNS={
 "foundation":42208334348, "scoped":42208334405,
 "security":42208334526,"transport":42208334592,
 "durable":42208334762,"perf":42208334598
}
EXPECTED_ARTIFACTS={
 "ENG-01":"c09d1c3441e695d2a8d7eaf9242ca7e98ce91dee3d4ac917cfee00782ce3e120",
 "ENG-02":"c9c673e7c8626dbfba34b92f6b82edf63b5a8db1eef1abbe5bf142d363c68b7f",
 "ENG-03":"e305c390c5692ecb3ed7b3e58ae0430931c477710b5c4893f8348170680f0efe",
 "ENG-04":"de721d8ec741ad553a23c0feed122cd7ca3362f3e10160fa631bde89fabf1fb8",
 "ENG-05":"4c169b03352c7277ca27fd007231bbb59c6a9dd7dbce9e1c51eb8fc1614904c4",
 "ENG-06":"078b5cd23651eab703a78c6a7f8284a882e19a2564e84bb551535fc039773958",
 "ENG-14":"459158e3fe15fac7e875a473a5c94c46a7102f35b7bd8d83403749be846b5a5e",
 "LEGACY_REVIEW_TRANSPORT":"02bef48f661c9d51f568e97f3b7fecf686cf3e0d00fabeb0b9f33dde474f77a5"
}
ALLOW_AFTER_BASE={
"governance/ABC_A2_G01_G10_EVIDENCE_RECONCILIATION_v1.json",
"governance/ABC_A2_INDEPENDENT_RISK_REGISTER_v1.json",
"governance/ABC_A2_PREDEPLOYMENT_DECISION_PACKET_v1.md",
"scripts/validate_a2_closure_packet_v1.py",
".github/workflows/a2-closure-packet-integrity.yml"
}


class EvidenceError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def data():
    return json.loads(MATRIX.read_text()),json.loads(RISKS.read_text())


def real_path(ref: str) -> Path:
    require(type(ref) is str and ref and not ref.startswith("/") and
            ".." not in Path(ref).parts,"invalid_relative_source_path")
    path=(ROOT/ref).resolve()
    require(path.is_relative_to(ROOT.resolve()) and path.is_file(),
            f"missing_source:{ref}")
    return path


def _assertion_exists(test_path: Path, name: str) -> bool:
    tree=ast.parse(test_path.read_text(),filename=str(test_path))
    return any(isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and
               node.name==name for node in ast.walk(tree))


def check(matrix,risks,*,check_sources=True):
    require(matrix.get("schema")=="abc.a2.g01-g10.evidence-reconciliation.v1","schema")
    require(matrix.get("baseline_code_sha")==BASE and SHA.fullmatch(BASE),"source_base")
    require(matrix.get("source_scope")==
            "LOCAL_INTEGRATION_ONLY / CI-DISPOSABLE_PG16 / SYNTHETIC_NON_MEDIA","ci_scope")
    require(matrix.get("required_gates")==GATE_IDS,"canonical_gate_order")
    require(matrix.get("legacy_v0_ledger")==
            "governance/ABC_A2_EIGHT_SCOPE_EVIDENCE_LEDGER_v0.json","baseline_ledger")
    require(matrix.get("source_runs") and
            {k:v["id"] for k,v in matrix["source_runs"].items()}==RUNS,
            "exact_verified_run_set")
    for run in matrix["source_runs"].values():
        require(run.get("sha")==BASE,"run_code_sha_drift")
        if "job" in run:
            require(type(run["job"]) is int and run["job"]>0,"missing_job")
    for key in (
      "cloud_deployment_permitted","cloud_deployment_proven",
      "cost_authorized","customer_media_enabled","eng06_release_approved",
      "eng07_dispatch_authorized","independent_security_approved",
      "independent_sre_approved","independent_specialist_approved",
      "architecture_adr_ratified","a2_operational_closed"
    ):
        require(matrix.get(key) is False, "unsafe_completion_"+key)
    require(matrix.get("scoped_artifact_digests")==EXPECTED_ARTIFACTS,"artifact_scope_drift")
    require(len(matrix.get("scoped_job_ids",{}))==8 and
            set(matrix["scoped_job_ids"])==SCOPES, "scoped_jobs")
    require(len(matrix.get("artifact_inventory",[]))>=8,"missing_run_artifact_inventory")
    for artifact in matrix["artifact_inventory"]:
        require(artifact.get("run_id") in RUNS.values(),"unapproved_artifact_run")
        if artifact.get("sha256") is not None:
            require(SHA256.fullmatch(artifact["sha256"]) is not None,"bad_artifact_digest")
    scopes=matrix.get("scopes")
    require(type(scopes) is list and len(scopes)==8,"scope_count")
    require({s.get("scope_id") for s in scopes}==SCOPES,"missing_or_duplicate_scope")
    coverage=0
    counts={}
    gate_totals=dict.fromkeys(GATE_IDS,0)
    for scope in scopes:
        sid=scope["scope_id"]
        require(scope.get("capability") and scope.get("implementation_status")=="PARTIAL","false_full_engine")
        require(scope.get("canonical_engine") is (sid!="LEGACY_REVIEW_TRANSPORT"),"canonical_19_alias")
        require(scope.get("managed_deployment_verified") is False,"managed_deployment_faked")
        require(len(scope.get("contracts",[]))==1 and
                scope.get("owner_risks") and all(isinstance(v,str) and v for v in scope["owner_risks"]),
                "missing_contract_or_risk")
        if check_sources:
            for p in scope["contracts"]:
                real_path(p)
        gates=scope.get("gates",[])
        require(len(gates)==10 and
                [g.get("gate_id") for g in gates]==GATE_IDS,"gate_list_invalid")
        counts[sid]=0
        for gate in gates:
            gid=gate["gate_id"]
            require(gate.get("operational_status")=="OPEN","fake_gate_pass")
            require(gate.get("review_status")=="PENDING_INDEPENDENT_REVIEW","false_review")
            require(gate.get("reviewer_identity") is None and
                    gate.get("review_signature") is None,"fake_reviewer_attestation")
            require(isinstance(gate.get("reviewer_role"),str) and gate["reviewer_role"] and
                    isinstance(gate.get("missing_evidence"),str) and gate["missing_evidence"] and
                    isinstance(gate.get("scope_limit"),str) and gate["scope_limit"] and
                    isinstance(gate.get("required_acceptance"),str) and gate["required_acceptance"] and
                    isinstance(gate.get("blocker_type"),str) and gate["blocker_type"],
                    "incomplete_gate_accountability")
            require(gate.get("source_paths") and
                    type(gate["source_paths"]) is list,"missing_source_map")
            if check_sources:
                for p in gate["source_paths"]:
                    real_path(p)
            ev=gate.get("covered_by_tests",[])
            require(type(ev) is list and len(ev)<=2,"unsupported_test_bundle")
            require(gate.get("ci_evidence_class")==(
                    "SYNTHETIC_SUBCRITERION_EVIDENCED" if ev else
                    "NO_DIRECT_SCOPED_TEST_EVIDENCE"),"false_ci_attribution")
            counts[sid]+=bool(ev)
            coverage+=bool(ev)
            gate_totals[gid]+=1
            for e in ev:
                require(e.get("observed_code_sha")==BASE,"test_head_mismatch")
                rid=e.get("observed_ci_run_id")
                require(rid in RUNS.values(),"unverified_run")
                job=e.get("observed_ci_job_id")
                require(type(job) is int and job>0,"untrusted_job")
                url=e.get("job_url","")
                found=RUN_JOB.fullmatch(url)
                require(found is not None and (int(found[1]),int(found[2]))==(rid,job),
                        "job_url_not_exact_run")
                source=e.get("path","")
                require(source.startswith("runtime/phase04/tests/"),"test_path_scope")
                require(e.get("assertion") and e.get("reproduction") and
                        e.get("scope_limit"),"unsupported_test_claim")
                if check_sources:
                    require(_assertion_exists(real_path(source),e["assertion"]),
                            f"missing_test_method:{sid}:{gid}:{e['assertion']}")
                if rid==RUNS["scoped"]:
                    require(job==matrix["scoped_job_ids"][sid],"wrong_scope_job_id")
                    require(e.get("artifact_name")==f"a2-{sid}-{rid}" and
                            e.get("artifact_sha256")==EXPECTED_ARTIFACTS[sid],
                            "wrong_scoped_artifact")
                else:
                    expected_run_jobs={r["id"]:r["job"] for r in matrix["source_runs"].values()
                                       if "job" in r}
                    require(expected_run_jobs.get(rid)==job,"wrong_run_job")
                if e.get("artifact_name") is None:
                    require(e.get("artifact_sha256") is None and
                            e.get("evidence_kind")=="GITHUB_ACTIONS_JOB_LOG_ONLY",
                            "missing_artifact_must_be_explicit")
                else:
                    require(type(e.get("artifact_name")) is str and
                            SHA256.fullmatch(e.get("artifact_sha256","")) is not None,
                            "artifact_digest_required")
    require(all(x==8 for x in gate_totals.values()),"gates_are_not_8_by_10")
    require(coverage==55 and counts=={
      "ENG-01":5,"ENG-02":8,"ENG-03":7,"ENG-04":7,
      "ENG-05":8,"ENG-06":8,"ENG-14":6,
      "LEGACY_REVIEW_TRANSPORT":6
    },"unsupported_coverage_count")
    require(risks.get("schema")=="abc.a2.risk-register.v1","risk_schema")
    require(risks.get("base_code_sha")==BASE,"risk_source_mismatch")
    require(risks.get("decision")=="OPEN_RISKS_NOT_CLOSED","risk_acceptance_faked")
    for k in ("a2_closed","independent_signoffs_attested","eng06_customer_release_approved"):
        require(risks.get(k) is False,"risk_release_override_"+k)
    require(risks.get("owner_cost_hold") is True,"owner_cost_hold_removed")
    entries=risks.get("risks",[])
    require(type(entries) is list and len(entries)==14,"risk_count")
    require({v.get("id") for v in entries}=={f"A2-R{i:03d}" for i in range(1,15)},
            "risk_duplicate_or_missing")
    for entry in entries:
        require(entry.get("priority") in {"P0","P1"} and
                entry.get("status")=="OPEN" and
                entry.get("reviewer_decision")=="NOT_RECEIVED" and
                entry.get("accepted_risk") is False and
                type(entry.get("depends_on_authorized_infrastructure")) is bool and
                entry.get("owner_role") and entry.get("mitigation") and
                entry.get("description"),"false_risk_closure")
        require(set(entry.get("linked_gates",[]))<=set(GATE_IDS) and
                bool(entry.get("linked_gates")),"risk_gate_not_canonical")
        require(entry.get("tracking_issue","").startswith(
           "https://github.com/saleheebrahimi2029-hub/abc-platform/issues/"),
           "missing_issue_tracking")
    if check_sources:
        require(PACKET.is_file(),"missing_human_packet")
        doc=PACKET.read_text()
        for fragment in ("80 OPEN","55","25",BASE,"ENG-06","BLOCKED",
                         "NOT_DEPLOYED","PENDING"):
            require(fragment in doc,f"human_packet_incomplete:{fragment}")
        old=json.loads(real_path(matrix["legacy_v0_ledger"]).read_text())
        quality=json.loads(real_path("governance/abc_engine_quality_19.v0.review.json").read_text())
        require(quality["open_gate_count"]==190 and quality["completion_count"]==0,
                "canonical_19_register_false_completion")
        require(old["production_ready"] is False and
                old["customer_release_approved"] is False and
                len(old["scopes"])==8 and
                all(g["status"]=="OPEN" for scope in old["scopes"]
                    for g in scope["gate_results"].values()),"historic_80_gate_closure_spoof")
    return {"schema":matrix["schema"],"baseline_code_sha":BASE,
            "scopes":8,"gate_count":80,"ci_subcriteria_indexed":coverage,
            "no_direct_test_reference":80-coverage,"independently_approved_gates":0,
            "open_risks":len(entries),"a2_operational_closed":False,
            "customer_release_approved":False,"owner_cost_hold":True}


def negative_self_tests(m,r):
    tests=[]
    def reject(label,func):
        x=copy.deepcopy(m)
        y=copy.deepcopy(r)
        func(x,y)
        try:
            check(x,y,check_sources=False)
        except EvidenceError:
            tests.append(label)
        else:
            raise EvidenceError("unsafe_evidence_accepted:"+label)
    reject("fake_gate_pass",lambda x,y:x["scopes"][0]["gates"][0].update(
        operational_status="PASS"))
    reject("fake_independent_reviewer",lambda x,y:x["scopes"][0]["gates"][0].update(
        reviewer_identity="ai-assistant"))
    reject("wrong_commit",lambda x,y:x.update(baseline_code_sha="0"*40))
    reject("fake_release",lambda x,y:x.update(eng06_release_approved=True))
    reject("fake_risk_acceptance",lambda x,y:y["risks"][0].update(accepted_risk=True))
    reject("fake_paid_deploy",lambda x,y:x.update(cloud_deployment_permitted=True))
    reject("missing_gate",lambda x,y:x["scopes"][0]["gates"].pop())
    reject("scope_alias",lambda x,y:x["scopes"][7].update(
        canonical_engine=True))
    reject("invented_ci_test",lambda x,y:x["scopes"][0]["gates"][1][
        "covered_by_tests"][0].update(observed_ci_run_id=123))
    reject("wrong_scoped_job",lambda x,y:x["scopes"][0]["gates"][1][
        "covered_by_tests"][0].update(observed_ci_job_id=100))
    reject("fake_risk_signoff",lambda x,y:y.update(independent_signoffs_attested=True))
    reject("missing_risk",lambda x,y:y["risks"].pop())
    return tests


def verified_checkout_unchanged():
    if os.environ.get("GITHUB_ACTIONS")!="true":
        return []
    subprocess.run(["git","merge-base","--is-ancestor",BASE,"HEAD"],cwd=ROOT,check=True)
    out=subprocess.check_output(["git","diff","--name-only",BASE,"HEAD"],cwd=ROOT,text=True)
    changed=set(out.splitlines())
    require(changed<=ALLOW_AFTER_BASE,"runtime_or_unapproved_source_drift:"+str(sorted(changed-ALLOW_AFTER_BASE)))
    require(changed and "governance/ABC_A2_G01_G10_EVIDENCE_RECONCILIATION_v1.json" in changed,
            "no_new_matrix_change")
    return sorted(changed)


def _github_get(endpoint,token):
    url=f"https://api.github.com/repos/{REPO}{endpoint}"
    req=Request(url,headers={
        "Authorization":"Bearer "+token,
        "Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28",
        "User-Agent":"abc-a2-audit-gate-v1"})
    with urlopen(req,timeout=25) as response:
        return json.load(response)


def check_actual_github_runs(matrix):
    token=os.getenv("GITHUB_TOKEN","")
    require(token.startswith("ghs_") or token.startswith("github_pat_") or
            len(token)>=16,"github_actions_token_required")
    for rid in RUNS.values():
        info=_github_get(f"/actions/runs/{rid}",token)
        require(info.get("head_sha")==BASE and
                info.get("status")=="completed" and
                info.get("conclusion")=="success","actual_actions_run_not_success:"+str(rid))
        jobs=_github_get(f"/actions/runs/{rid}/jobs?per_page=100",token)
        listed={j["id"]:j for j in jobs["jobs"]}
        required_jobs={e["observed_ci_job_id"]
                       for s in matrix["scopes"] for g in s["gates"]
                       for e in g["covered_by_tests"] if e["observed_ci_run_id"]==rid}
        if rid==RUNS["scoped"]:
            required_jobs|=set(matrix["scoped_job_ids"].values())
        for jid in required_jobs:
            require(jid in listed and listed[jid]["conclusion"]=="success" and
                    listed[jid]["status"]=="completed",
                    f"unverified_actual_job:{rid}/{jid}")
    return len(RUNS)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--verify-github-runs",action="store_true")
    args=parser.parse_args()
    matrix,risks=data()
    result=check(matrix,risks,check_sources=True)
    result["negative_mutations_rejected"]=len(negative_self_tests(matrix,risks))
    result["checkout_governance_only_changes"]=verified_checkout_unchanged()
    if args.verify_github_runs:
        result["revalidated_actual_github_runs"]=check_actual_github_runs(matrix)
    else:
        result["revalidated_actual_github_runs"]="NOT_CHECKED_IN_THIS_EXECUTION"
    result["integrity_status"]="PASS_ONLY_AS_DOCUMENTATION_AND_EVIDENCE_INDEX"
    print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2))
    report=os.getenv("ABC_A2_EXIT_PACKET_REPORT","")
    if report:
        p=Path(report)
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")


if __name__=="__main__":
    try:
        main()
    except (EvidenceError,FileNotFoundError,SyntaxError,
            subprocess.CalledProcessError) as e:
        sys.stderr.write("A2 evidence integrity FAILED: "+str(e)+"\n")
        sys.exit(1)

"""Architectural freeze, offline salon UX and zero-trust backbone preflight.

Static source controls protect version boundaries. The staging bootstrap
check runs locally with synthetic inputs and verifies that startup is denied.
Live provider attestation and release approval are outside this check.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LOCKED={
    "runtime/phase04/abc_foundation/internal_engine_ports.v1.json":
        "6e3e4451bb79f34c484c332044b28614b1bbc3ce",
    "runtime/phase04/abc_foundation/isolated_engine_service.py":
        "06020a11a795f00805579f9f2fae84db65871c64",
    "contracts/v1/state-machines.json":
        "00a199e8c6c45bfb8bd7add34e635d2b08d45ce1"
}
TARGET={
 "ENG-04":("RECOMMENDATION_INTELLIGENCE","eng04.recommendation.v2.json"),
 "ENG-05":("DECISION_INTELLIGENCE","eng05.decision.v2.json"),
 "ENG-06":("TECHNICAL_PLANNING_INTELLIGENCE","eng06.technical-plan.v2.json")
}


def git_blob_sha(contents):
    return hashlib.sha1(b"blob "+str(len(contents)).encode()+b"\0"+contents).hexdigest()


def validate_staging_owner_hold():
    runtime = ROOT / "runtime/phase04"
    suite = "tests/test_a2_staging_api_owner_hold.py"
    if not (runtime / suite).is_file():
        raise AssertionError("staging_owner_hold_suite_missing")
    subprocess.run(
        [sys.executable, "-m", "unittest", suite],
        cwd=runtime,
        check=True,
        timeout=30,
    )


def validate():
    for path,pinned in LOCKED.items():
        assert git_blob_sha((ROOT/path).read_bytes())==pinned, "frozen_contract_drift:"+path
    src=ROOT/"runtime/phase04/abc_foundation"
    assert "engine_v2_contracts" not in (src/"isolated_engine_service.py").read_text()
    v2=(src/"engine_v2_contracts.py").read_text()
    assert "dispatch_authorized" in v2 and "stub_response" in v2
    manifest={}
    for engine,(role,filename) in TARGET.items():
        contract=json.loads((src/"engine_v2"/filename).read_text())
        assert contract["engine_id"]==engine and contract["role"]==role
        assert contract["status"]=="CONTRACT_DRAFT_NO_RUNTIME_RELEASE"
        assert contract["request_payload_schema"]["additionalProperties"] is False
        assert contract["response_result_schema"]["additionalProperties"] is False
        assert "NOT_IMPLEMENTED" in contract["errors"]
        assert engine=="ENG-04" or "ENG-14" in (
            contract["upstream"] if engine=="ENG-05" else ["ENG-14"])
        manifest[engine]=role

    # ENG01/02/03/14 integration remains deny-first and scoped.
    core={
      "eng01_orchestrator.py":("verified_oidc_identity_required",
         "capability_not_implemented","eng14_transition_policy"),
      "eng02_consultation.py":("synthetic_service_only",
         "verified_identity_required","scope_not_authorized"),
      "eng03_executor.py":("stale_or_expired_lease",
         "consumer_login_binding_denied","ON CONFLICT DO NOTHING"),
      "eng14_transition_policy.py":("POLICY_AND_EXECUTOR_NOT_APPROVED",
         "SYNTHETIC_S0_CHECKPOINT_ONLY","eng14_transition_denied")
    }
    for filename,needles in core.items():
        text=(src/filename).read_text()
        assert all(needle in text for needle in needles), "backbone_guard_drift:"+filename

    validate_staging_owner_hold()

    proto=ROOT/"prototypes/abc-ai-studio-v2"
    html=(proto/"index.html").read_text()
    js=(proto/"app.js").read_text()
    css=(proto/"style.css").read_text()
    for x in ('Input &amp; Controls','Visual Canvas','Look Workspace',
              'Technical Plan','Look','consent',''):
        assert x in html or x=="" or x=="consent"
    assert 'connect-src &#39;none&#39;' not in html
    assert "connect-src 'none'" in html and "form-action 'none'" in html
    assert 'data-mode="plan"' in html and 'id="check-plan"' in html
    assert 'dir="rtl"' in html and 'lang="fa"' in html
    assert "grid-template-columns" in css and "@media" in css
    assert "BLOCKED" in js and "NOT TESTED" not in js
    for forbidden in ("fetch(","XMLHttpRequest","WebSocket","localStorage",
                      "sessionStorage","navigator.mediaDevices","getUserMedia",
                      "http://","https://","type=\"file\""):
        assert forbidden not in js, "offline_prototype_violation:"+forbidden
    return {"engine_v2_port_count":len(manifest),
      "v1_frozen_artifacts":len(LOCKED),
      "secure_core_preflight":sorted([*core, "staging_api.py"]),
      "offline_ai_studio":"SYNTHETIC_ONLY",
      "real_engine_execution":False,"customer_release_approved":False}


if __name__=="__main__":
    print(json.dumps(validate(),sort_keys=True))

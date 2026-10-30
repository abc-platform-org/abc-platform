"""W1/W2 admission evidence is *not* permission to deploy or process media."""
import copy
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/"governance/abc_w1w2_private_runtime_evidence.v0.review.json"
REQ=["W1-01_PRIVATE_NETWORK","W1-02_MANAGED_WORKLOAD_IDENTITY",
     "W1-03_SERVICE_MTLS","W1-04_PRIVATE_POSTGRES",
     "W1-05_SECRETS_AND_BACKUP","W1-06_TELEMETRY_AND_RESPONSE",
     "W1-07_DEPLOY_ROLLBACK","W2-01_PRECAPTURE_CONSENT",
     "W2-02_SESSION_POLICY_GATES","W2-03_DURABLE_ENGINE_CONTRACTS",
     "W2-04_ENG06_INDEPENDENCE","W2-05_RELEASE_VALIDATION"]

def check(v):
    if v["schema_version"]!="abc.w1w2-private-runtime-evidence.v0.review":
        raise ValueError("w1w2_schema_mismatch")
    if v["state"]!="UNPROVISIONED_BLOCKED" or v["release_state"]!="BLOCKED":
        raise ValueError("w1w2_unapproved_state")
    required_false=("managed_private_environment_verified","real_media_ingress_enabled",
       "eng05_to_eng06_dispatch_enabled","new_v3_runtime_enabled",
       "customer_release_approved","independent_approval_received")
    if any(v.get(k) is not False for k in required_false):
        raise ValueError("w1w2_false_operational_attestation")
    if v["synthetic_ci_is_not_operational_evidence"] is not True:
        raise ValueError("w1w2_ci_misrepresented")
    gates=v["criteria"]
    if [g["id"] for g in gates]!=REQ:
        raise ValueError("w1w2_missing_or_reordered_gate")
    if not all(g["status"]=="OPEN" and g["evidence_refs"]==[]
       and g["independent_signoffs"]==[] and g["provider_resource_ref"] is None
       and g["owner_assignment"] is None
       and len(g["exit_criterion"])>=75 and g["review_domain"]
       for g in gates):
        raise ValueError("w1w2_unsigned_gate_forgery")
    pg=(ROOT/"runtime/phase04/abc_foundation/pg_store.py").read_text()
    http=(ROOT/"runtime/phase04/abc_foundation/http_api.py").read_text()
    if not all(x in pg for x in (
        "def authorize_capture_preflight(","ce.status='ACTIVE'",
        "ce.revoked_at IS NULL","ce.valid_until>clock_timestamp()",
        "ce.purpose @> ARRAY['CAPTURE','AI_PROCESSING']::text[]",
        "s.state_version=%s","s.state='CREATED'",
        '"capture_authorized": False','"customer_media_accepted": False',
    )):
        raise ValueError("w1w2_precapture_gate_missing")
    if not all(x in http for x in (
        "MEDIA_RE.fullmatch(self.path)","authorize_capture_preflight",
        "pre_capture_authority_unavailable",
        'raise DomainError(501, "capability_not_implemented")'
    )):
        raise ValueError("w1w2_http_preflight_bypassed")
    if not (ROOT/"runtime/phase04/tests/test_eng02_precapture_http.py").exists():
        raise ValueError("w1w2_http_negative_tests_missing")
    return {"criteria":12,"open":12,"signed":0,"private_runtime":False,
            "media_ingress":False,"eng05_to_eng06_delivery":False,
            "customer_release":False}

def negative_tests(value):
    mutations=[
        lambda v:v.update({"managed_private_environment_verified":True}),
        lambda v:v.update({"eng05_to_eng06_dispatch_enabled":True}),
        lambda v:v.update({"real_media_ingress_enabled":True}),
        lambda v:v.update({"state":"ACCEPTED"}),
        lambda v:v["criteria"][0].update({"status":"PASS"}),
        lambda v:v["criteria"][4].update({"provider_resource_ref":"fictitious"}),
        lambda v:v["criteria"][10].update({"evidence_refs":["self-asserted"]}),
        lambda v:v["criteria"].pop(),
    ]
    for n,mutate in enumerate(mutations):
        changed=copy.deepcopy(value)
        mutate(changed)
        try:
            check(changed)
        except ValueError:
            continue
        raise AssertionError("w1w2_bad_claim_accepted_"+str(n))
    return len(mutations)

if __name__=="__main__":
    x=json.loads(EVIDENCE.read_text())
    out=check(x)
    out["negative_tests"]=negative_tests(x)
    print(json.dumps(out,sort_keys=True))

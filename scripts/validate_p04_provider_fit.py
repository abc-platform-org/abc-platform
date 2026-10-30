"""Phase04 provider-fit and nonactive private commissioning policy.

Static checks only. They DO NOT attest provider network, secret mounts,
money approval or deployed workload identity. Fail closed for any proposal
that substitutes public web or Render-managed Postgres for ABC physical mTLS.
"""
import json
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]
DECISION=ROOT/"governance/phase04_infrastructure_selection.v1.json"
CANDIDATE=ROOT/"infra/render/p04_private_services.nonactive.candidate.yaml"
EXPECTED={
    "abc-p04-private-api":("pserv","python -m abc_foundation.staging_api"),
    "abc-eng04-private-synthetic":("pserv","python -m abc_foundation.private_engine_service_server"),
    "abc-eng05-private-synthetic":("pserv","python -m abc_foundation.private_engine_service_server"),
    "abc-eng06-private-synthetic":("pserv","python -m abc_foundation.private_engine_service_server"),
    "abc-eng03-worker":("worker","python -m abc_foundation.staging_worker")
}
NEVER={"ABC_PG_DSN","ABC_WORKER_DSN","ABC_TLS_KEY_FILE",
       "ABC_API_TLS_KEY_FILE","ABC_OIDC_JWKS_URI","ABC_DB_CERT_SERIAL"}
BRANCH="security/p04-distributed-replay-managed-db-v2-gate-20261030"


def validate(selection,blueprint):
    assert selection["schema_version"]=="abc.phase04.infrastructure-selection.v1"
    assert selection["decision_status"]=="CANDIDATE_REQUIRES_OWNER_OPERATOR_COST_SECURITY_APPROVAL"
    assert selection["deployment_authorized"] is False
    assert selection["billing_authorized"] is False
    assert selection["production_release_authorized"] is False
    assert selection["workspace"]["current_services"]==0
    assert selection["workspace"]["current_postgres"]==0
    assert selection["compute"]["network"]=="PRIVATE_SERVICE_PSERV"
    assert selection["compute"]["v2_live_dispatch"]=="DISABLED_PENDING_REAL_SCOPE_AUTHORITY"
    assert selection["database"]["selection"]=="EXTERNALLY_CONTROLLED_PRIVATE_POSTGRES16_REQUIRED"
    assert selection["database"]["render_managed_postgres_acceptable"] is False
    assert selection["database"]["provisioned"] is False
    assert selection["identity"]["pki_provisioned"] is False
    assert selection["identity"]["secrets_manager_configured"] is False
    owner=selection["owner_approval"]
    assert owner["monthly_spend_cap_usd"] is None
    assert owner["approver"] is None
    assert owner["approved_at"] is None
    assert owner["independent_security_approval"] is False
    assert isinstance(blueprint,dict) and set(blueprint)=={"services"}
    svcs=blueprint["services"]
    assert len(svcs)==5
    assert {s["name"] for s in svcs}==set(EXPECTED)
    assert not any(s.get("type")=="web" for s in svcs)
    for s in svcs:
        service_type,command=EXPECTED[s["name"]]
        assert s["type"]==service_type and s["dockerCommand"]==command
        assert s["runtime"]=="docker" and s["region"]=="frankfurt"
        assert s["branch"]==BRANCH and s["autoDeployTrigger"]=="off"
        assert s["plan"]=="starter" and s["numInstances"]==1
        assert s["dockerContext"]=="runtime/phase04"
        assert s["dockerfilePath"]=="runtime/phase04/Dockerfile"
        items=s["envVars"]
        env={e["key"]:e for e in items}
        assert len(items)==len(env)
        assert env["ABC_ENV"].get("value")=="STAGING_PRIVATE"
        assert env["ABC_STAGING_PURPOSE"].get("value")=="SYNTHETIC_NO_CLIENT_DATA"
        expected_net="RENDER_PRIVATE_SERVICE" if service_type=="pserv" else "RENDER_BACKGROUND_WORKER"
        assert env["ABC_NETWORK_BOUNDARY"].get("value")==expected_net
        for key in NEVER.intersection(env):
            assert env[key].get("sync") is False
            assert set(env[key])=={"key","sync"}
        assert not any("fromDatabase" in e or "fromService" in e for e in items)
        assert not any(e["key"].endswith("_PASSWORD") for e in items)
    return {"candidate_verified":True,"services":5,
        "public_services":0,"render_database_resources":0,
        "infrastructure_provisioned":False,"deployment_allowed":False,
        "phase04_complete":False}


def main():
    results=validate(json.loads(DECISION.read_text()),
         yaml.safe_load(CANDIDATE.read_text()))
    print(json.dumps(results,sort_keys=True))


if __name__=="__main__":
    main()

"""Fail-closed static policy for Render private staging Blueprint.

This checks repository policy, NOT actual Render resources or runtime secrets.
"""
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]
BLUEPRINT=ROOT/"infra/render/staging.render.yaml"
obj=yaml.safe_load(BLUEPRINT.read_text())
if not isinstance(obj,dict) or set(obj)!={"services","databases"}:
    raise SystemExit("unexpected_blueprint_topology")
dbs=obj["databases"]
services=obj["services"]
assert len(dbs)==1 and len(services)==2, "must be exactly one DB and two services"
db=dbs[0]
assert db["name"]=="abc-p04-staging-pg"
assert db["region"]=="frankfurt" and db["postgresMajorVersion"]=="16"
assert db["ipAllowList"]==[], "external Postgres ingress MUST be disabled"
assert db["user"]=="abc_staging_migrator", "no application user may own schema"
assert db["databaseName"]=="abc_staging"
assert db["plan"] not in ("free",None)
assert {x["type"] for x in services}=={"pserv","worker"}, "public service prohibited"
assert {x["name"] for x in services}=={"abc-p04-private-api","abc-p04-session-index-worker"}
for svc in services:
    assert svc["runtime"]=="docker"
    assert svc["branch"]=="foundation/phase-04-runtime-20261029"
    assert svc["autoDeployTrigger"]=="off", "no automatic staging deploy from draft"
    assert svc["region"]=="frankfurt"
    assert svc["numInstances"]==1
    assert svc["dockerContext"]=="runtime/phase04"
    assert svc["dockerfilePath"]=="runtime/phase04/Dockerfile"
    env=svc["envVars"]
    names={v["key"] for v in env}
    assert len(names)==len(env)
    mapping={v["key"]:v for v in env}
    assert mapping["ABC_ENV"].get("value")=="STAGING_PRIVATE"
    assert mapping["ABC_STAGING_PURPOSE"].get("value")=="SYNTHETIC_NO_CLIENT_DATA"
    assert all("fromDatabase" not in v and "fromService" not in v for v in env), \
        "never inject migrator credentials into runtime"
    for v in env:
        if v["key"].endswith("_DSN") or v["key"] in ("ABC_OIDC_ISSUER","ABC_OIDC_AUDIENCE","ABC_OIDC_JWKS_URI","ABC_CONSUMER_ID"):
            assert v.get("sync") is False and "value" not in v, "runtime secrets must be set out-of-band"
        if v["key"].endswith("_PASSWORD") or v["key"]=="ABC_STAGING_MIGRATOR_DSN":
            raise AssertionError("privileged secret in runtime environment")
    if svc["type"]=="pserv":
        assert mapping["ABC_NETWORK_BOUNDARY"]["value"]=="RENDER_PRIVATE_SERVICE"
        assert mapping.keys()>={"ABC_PG_DSN","ABC_OIDC_ISSUER","ABC_OIDC_AUDIENCE","ABC_OIDC_JWKS_URI"}
        assert svc["dockerCommand"]=="python -m abc_foundation.staging_api"
    else:
        assert mapping["ABC_NETWORK_BOUNDARY"]["value"]=="RENDER_BACKGROUND_WORKER"
        assert mapping.keys()>={"ABC_WORKER_DSN","ABC_CONSUMER_ID"}
        assert svc["dockerCommand"]=="python -m abc_foundation.staging_worker"
print("PASS: private-only staging Blueprint, no automatic deploy or public DB and no privileged runtime DSN")

"""Six v2-to-19 review adapters must never auto-migrate or approve release."""
import json
from pathlib import Path
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[1]
def validate():
    r=json.loads((ROOT/"governance/abc_v2_to_19_adapters.v0.review.json").read_text())
    s=json.loads((ROOT/"contracts/review/v2_to_19_adapter_projection.v0.schema.json").read_text())
    c=json.loads((ROOT/"governance/abc_engine_registry_19.v0.review.json").read_text())
    Draft202012Validator.check_schema(s)
    assert r["decision_status"]=="CODE_REVIEW_ONLY"
    assert r["owner_signoff"] is False
    assert r["live_dispatch_enabled"] is False
    assert r["customer_release_approved"] is False
    assert r["source_protocol"]==c["frozen_v2_draft_api"]
    assert r["target_protocol"]==c["future_canonical_protocol"]
    assert len(r["adapters"])==6
    assert len(s["allOf"][0]["oneOf"])==6
    assert len({x["adapter_id"] for x in r["adapters"]})==6
    return {"review_adapters":6,"migrations_complete":0,"release":False}
if __name__=="__main__":
    print(json.dumps(validate(),sort_keys=True))

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
    actual={(x["adapter_id"],x["source_engine"],x["target_engine"])
            for x in r["adapters"]}
    expected={
      ("A04_TO_06_DECISION_INPUT","ENG-04","ENG-06"),
      ("A04_TO_07_LOOK_SPEC_INPUT","ENG-04","ENG-07"),
      ("A05_TO_06_DECISION_EVIDENCE","ENG-05","ENG-06"),
      ("A06_TO_15_PLAN_CANDIDATE","ENG-06","ENG-15"),
      ("A04_PIXEL_TO_11_QA_EVIDENCE","ENG-04","ENG-11"),
      ("A06_SOURCE_TO_16_REVIEW_EVIDENCE","ENG-06","ENG-16")}
    assert actual==expected
    assert {x["target_engine"] for x in r["adapters"]}<={
        x["engine_id"] for x in c["engines"]}
    for index,item in enumerate(r["adapters"]):
        assert item["runtime_enabled"] is False
        assert item["migration_status"]=="UNMIGRATED"
        p=s["allOf"][0]["oneOf"][index]["properties"]
        assert p["adapter_id"]["const"]==item["adapter_id"]
        assert p["source_engine"]["const"]==item["source_engine"]
        assert p["target_engine"]["const"]==item["target_engine"]
        assert p["projection"]["additionalProperties"] is False
    return {"review_adapters":6,"migrations_complete":0,"release":False}
if __name__=="__main__":
    print(json.dumps(validate(),sort_keys=True))

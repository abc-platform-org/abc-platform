"""Fail-closed static evidence for six A1 adapter runtime bindings.

A conceptual registry edge is not evidence of a physical producer/consumer.
Never infer operational authorization from matching engine numbers.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=ROOT/"governance/abc_v2_to_19_adapters.v0.review.json"
MIGRATIONS=ROOT/"runtime/phase04/migrations"
RUNTIME=ROOT/"runtime/phase04/abc_foundation"

def build():
    registry=json.loads(REGISTRY.read_text())
    sql_files=sorted(MIGRATIONS.glob("*.sql"))
    assert len(sql_files)==31
    sources=[*sql_files,*sorted(RUNTIME.rglob("*.py"))]
    records=[]
    for adapter in registry["adapters"]:
        key=adapter["adapter_id"]
        occurrences=[]
        for source in sources:
            for line_no,line in enumerate(source.read_text(encoding="utf-8").splitlines(),1):
                if key in line:
                    occurrences.append({"file":str(source.relative_to(ROOT)),
                                        "line":line_no,"text":line.strip()[:240]})
        # No callsite is verified by a mere string match. Require explicit
        # separately-reviewed source and destination bindings.
        records.append({"adapter_id":key,"source_engine":adapter["source_engine"],
                        "target_engine":adapter["target_engine"],
                        "literal_references":occurrences,
                        "producer_write_callsite":"UNVERIFIED",
                        "consumer_read_callsite":"UNVERIFIED",
                        "source_table_or_queue":"UNVERIFIED",
                        "target_table_or_queue":"UNVERIFIED",
                        "service_principal":"UNVERIFIED",
                        "wire_schema":"UNVERIFIED",
                        "live_route":False})
    assert len(records)==6 and len({r["adapter_id"] for r in records})==6
    # Quarantine storage is never proof of live engine routes.
    bridge_sql=(MIGRATIONS/"0031_a1_six_adapter_bridge_quarantine.sql").read_text()
    for table in ("a1_bridge_registry","a1_bridge_legacy","a1_bridge_shadow"):
        assert "CREATE TABLE IF NOT EXISTS abc."+table in bridge_sql
    for forbidden in ("enabled boolean NOT NULL DEFAULT true",
                      "dispatch_authorized boolean NOT NULL DEFAULT true",
                      "customer_release_approved boolean NOT NULL DEFAULT true"):
        assert forbidden not in bridge_sql
    # Bridge tables are quarantine storage, never evidence of live engine routes.
    bridge_sql=(MIGRATIONS/"0031_a1_six_adapter_bridge_quarantine.sql").read_text()
    for table in ("a1_bridge_registry","a1_bridge_legacy","a1_bridge_shadow"):
        assert "CREATE TABLE IF NOT EXISTS abc."+table in bridge_sql
    for forbidden in ("enabled boolean NOT NULL DEFAULT true",
                      "dispatch_authorized boolean NOT NULL DEFAULT true",
                      "customer_release_approved boolean NOT NULL DEFAULT true"):
        assert forbidden not in bridge_sql
    assert all(not a["runtime_enabled"] for a in registry["adapters"])
    assert not registry["live_dispatch_enabled"] and not registry["customer_release_approved"]
    return {"classification":"STATIC_SOURCE_ONLY_NOT_RUNTIME_PROOF",
            "migration_count":len(sql_files),"adapters":records,
            "complete_verified_runtime_bindings":0,"a1_closure_authorized":False}

if __name__=="__main__":
    print(json.dumps(build(),indent=2,sort_keys=True))

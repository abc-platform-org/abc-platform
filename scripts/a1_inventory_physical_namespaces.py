"""A1 physical namespace inventory: deterministic static DDL and reference scan.

This is not live PostgreSQL catalog introspection and does not migrate data.
"""
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MIGRATIONS=ROOT/"runtime/phase04/migrations"
RUNTIME=ROOT/"runtime/phase04/abc_foundation"
EXPECTED=tuple(f"{n:04d}" for n in range(1,31))
DDL={
 "tables":r"\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?abc\.([a-z][a-z0-9_]*)",
 "functions":r"\bCREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+abc\.([a-z][a-z0-9_]*)",
 "roles":r"\bCREATE\s+ROLE\s+([a-z][a-z0-9_]*)",
 "policies":r"\bCREATE\s+POLICY\s+([a-z][a-z0-9_]*)",
 "triggers":r"\bCREATE\s+TRIGGER\s+([a-z][a-z0-9_]*)",
}
REF=re.compile(r"\babc\.(eng(?:0[1-9]|1[0-9])_[a-z0-9_]+)\b",re.I)
def build():
    files=sorted(MIGRATIONS.glob("*.sql"))
    assert len(files)==30 and tuple(p.name[:4] for p in files)==EXPECTED, "migration_sequence_drift"
    entries=[]
    declared=set()
    for p in files:
        sql=p.read_text(encoding="utf-8")
        items={k:sorted(set(re.findall(v,sql,re.I))) for k,v in DDL.items()}
        declared.update(items["tables"])
        entries.append({"migration":p.name,"ddl":items,
                        "legacy_references":sorted(set(REF.findall(sql))),
                        "has_grant":"GRANT " in sql.upper(),
                        "has_revoke":"REVOKE " in sql.upper()})
    modules={}
    for p in sorted(RUNTIME.glob("*.py")):
        refs=sorted(set(REF.findall(p.read_text(encoding="utf-8"))))
        if refs: modules[p.name]=refs
    assert "eng19_review_inbox" in declared and "eng06_ci_jobs" in declared
    assert "eng06_ci_results" in declared and "eng19_review_edges" in declared
    return {"classification":"STATIC_SOURCE_INVENTORY_NOT_LIVE_CATALOG",
            "migration_count":len(entries),"migrations":entries,
            "runtime_references":modules,
            "declared_table_count":len(declared),
            "production_catalog_verified":False,
            "canonical_dispatch_authorized":False}
if __name__=="__main__":
    print(json.dumps(build(),indent=2,sort_keys=True))

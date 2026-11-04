"""Fail-closed A2 evidence-ledger validation; does not certify engine completion."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ledger=json.loads((ROOT/"governance/ABC_A2_EIGHT_SCOPE_EVIDENCE_LEDGER_v0.json").read_text())
assert ledger["stage"]=="A2"
assert ledger["production_ready"] is False
assert ledger["customer_release_approved"] is False
expected={"ENG-01","ENG-02","ENG-03","ENG-04","ENG-05","ENG-06","ENG-14","LEGACY_REVIEW_TRANSPORT"}
assert {s["scope_id"] for s in ledger["scopes"]}==expected
migration_dir=ROOT/"runtime/phase04/migrations"
for scope in ledger["scopes"]:
    candidates=scope["source_candidates"]
    for module in candidates["modules"]:
        assert (ROOT/"runtime/phase04/abc_foundation"/module).is_file(), module
    for test in candidates["tests"]:
        assert (ROOT/"runtime/phase04/tests"/test).is_file(), test
    for prefix in candidates["migrations"]:
        matches=list(migration_dir.glob(prefix+"_*.sql"))
        assert len(matches)==1, (scope["scope_id"],prefix)

    assert scope["implementation_status"] in {"IMPLEMENTED","PARTIAL","MISSING"}
    assert scope["independent_deployment_verified"] is False
    assert set(scope["gate_results"])=={f"G{i:02d}" for i in range(1,11)}
    for gate in scope["gate_results"].values():
        assert gate["status"] in {"PASS","OPEN","FAIL"}
        if gate["status"]=="PASS":
            assert gate["evidence"] and gate["reviewer"], "PASS requires evidence and reviewer"
        if gate["status"]=="OPEN":
            assert not gate["evidence"] and gate["reviewer"] is None
print("A2 ledger valid: 8 scopes, 80 explicit gates; no unsupported PASS")

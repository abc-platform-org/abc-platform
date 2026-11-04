"""Fail-closed A2 evidence-ledger validation; does not certify engine completion."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ledger=json.loads((ROOT/"governance/ABC_A2_EIGHT_SCOPE_EVIDENCE_LEDGER_v0.json").read_text())
assert ledger["stage"]=="A2"
assert ledger["production_ready"] is False
assert ledger["customer_release_approved"] is False
quality=json.loads((ROOT/"governance/abc_engine_quality_19.v0.review.json").read_text())
assert ledger["canonical_required_gates"]==quality["required_gates"]
expected={"ENG-01","ENG-02","ENG-03","ENG-04","ENG-05","ENG-06","ENG-14","LEGACY_REVIEW_TRANSPORT"}
assert len(ledger["scopes"])==len(expected)
assert {s["scope_id"] for s in ledger["scopes"]}==expected
ci=ledger["ci_validation_evidence"]
assert ci["conclusion"]=="success"
assert ci["run_number"]==498
assert ci["commit_sha"]=="58d45503c5f94bb5fbcf1545a8e7a7ad69dd8069"
assert ci["scope"]=="FOUNDATION_INTEGRATION_AND_LEDGER_STRUCTURE_ONLY"
assert ledger["gate_evidence_assessment"]["reviewer_authority"]=="NOT_PROVISIONED"
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

    assert scope["scope_id"]!="LEGACY_REVIEW_TRANSPORT" or scope["capability"]=="legacy_transport"
    assert scope["implementation_status"] in {"IMPLEMENTED","PARTIAL","MISSING"}
    assert scope["independent_deployment_verified"] is False
    assert set(scope["gate_results"])==set(ledger["canonical_required_gates"])
    assert set(scope["gate_evidence_candidates"])==set(ledger["canonical_required_gates"])
    for gate_id,candidate in scope["gate_evidence_candidates"].items():
        assert candidate["review_status"]=="NOT_ATTESTED", gate_id
        assert candidate["ci_sha"]==ci["commit_sha"], gate_id
        assert candidate["ci_run"]==ci["url"], gate_id
        for path in candidate["candidate_paths"]:
            if path.endswith("_*.sql"):
                assert len(list(ROOT.glob(path)))==1, path
            else:
                assert (ROOT/path).is_file(), path
    for gate in scope["gate_results"].values():
        assert gate["status"] in {"PASS","OPEN","FAIL"}
        if gate["status"]=="PASS":
            assert gate["evidence"] and gate["reviewer"], "PASS requires evidence and reviewer"
        if gate["status"]=="OPEN":
            assert not gate["evidence"] and gate["reviewer"] is None
print("A2 ledger valid: 8 scopes, 80 explicit gates; no unsupported PASS")

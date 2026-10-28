#!/usr/bin/env python3
"""Validate design-Gate reconciliation dossier: structure, SHA provenance and non-fabricated approvals.

This does not approve Gate-00/01/02, execute engines, validate client safety, or merge PRs.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "docs/00-governance/gate-reconciliation"

docs = [
    "README.md", "SOURCE_AUDIT.md", "SINGLE_OWNER_GATE_POLICY.md",
    "MERGE_READINESS_AND_RUNBOOK.md", "OWNER_REVIEW_AND_ATTESTATION.md",
    "ISSUE_RECONCILIATION.md", "SOURCE_EXCEPTION_PROPOSALS.csv",
    "ADR_DECISION_MATRIX.csv", "RELEASE_SAFETY_DEFERRALS.csv",
    "GATE_DECISIONS.csv", "GATE_RECONCILIATION_SNAPSHOT.json",
]
for name in docs:
    path = P/name
    assert path.is_file() and path.stat().st_size > 200, f"missing/empty: {name}"

def read_csv(name):
    with (P/name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))

source = read_csv("SOURCE_EXCEPTION_PROPOSALS.csv")
assert len(source) == 3
assert {r["exception_id"] for r in source} == {"SRC-EXC-001","SRC-EXC-002","SRC-EXC-003"}
assert all(r["status"] == "UNRECOVERED_PENDING_OWNER_EXCEPTION" for r in source)
assert all(r["fallback_source_url"].startswith("https://") for r in source)
assert all(r["forbidden_inference"] and r["review_trigger"] for r in source)
assert all(r["issue"] == "2" for r in source)

adrs = read_csv("ADR_DECISION_MATRIX.csv")
assert len(adrs) == 10
assert {r["adr_id"] for r in adrs} == {f"ADR-{i:03d}" for i in range(1,11)}
for row in adrs:
    assert row["decision_status"] == "PENDING_OWNER_ATTESTATION"
    assert row["accountable_owner"] == "saleheebrahimi2029-hub"
    assert row["runtime_status"] == "NOT_IMPLEMENTED"
    f = ROOT / row["source_path"]
    assert f.is_file(), row["source_path"]
    data = f.read_bytes()
    sha = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
    assert sha == row["reviewed_blob_sha"], f"ADR Git blob SHA mismatch {row['adr_id']}: {sha} vs {row['reviewed_blob_sha']}"
    assert row["later_evidence_gate"] and row["conditions_and_nonclaims"]

deferrals = read_csv("RELEASE_SAFETY_DEFERRALS.csv")
assert len(deferrals) == 9
assert len({r["deferral_id"] for r in deferrals}) == 9
assert all(r["status"] == "PENDING_OWNER_RISK_ACCEPTANCE" for r in deferrals)
assert all(r["block_policy"].startswith("HARD_") for r in deferrals)
assert all(r["required_proof"] and r["target_gate"] for r in deferrals)

gates=read_csv("GATE_DECISIONS.csv")
assert len(gates)==3
assert {r["gate_id"] for r in gates} == {"G-00", "G-01", "G-02"}
assert all(r["approval_state"] == "NOT_APPROVED" for r in gates)
assert all(r["submitted_reviews"] == "0 reviews" for r in gates)
assert all(re.fullmatch(r"[a-f0-9]{40}", r["reviewed_original_head_sha"]) for r in gates)
assert {r["gate_id"]:r["reviewed_original_head_sha"] for r in gates} == {
    "G-00":"9d7a8ed1d079059ce99d6165664cf49b64579fa6",
    "G-01":"7f940efdfeebd373825179abe3f94a11299e2749",
    "G-02":"164c512a944faf186144fdbb0d88dcabee871ade",
}

snapshot=json.loads((P/"GATE_RECONCILIATION_SNAPSHOT.json").read_text(encoding="utf-8"))
assert snapshot["accountable_owner"] == "saleheebrahimi2029-hub"
assert snapshot["source_audit"]["exceptions_proposed"] == 3
assert snapshot["source_audit"]["exceptions_signed"] == 0
assert snapshot["design"]["adrs_proposed"] == 10
assert snapshot["design"]["adrs_formally_approved"] == 0
assert snapshot["proposed_release_deferrals"] == 9
assert snapshot["adopted_release_deferrals"] == 0
assert all(not value for value in snapshot["changes_authorized"].values())
assert snapshot["gate_status"]["G-00"] == "BLOCKED_FOR_FORMAL_APPROVAL"
assert all(g != "PASS" for g in snapshot["gate_status"].values())
assert snapshot["golden_runtime_executed_verified"] == 0
assert snapshot["phase02_contract_audit"]["found_design_defects"] == 12
assert snapshot["phase02_contract_audit"]["verified_ci_run_id"] == 40778026510
assert snapshot["reviewed_prs"][2]["head_sha"] == "164c512a944faf186144fdbb0d88dcabee871ade"
assert len(snapshot["reviewed_prs"])==3
assert all(p["submitted_reviews"]==0 and p["draft"] and not p["merged"] for p in snapshot["reviewed_prs"])

attestation=(P/"OWNER_REVIEW_AND_ATTESTATION.md").read_text(encoding="utf-8")
assert "NOT SIGNED" in attestation
for code in ["SRC-EXC-001","SRC-EXC-002","SRC-EXC-003","ADR-001","ADR-010"]:
    assert code in (attestation + "\n" + (P/"ADR_DECISION_MATRIX.csv").read_text())
assert "G-00" in (P/"README.md").read_text()
print("GATE_RECONCILIATION_DOC_PASS: 3 unsigned source exceptions, 10 ADR blob-SHA verified / unsigned, 9 unaccepted release deferrals, G00/G01/G02 not approved; 11 dossier artifacts. NO MERGE / NO RUNTIME / NO EXPERT CERTIFICATION.")

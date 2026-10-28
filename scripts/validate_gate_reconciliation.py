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
    "ISSUE_RECONCILIATION.md", "OWNER_GOVERNANCE_DIRECTIVE.md", "ADR_TECHNICAL_REVIEW.md", "DELEGATED_DESIGN_DECISION_2026-10-29.md", "SOURCE_EXCEPTION_PROPOSALS.csv",
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
assert all(r["status"] == "ACCEPTED_BOUNDED_DESIGN_ONLY_BY_DELEGATION" for r in source)
assert all(r["fallback_source_url"].startswith("https://") for r in source)
assert all(r["forbidden_inference"] and r["review_trigger"] for r in source)
assert all(r["issue"] == "2" for r in source)

adrs = read_csv("ADR_DECISION_MATRIX.csv")
review_path=P/"ADR_TECHNICAL_REVIEW.md"
review_text=review_path.read_text(encoding="utf-8")
assert "ENGINEERING_RECOMMENDATION_ONLY" in review_text
for adr_num in range(1,11):
    assert f"ADR-{adr_num:03d}" in review_text, f"missing review ADR-{adr_num:03d}"
assert "not** an actual owner GitHub review" in review_text
assert len(adrs) == 10
assert {r["adr_id"] for r in adrs} == {f"ADR-{i:03d}" for i in range(1,11)}
for row in adrs:
    assert row["decision_status"] == "ACCEPTED_DESIGN_CONDITIONAL_BY_DELEGATION"
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
assert all(r["status"] == "ADOPTED_HARD_RELEASE_BLOCK_BY_DELEGATION" for r in deferrals)
assert all(r["block_policy"].startswith("HARD_") for r in deferrals)
assert all(r["required_proof"] and r["target_gate"] for r in deferrals)

gates=read_csv("GATE_DECISIONS.csv")
assert len(gates)==3
assert {r["gate_id"] for r in gates} == {"G-00", "G-01", "G-02"}
assert all(r["approval_state"] == "DELEGATED_DESIGN_ONLY_ACCEPTED_NO_HUMAN_PR_REVIEW" for r in gates)
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
assert snapshot["source_audit"]["exceptions_design_accepted_by_delegation"] == 3
assert snapshot["design"]["adrs_design_accepted_by_delegation"] == 10
assert snapshot["design"]["adrs_formally_approved"] == 0
assert snapshot["owner_formal_gate_approval_recorded"] is False
assert snapshot["qualified_specialist_attestations"] == 0
assert snapshot["independent_privacy_legal_reviews"] == 0
assert snapshot["independent_visual_qa_reviews"] == 0
assert snapshot["delegated_decision"]["decision_id"] == "ABC-DDR-20261029-001"
assert snapshot["delegated_decision"]["actor"] == "AI_ENGINEERING_CONSULTANT_NOT_HUMAN_REVIEWER"
assert snapshot["delegated_decision"]["qualifier"] == "DESIGN_ONLY_CONDITIONAL"
assert snapshot["delegated_decision"]["signed_human_github_review"] is False
assert all(snapshot["delegated_decision"][k] is True for k in (
    "accepts_all_ten_adr_design_choices",
    "accepts_three_bounded_source_exceptions",
    "accepts_nine_hard_release_blocks",
    "conditional_pr_merging_authorized_after_exact_head_ci_and_branch_checks"))
decision=(P/"DELEGATED_DESIGN_DECISION_2026-10-29.md").read_text(encoding="utf-8")
assert "AI engineering consultant" in decision
assert "not a real GitHub human reviewer" in decision
assert "No production authorization" in decision
for code in [f"ADR-{i:03d}" for i in range(1,11)] + [f"SRC-EXC-{i:03d}" for i in range(1,4)]:
    assert code in decision, f"delegated decision missing {code}"

assert snapshot["design"]["adrs_proposed"] == 10
assert snapshot["design"]["adrs_formally_approved"] == 0
assert snapshot["owner_governance_direction"]["status"] == "USER_DIRECTIVE_ADOPTED"
assert snapshot["owner_governance_direction"]["does_not_infer_signed_git_review"] is True
assert snapshot["policy_change_approved_in_pr"] is False
assert snapshot["owner_formal_gate_approval_recorded"] is False
assert "USER_DIRECTIVE_ADOPTED_AS_PRODUCT_GOVERNANCE_POLICY" in (P/"OWNER_GOVERNANCE_DIRECTIVE.md").read_text(encoding="utf-8")
assert snapshot["proposed_release_deferrals"] == 9
assert snapshot["adopted_release_deferrals"] == 9
assert all(not value for value in snapshot["changes_authorized"].values())
assert snapshot["gate_status"]["G-00"] == "DESIGN_BASELINE_ACCEPTED_BY_DELEGATION"
assert snapshot["gate_status"]["G-01"] == "PRODUCT_DESIGN_ACCEPTED_BY_DELEGATION"
assert snapshot["gate_status"]["G-02"] == "CONTRACT_DESIGN_ACCEPTED_BY_DELEGATION"
assert all("RELEASED" not in g and "FORMAL_PASS" not in g for g in snapshot["gate_status"].values())
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
print("GATE_RECONCILIATION_DESIGN_DECISION_PASS: 3 bounded source exceptions, 10 conditional ADR designs, 9 mandatory hard release blocks, G00/G01/G02 DELEGATED DESIGN ONLY; 14 dossier artifacts. NO HUMAN REVIEW CLAIM / NO RUNTIME / NO EXPERT CERTIFICATION.")

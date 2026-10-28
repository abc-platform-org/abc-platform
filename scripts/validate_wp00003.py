#!/usr/bin/env python3
"""Validate Phase-00 WP-000-03 governance *documentation*, never runtime readiness."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "docs/00-governance/phase-00/wp-000-03"

DOCS = [
    "README.md", "ACCOUNTABILITY_AND_RACI.md", "GATE00_CLOSURE_MATRIX.csv",
    "APPROVAL_LEDGER.csv", "GITHUB_ISSUES.md", "RISK_TREATMENT_PLAN.md",
    "SOURCE_RECOVERY_DECISION.md", "SECURITY_PRIVACY_REVIEW_PROTOCOL.md",
    "SOP_SAFETY_APPROVAL_POLICY.md", "QA_ACCEPTANCE_AND_RUNBOOK.md",
    "DECISION_ASSIGNMENT_REQUEST.md", "GATE00_DECISION.md",
    "WP00003_GOVERNANCE_SNAPSHOT.json",
]
for filename in DOCS:
    f = P / filename
    assert f.is_file() and f.stat().st_size > 100, f"missing/empty {f}"

def table(file: str):
    with (P / file).open(newline="", encoding="utf-8") as h:
        return list(csv.DictReader(h))

blockers = table("GATE00_CLOSURE_MATRIX.csv")
assert len(blockers) == 14, f"expected 14 blockers, got {len(blockers)}"
assert {r["blocker_id"] for r in blockers} == {f"B-{i:03d}" for i in range(1, 15)}
assert {int(r["github_issue"]) for r in blockers} <= set(range(2, 10))
assert all(r["state"] not in {"PASS", "APPROVED", "CLOSED"} for r in blockers)
assert any(r["target_gate"] == "G-01" for r in blockers)
assert any(r["target_gate"] == "G-03" for r in blockers)

ledger = table("APPROVAL_LEDGER.csv")
assert len(ledger) == 20, f"expected 20 approval entries, got {len(ledger)}"
actual = {r["record_id"] for r in ledger}
expected = {f"ADR-{i:03d}" for i in range(1, 11)}
expected |= {f"SRC-EXC-{i:03d}" for i in range(1, 4)}
expected |= {f"GOV-A{i:02d}" for i in range(1, 7)}
expected |= {"G-00"}
assert actual == expected, f"approval registry mismatch: {actual ^ expected}"
assert all(not r["evidence_url"] and r["reviewer"] == "UNASSIGNED" for r in ledger)
assert all(r["status"].startswith(("PENDING", "PERSON_UNASSIGNED", "BLOCKED")) for r in ledger)

raci = (P / "ACCOUNTABILITY_AND_RACI.md").read_text(encoding="utf-8")
assert {f"ENG-{i:02d}" for i in range(1, 20)} <= set(re.findall(r"ENG-\d\d", raci))
for mid in range(1, 7):
    assert f"GOV-A{mid:02d}" in raci

issue_doc = (P / "GITHUB_ISSUES.md").read_text(encoding="utf-8")
for n in range(2, 10):
    assert f"/issues/{n}" in issue_doc, n

snapshot = json.loads((P / "WP00003_GOVERNANCE_SNAPSHOT.json").read_text(encoding="utf-8"))
assert snapshot["gate_00"] == "BLOCKED_FOR_FORMAL_APPROVAL"
assert snapshot["status_authority"]["real_people_verified"] == 0
assert snapshot["status_authority"]["adr_decisions_signed"] == 0
assert snapshot["status_authority"]["source_exceptions_accepted"] == 0
assert snapshot["blocker_tracking"]["total"] == 14
assert snapshot["qa"]["golden_authored"] == 120
assert snapshot["qa"]["golden_execution_verified"] == 0
assert snapshot["policy"]["may_auto_merge"] is False
assert snapshot["policy"]["main_write_allowed"] is False
assert snapshot["policy"]["notion_write_allowed"] is False

gate = (P / "GATE00_DECISION.md").read_text(encoding="utf-8")
assert "**\`BLOCKED_FOR_FORMAL_APPROVAL\`**".replace("\\", "") in gate or "BLOCKED_FOR_FORMAL_APPROVAL" in gate
assert "PERSON_UNASSIGNED" in gate
assert "AUTHORED_NOT_RUN" in gate

crosswalk = ROOT / "docs/05-delivery/PHASE_00_TRACEABILITY.csv"
assert crosswalk.is_file(), "WP-000-01 traceability must remain present"
with crosswalk.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
assert len(rows) == 64
assert len([r for r in rows if r["id"].startswith("ABC-F")]) == 18
assert len([r for r in rows if r["id"].startswith("AIS-")]) == 26
assert len([r for r in rows if r["id"].startswith("PRD-")]) == 20

print("WP00003 DOCUMENT INTEGRITY PASS: 13 artifacts / 14 blockers / 20 unsigned decision records / 19 ENG / 64 mapped requirements. Gate-00 BLOCKED; no runtime tests inferred.")

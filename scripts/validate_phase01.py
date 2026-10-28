#!/usr/bin/env python3
"""Phase-01 *document integrity* checks. Does not execute AI engines."""
from __future__ import annotations
import csv
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"docs/01-product/phase-01"
REQUIRED=[
"README.md","PRODUCT_BASELINE.md","SINGLE_OWNER_GOVERNANCE.md",
"MASTER_PRD_V1.md","AI_STUDIO_ACCEPTANCE_SPEC.md","ADAPTIVE_CONSULTATION_SPEC.md",
"SALON_OS_REQUIREMENTS.md","SESSION_JOURNEYS_AND_FAILURES.md",
"NFR_PRIVACY_AND_GOVERNANCE.md","FEATURE_RELEASE_MATRIX.csv",
"STORY_ACCEPTANCE_MATRIX.csv","SERVICE_PACK_COVERAGE.csv",
"USER_ROLE_PERMISSION_MATRIX.csv","PHASE_01_DECISIONS_AND_DEPENDENCIES.md",
"GATE_01_DECISION.md","PHASE_01_IMPLEMENTATION_BACKLOG.md",
]
for name in REQUIRED:
    f=P/name
    assert f.exists() and f.stat().st_size>200, f"Missing/empty: {name}"
def read_csv(name):
    with (P/name).open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))
f=read_csv("FEATURE_RELEASE_MATRIX.csv")
s=read_csv("STORY_ACCEPTANCE_MATRIX.csv")
assert len(f)==len(s)==64, (len(f),len(s))
ids_f=[x["id"] for x in f]
ids_s=[x["id"] for x in s]
EXPECTED=({f"ABC-F{i:02d}" for i in range(1,19)}
        |{f"AIS-{i:03d}" for i in range(1,27)}
        |{f"PRD-{i:03d}" for i in range(1,21)})
assert len(EXPECTED)==64
assert len(set(ids_f))==len(set(ids_s))==64
assert set(ids_f)==set(ids_s)==EXPECTED
for row in f:
    assert row["accountable_owner"]=="saleheebrahimi2029-hub", row["id"]
    assert row["first_release"] in {"MVP","V2","V3"}, row["id"]
    assert row["gate"] and row["phases"] and row["technical_owner"]
    assert row["implementation_status"]=="SPECIFIED_NOT_IMPLEMENTED",row["id"]
for row in s:
    assert row["owner"]=="saleheebrahimi2029-hub"
    assert row["status"]=="ACCEPTANCE_SPECIFIED_NOT_TESTED"
    assert row["user_story"].startswith("As "), row["id"]
    assert len(row["objective_acceptance_condition"])>35,row["id"]
    assert row["test_suite"] and row["gate"] and row["first_release"]

services=read_csv("SERVICE_PACK_COVERAGE.csv")
assert len(services)==11
assert len({x["family"] for x in services})==11
assert all(x["release_state"]=="NOT_RELEASED" for x in services)
assert all(x["accountable_owner"]=="saleheebrahimi2029-hub" for x in services)
assert all(x["sop_or_pro_review"] and x["specialist_evidence"] for x in services)
roles=read_csv("USER_ROLE_PERMISSION_MATRIX.csv")
assert len(roles)>=30
assert {"Client","Specialist","SalonManager","OrganizationOwner","AskABC"} <= {x["actor"] for x in roles}
assert any(x["actor"]=="Client" and x["action"]=="approve_execution_plan" and x["policy"]=="DENY" for x in roles)
assert any(x["actor"]=="PlatformOperator" and x["action"]=="approve_salon_service_plan" and x["policy"]=="DENY" for x in roles)
assert any(x["actor"]=="AskABC" and x["action"]=="execute_payment_or_inventory_mutation" and "DENY" in x["policy"] for x in roles)

baseline=(ROOT/"docs/05-delivery/PHASE_00_TRACEABILITY.csv")
assert baseline.exists()
with baseline.open(newline="",encoding="utf-8") as stream:
    old=list(csv.DictReader(stream))
assert len(old)==64
assert {x["id"] for x in old}==EXPECTED

prd=(P/"MASTER_PRD_V1.md").read_text(encoding="utf-8")
studio=(P/"AI_STUDIO_ACCEPTANCE_SPEC.md").read_text(encoding="utf-8")
for i in range(1,27):
    assert f"AIS-{i:03d}" in studio, f"AIS-{i:03d} not in spec"
for keyword in ["Transform","Try On","Compare","Inspiration","LookSpec","shared","SOP","Visual"]:
    assert keyword.lower() in (prd+"\n"+studio).lower(),keyword
gate=(P/"GATE_01_DECISION.md").read_text(encoding="utf-8")
assert "PENDING_G00_RESOLUTION_AND_OWNER_PRODUCT_SIGNOFF" in gate
assert "BLOCKED_FOR_FORMAL_APPROVAL" in gate
owner=(P/"SINGLE_OWNER_GOVERNANCE.md").read_text(encoding="utf-8")
assert "saleheebrahimi2029-hub" in owner
assert "independent" in owner.lower()

print("PHASE01 DOC_INTEGRITY PASS: 64 requirements (18 ABC-F, 26 AIS, 20 PRD), 64 stories, 11 service packs NOT_RELEASED, 32 role rules. OWNER ASSIGNED / ENGINE NOT IMPLEMENTED / G-01 NOT FORMALLY APPROVED")

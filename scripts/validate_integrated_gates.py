#!/usr/bin/env python3
"""ABC P00/P01/P02 + governance merged-tree audit.

Audit only: validates source bytes, traceability, contracts, status, hard release
denials. It DOES NOT execute engines, certify legal/specialist QA or authorize
a production release. Run against the assembled multi-parent Git tree.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
G = ROOT / "docs/00-governance/gate-reconciliation"
P1 = ROOT / "docs/01-product/phase-01"
P2 = ROOT / "contracts/v1"
OWNER = "saleheebrahimi2029-hub"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def json_file(path):
    return json.loads(path.read_text(encoding="utf-8"))


def csv_file(path):
    with path.open(encoding="utf-8", newline="") as h:
        return list(csv.DictReader(h))


def git_blob_sha(content):
    return hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()


# P00 original ZIP provenance. The original archive had 70 entries:
# 69 manifest hashes plus the manifest itself. Repository README.md pre-existed
# and intentionally remains unchanged; archive's README bytes are stored at an
# explicitly mapped preservation path. No silent file overwrite.
manifest = json_file(ROOT / "PACKAGE_MANIFEST.json")
require(manifest["file_count"] == 69 and len(manifest["files"]) == 69, "original ZIP manifest differs")
require(manifest["target_repo"] == OWNER + "/abc-platform", "original archive targeted other repo")
remap = {
    "README.md": "docs/00-governance/original-package/README.2026-10-28.md",
}
# Original ZIP files updated by the Phase-00 decision/WP scripts are NOT
# silently overwritten. Their original Git blobs remain byte-exact in an
# archival mirror while the active docs retain the subsequent valid revisions.
superseded = [
    "CHANGELOG.md",
    "docs/00-governance/ADR_INDEX.md",
    "docs/00-governance/SOURCE_AND_AUTHORITY_REGISTER.md",
    "docs/00-governance/adrs/ADR-001.md",
    "docs/00-governance/adrs/ADR-002.md",
    "docs/00-governance/adrs/ADR-008.md",
    "docs/00-governance/adrs/ADR-009.md",
    "docs/00-governance/adrs/ADR-010.md",
    "scripts/validate_baseline.py",
]
remap.update({path: "docs/00-governance/original-package/source-snapshot/" + path for path in superseded})
require(len(remap) == 10 and set(remap) <= set(manifest["files"]), "source exception mapping not exact")
for original in remap:
    current = ROOT/original
    require(current.is_file(), f"original path removed during source preservation: {original}")
    require(hashlib.sha256(current.read_bytes()).hexdigest() != manifest["files"][original],
            f"unexpected source snapshot remap not needed or conflict: {original}")
sha_mismatches = []
for original, expected_sha256 in manifest["files"].items():
    path = ROOT / remap.get(original, original)
    require(path.is_file(), f"missing archive source entry: {original} => {path}")
    found = hashlib.sha256(path.read_bytes()).hexdigest()
    if found != expected_sha256:
        sha_mismatches.append((original, found, expected_sha256))
require(not sha_mismatches, f"ORIGINAL ARCHIVE SHA256 MISMATCH: {sha_mismatches}")
original_readme = ROOT / remap["README.md"]
require(
    git_blob_sha(original_readme.read_bytes()) == "59c671843d5320e82d8e9d696b3f1b8915469949",
    "archive README exact Git blob mismatch",
)
require(
    (ROOT / "README.md").read_bytes() != original_readme.read_bytes(),
    "existing 82-byte README intentionally preserved, not falsely claimed equal",
)
require(
    git_blob_sha((ROOT / "PACKAGE_MANIFEST.json").read_bytes()) ==
    "03071a7fccf1cafc17f8157cb397be1dd7a358eb",
    "original manifest modified",
)
require((ROOT / "README.md").exists(), "repository root README unexpectedly deleted")

# Scope, source authority and risk: DESIGN_ONLY, not qualified product release.
sources = csv_file(G / "SOURCE_EXCEPTION_PROPOSALS.csv")
adrs = csv_file(G / "ADR_DECISION_MATRIX.csv")
deferrals = csv_file(G / "RELEASE_SAFETY_DEFERRALS.csv")
gates = csv_file(G / "GATE_DECISIONS.csv")
snap = json_file(G / "GATE_RECONCILIATION_SNAPSHOT.json")
require(len(sources) == 3 and len(adrs) == 10 and len(deferrals) == 9 and len(gates) == 3, "governance counts")
require({x["exception_id"] for x in sources} == {f"SRC-EXC-{i:03d}" for i in range(1, 4)}, "source exception IDs")
require(all(x["status"] == "ACCEPTED_BOUNDED_DESIGN_ONLY_BY_DELEGATION" for x in sources), "source status")
require(all(x["decision_status"] == "ACCEPTED_DESIGN_CONDITIONAL_BY_DELEGATION" for x in adrs), "ADR statuses")
for adr in adrs:
    p = ROOT / adr["source_path"]
    require(p.exists(), f"ADR missing: {p}")
    require(git_blob_sha(p.read_bytes()) == adr["reviewed_blob_sha"], f"ADR tampering: {adr['adr_id']}")
require(all(x["status"] == "ADOPTED_HARD_RELEASE_BLOCK_BY_DELEGATION" and x["block_policy"].startswith("HARD_") for x in deferrals), "release controls")
require(all(x["approval_state"] == "DELEGATED_DESIGN_ONLY_ACCEPTED_NO_HUMAN_PR_REVIEW" for x in gates), "gate approval semantics")
require(set(snap["gate_status"]) == {"G-00","G-01","G-02"}, "gate count")
require(all("DELEGATION" in status for status in snap["gate_status"].values()), "delegated design Gate state")
require(snap["delegated_decision"]["actor"] == "AI_ENGINEERING_CONSULTANT_NOT_HUMAN_REVIEWER", "decision authorship")
for key in ("signed_human_github_review","formal_reviewer_attestation","source_parent_bytes_recovered"):
    require(snap["delegated_decision"][key] is False, f"false external signoff: {key}")
for key in ("qualified_specialist_attestations","independent_privacy_legal_reviews","independent_visual_qa_reviews",
            "golden_runtime_executed_verified"):
    require(snap[key] == 0, f"fabricated professional/runtime proof: {key}")
require(snap["adopted_release_deferrals"] == 9, "must retain all 9 hard release constraints")
require("No production authorization" in (G/"DELEGATED_DESIGN_DECISION_2026-10-29.md").read_text(encoding="utf-8"), "missing no-live-release decision")

# Phase-01 release matrix exact cardinality and identity trace.
requirements = csv_file(P1 / "FEATURE_RELEASE_MATRIX.csv")
require(len(requirements) == 64, f"Phase-01 expected 64 requirements, found {len(requirements)}")
req_ids = {r["id"] for r in requirements}
require(len(req_ids) == 64, "duplicate requirement ID")
require({r["classification"] for r in requirements} == {"PRODUCT_MODULE","STUDIO_CAPABILITY","PRD_REQUIREMENT"}, "classification anomaly")
require(sum(r["id"].startswith("ABC-F") for r in requirements) == 18, "18 features")
require(sum(r["id"].startswith("AIS-") for r in requirements) == 26, "26 studio capabilities")
require(sum(r["id"].startswith("PRD-") for r in requirements) == 20, "20 PRDs")
require(all(r["accountable_owner"] == OWNER for r in requirements), "orphan project owner")
require(all(r["implementation_status"] == "SPECIFIED_NOT_IMPLEMENTED" for r in requirements), "fake runtime readiness")
packs = csv_file(P1 / "SERVICE_PACK_COVERAGE.csv")
require(len(packs) == 11 and len({r["family"] for r in packs}) == 11, "11 unique service packs")
require(all(r["release_state"] == "NOT_RELEASED" for r in packs), "unverified salon service released")
require(all(r["accountable_owner"] == OWNER for r in packs), "service owner missing")
require(all("SOP" in r["activation_policy"] or "qualified" in r["activation_policy"] for r in packs), "service release control not specified")
hair = [p for p in packs if "Hair color" in p["family"]]
require(len(hair) == 1 and "VISUAL_ONLY" in hair[0]["release_target"], "hair color must remain research/pilot visual only")

# Phase-02 machine-readable contracts and integration to P01 / ENG documents.
schemas = list((P2/"schemas").glob("*.schema.json"))
require(len(schemas) == 34, "Phase-02 schema inventory changed")
for p in schemas:
    schema = json_file(p)
    require(schema.get("$schema")=="https://json-schema.org/draft/2020-12/schema", f"invalid JSON Schema version {p}")
    require(schema.get("$id","").endswith("/"+p.name), f"schema ID mismatch {p.name}")
registry = json_file(P2/"engine-io-registry.json")
engines = registry["engines"]
engine_ids = {e["engine_id"] for e in engines}
require(len(engines)==19 and engine_ids=={f"ENG-{i:02d}" for i in range(1,20)}, "19 engine cardinality")
for e in engines:
    require(e["owner"] == OWNER and e["deployment_status"] == "DESIGN_ONLY", "engine owner/runtime truth")
    require((P2/"engines"/(e["engine_id"]+".contract.json")).exists(), "missing engine-specific interface")
    require((P2/e["input_schema"]).exists() and (P2/e["output_schema"]).exists(), "engine I/O ref missing")
events=json_file(P2/"events.json")
event_types={x["event_type"] for x in events["event_types"]}
require(len(event_types) == 25, "event contract coverage")
states=json_file(P2/"state-machines.json")["machines"]
require(len(states)==5, "5 guarded state machines")
consultation=next(x for x in states if x["id"]=="CONSULTATION_SESSION")
require(len(consultation["transitions"])==102, "session recovery transition count unexpected")
require(all(x["guards"] for m in states for x in m["transitions"]), "unguarded transition")
api=json_file(P2/"openapi.json")
ops={v["operationId"]:v for endpoints in api["paths"].values() for v in endpoints.values()}
require(len(api["paths"])==39 and len(ops)==41, "39 API paths, 41 operations")
require(all(v.get("x-abc-tenant-source") == "VERIFIED_AUTH_CONTEXT" for v in ops.values()), "tenant spoofing opportunity")
require(all(v.get("x-abc-roles") and v.get("x-abc-policy-guards") for v in ops.values()), "RBAC/policy guard not specified")
require(all("401" in v["responses"] and "403" in v["responses"] for v in ops.values()), "auth failure response missing")
for forbidden_op, forbidden_field in (("validateTechnicalPlan","qualification_id"),("proposeBusinessAction","requires_confirmation")):
    body=ops[forbidden_op]["requestBody"]["content"]["application/json"]["schema"]
    require(forbidden_field not in body.get("properties",{}), f"client could assert {forbidden_field}")
core_fixtures=json_file(P2/"examples/contract-fixtures.json")
event_fixtures=json_file(P2/"examples/event-payload-fixtures.json")
require((len(core_fixtures["valid"]),len(core_fixtures["invalid"]),len(event_fixtures["positive"]),len(event_fixtures["negative"]))==(33,39,25,77),
        "known synthetic coverage changed")
reqmap=csv_file(P2/"requirements-contract-map.csv")
require(len(reqmap)==64 and {x["requirement_id"] for x in reqmap}==req_ids, "requirements not exactly traceable")
require(all(x["accountable_owner"] == OWNER and x["implementation_proof_status"]=="NO_RUNTIME_IMPLEMENTATION" for x in reqmap), "crosswalk runtime/owner misstatement")
require({x["target_release"] for x in reqmap}<={"MVP","V2","V3","MVP_CONDITIONAL_VISUAL_ONLY"}, "unknown release")
for row in reqmap:
    for schema in row["schema_contracts"].split(";"):
        require((P2/"schemas"/(schema+".schema.json")).exists(), f"unknown schema in {row['requirement_id']}")
    for en in row["engine_ids"].split(";"):
        require(en in engine_ids, f"unknown engine in {row['requirement_id']}")
    for ev in row["event_types"].split(";"):
        require(ev=="NONE" or ev in event_types, f"unknown event in {row['requirement_id']}")
    for op in row["api_operations"].split(";"):
        require(op=="NONE" or op in ops, f"unknown API in {row['requirement_id']}")
deferred=[r for r in reqmap if r["status"]=="DEFERRED_RELEASE"]
require(len(deferred)==6 and all(r["target_release"]=="V2" for r in deferred), "6 deferred operational modules must remain V2")

# Original source evidence, no green runtime/service label from merged design docs.
for p in [ROOT/"docs/00-governance/phase-00/wp-000-03/GATE00_DECISION.md",
          P1/"GATE_01_DECISION.md", P2/"gate-02-decision.md"]:
    require(p.exists(), f"missing historic Gate document: {p}")
    content=p.read_text(encoding="utf-8")
    require("PENDING" in content or "BLOCKED" in content, "historic gate doc must remain immutable with original status")
require("G02_FORMAL_PASS_PENDING" in (P2/"gate-02-decision.md").read_text(), "G02 formal independent review still pending")

print("INTEGRATED_ABC_DESIGN_AUDIT_PASS: 70 ZIP source bytes preserved (10 explicitly archived original paths, 59 unchanged; active revisions intact), 3 delegated bounded source exceptions, 10 ADR blob matches, 9 hard release blockers, 64 P01 requirements, 11 NOT_RELEASED packs, 19 engines, 34 schemas, 41 API operations, 25 event types, 5 state machines, 174 synthetic fixtures. NO RUNTIME OR EXPERT/PRODUCTION CLAIM.")

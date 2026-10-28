#!/usr/bin/env python3
"""ABC Phase-02 Draft Contract Validator.

Validates real JSON Schema 2020-12 instances, positive/negative synthetic fixtures,
OpenAPI structural/tenant/mutation requirements, event and engine references, and
state machine safety. It does NOT execute engines or approve service releases.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts" / "v1"
SCHEMAS = CONTRACTS / "schemas"

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def must(value, error):
    if not value:
        raise AssertionError(error)

schema_files = sorted(SCHEMAS.glob("*.schema.json"))
must(len(schema_files) == 34, f"expected 34 schema files; got {len(schema_files)}")
schemas = {}
resources = []
for path in schema_files:
    data = load(path)
    Draft202012Validator.check_schema(data)
    must(data["$schema"] == "https://json-schema.org/draft/2020-12/schema", path.name)
    must(data["$id"] == f"https://schemas.abc.internal/v1/{path.name}", path.name)
    schemas[path.name.replace(".schema.json", "")] = data
    resources.append((data["$id"], Resource.from_contents(data)))
registry = Registry().with_resources(resources)
validator = {
    name: Draft202012Validator(s, registry=registry, format_checker=FormatChecker())
    for name, s in schemas.items()
}

def valid_instance(name: str, instance: dict):
    return list(validator[name].iter_errors(instance))

fixtures = load(CONTRACTS / "examples" / "contract-fixtures.json")
must(len(fixtures["valid"]) == 33, "33 synthetic positive fixtures expected")
must(len(fixtures["invalid"]) == 39, "39 synthetic negative fixtures expected")
for item in fixtures["valid"]:
    name, instance = item["schema"], item["instance"]
    must(name in validator and name != "common", f"invalid fixture schema {name}")
    errors = valid_instance(name, instance)
    must(not errors, f"VALID fixture rejected for {name}: {errors[0] if errors else ''}")
for item in fixtures["invalid"]:
    name, instance = item["schema"], item["instance"]
    errors = valid_instance(name, instance)
    must(bool(errors), f"INVALID fixture wrongly accepted for {name}: {item.get('reason')}")

engines = load(CONTRACTS / "engine-io-registry.json")["engines"]
engine_ids = {x["engine_id"] for x in engines}
expected_engine_ids = {f"ENG-{i:02d}" for i in range(1, 20)}
must(len(engines) == len(engine_ids) == 19 and engine_ids == expected_engine_ids, "engine registry incomplete or duplicated")
error_codes = {e["code"] for e in load(CONTRACTS / "error-catalog.json")["errors"]}
must(len(error_codes) == 20, "error catalog must have 20 unique codes")
for e in engines:
    must(e["owner"] == "saleheebrahimi2029-hub", e["engine_id"])
    must(e["deployment_status"] == "DESIGN_ONLY", e["engine_id"])
    for key in ("input_schema", "output_schema"):
        schema_path = CONTRACTS / e[key]
        must(schema_path.exists(), f"{e['engine_id']} missing {key}: {schema_path}")
    must(set(e["error_codes"]) <= error_codes, f"unknown error in {e['engine_id']}")
    must(e["preconditions"] and e["observability"], f"missing policy/telemetry {e['engine_id']}")
    desc_path = CONTRACTS / "engines" / f"{e['engine_id']}.contract.json"
    must(desc_path.exists(), f"missing per-engine contract {e['engine_id']}")
    desc = load(desc_path)
    must(desc["engine_id"] == e["engine_id"] and desc["owner"] == e["owner"], e["engine_id"])
    must(desc["release_state"] == "NOT_IMPLEMENTED", e["engine_id"])
    for key in ("typed_input_ref", "typed_output_ref"):
        must((desc_path.parent / desc[key]).resolve().exists(), f"invalid {key} for {e['engine_id']}")

events = load(CONTRACTS / "events.json")
evtypes = events["event_types"]
must(len(evtypes) == 25 and len({e["event_type"] for e in evtypes}) == 25, "event registry mismatch")
for ev in evtypes:
    must(ev["producer_engine_id"] in engine_ids, ev["event_type"])
    must((CONTRACTS / ev["payload_reference_schema"]).exists(), ev["event_type"])
    must(ev["required_payload_keys"], ev["event_type"])

for ev in evtypes:
    producer = next(e for e in engines if e["engine_id"] == ev["producer_engine_id"])
    must(ev["event_type"] in producer["emits"],
         f"producer {producer['engine_id']} does not declare event {ev['event_type']}")
valid_event_fixture = next(x["instance"] for x in fixtures["valid"] if x["schema"] == "event")
typed_evt = next(x for x in evtypes if x["event_type"] == valid_event_fixture["event_type"])
must(set(typed_evt["required_payload_keys"]) <= set(valid_event_fixture["payload"]),
     "event payload lacks registry required keys")

# Every registered event is now a discriminated typed envelope. Positive/negative
# fixtures must cover every event, including rejection of unknown payload fields.
event_fixtures = load(CONTRACTS / "examples" / "event-payload-fixtures.json")
must(len(event_fixtures["positive"]) == 25 and len(event_fixtures["negative"]) == 77,
     "full event fixture coverage expected")
registered_events = {ev["event_type"] for ev in evtypes}
must({x["event_type"] for x in event_fixtures["positive"]} == registered_events,
     "a registered event has no positive typed fixture")
for item in event_fixtures["positive"]:
    expected_producer = next(e["producer_engine_id"] for e in evtypes if e["event_type"] == item["event_type"])
    must(item["instance"]["producer_engine_id"] == expected_producer, "producer fixture mismatch")
    must(item["instance"].get("trace_id"), "event trace id missing")
    err = valid_instance("event", item["instance"])
    must(not err, f"valid event payload {item['event_type']} rejected: {err[0] if err else ''}")
for item in event_fixtures["negative"]:
    err = valid_instance("event", item["instance"])
    must(bool(err), f"invalid event payload accepted: {item['event_type']} {item['reason']}")
event_schema = schemas["event"]
must(len(event_schema.get("allOf", [])) == len(evtypes), "each event needs exactly one schema branch")
must("producer_engine_id" in event_schema["required"] and "trace_id" in event_schema["required"],
     "event producer and trace binding must be mandatory")
must(set(event_schema["properties"]["event_type"]["enum"]) == registered_events,
     "event type enum differs from registry")

must(events["delivery"] == "TRANSACTIONAL_OUTBOX_AT_LEAST_ONCE", "invalid message delivery claim")
must(events["deduplication"] == "consumer_id:event_id", "missing event dedupe")

machines = load(CONTRACTS / "state-machines.json")
must(len(machines["machines"]) == 5, "expected five machines")
for machine in machines["machines"]:
    st = set(machine["states"])
    must(machine["initial"] in st, machine["id"])
    seen = set()
    for t in machine["transitions"]:
        must(t["from"] in st and t["to"] in st, f"unknown transition node {machine['id']}: {t}")
        must(t["guards"] and t["actor"], f"unguarded transition {machine['id']}: {t}")
        edge=(t["from"],t["to"],t["actor"])
        must(edge not in seen, f"duplicate edge: {edge}")
        seen.add(edge)

# Actual reachability and recoverability, not merely valid state names.
for machine in machines["machines"]:
    states_reachable = {machine["initial"]}
    for _ in range(len(machine["states"]) + 1):
        before = len(states_reachable)
        for edge in machine["transitions"]:
            if edge["from"] in states_reachable:
                states_reachable.add(edge["to"])
        if len(states_reachable) == before:
            break
    must(states_reachable == set(machine["states"]),
         f"{machine['id']} has unreachable states: {set(machine['states']) - states_reachable}")
session_machine = next(m for m in machines["machines"] if m["id"] == "CONSULTATION_SESSION")
def session_edges(origin):
    return [t for t in session_machine["transitions"] if t["from"] == origin]
for origin in ("PAUSED", "FAILED_RECOVERABLE"):
    outgoing = session_edges(origin)
    must(outgoing and any(t["to"] not in ("CANCELLED", "CLOSED") for t in outgoing),
         f"{origin} cannot resume safely")
    for edge in outgoing:
        if edge["to"] != "CANCELLED":
            must("checkpoint_state_equals_target" in edge["guards"],
                 f"{origin} can jump to arbitrary saved state")
            must(any("policy" in guard for guard in edge["guards"]),
                 f"{origin} bypasses current policy")
for edge in session_edges("SAFETY_BLOCKED"):
    must(edge["to"] in ("INTENT_DEFINED", "CANCELLED"), "safety-block escape")
    if edge["to"] != "CANCELLED":
        must("qualified_specialist_review" in edge["guards"] and
             "non_bypassable_policy_recheck_passed" in edge["guards"],
             "safety-block bypass without qualified review")
must(any(t["to"] == "SAFETY_BLOCKED" for t in session_machine["transitions"]),
     "safety-blocked state is unreachable")

for machine_id, source, target in machines["forbidden_transitions"]:
    machine = next(m for m in machines["machines"] if m["id"] == machine_id)
    must(not any(t["from"] == source and t["to"] == target for t in machine["transitions"]),
         f"unsafe transition allowed: {machine_id} {source}->{target}")
plan = next(m for m in machines["machines"] if m["id"] == "TECHNICAL_PLAN")
for edge in plan["transitions"]:
    if edge["to"] in ("VALIDATED", "CONDITIONALLY_VALIDATED"):
        must(edge["actor"] == "SPECIALIST", "human approval bypass")
        must("authenticated_qualified_specialist" in edge["guards"], "qualification guard bypass")
visual = next(m for m in machines["machines"] if m["id"] == "VISUAL_JOB")
must(any(t["to"] == "QA_PASSED" and "visual_qa_report_passed" in t["guards"] for t in visual["transitions"]),
     "no visual QA release gate")

api = load(CONTRACTS / "openapi.json")
must(api["openapi"] == "3.1.0", "OpenAPI major not 3.1")
must(len(api["paths"]) == 39, f"expected 39 API paths, found {len(api['paths'])}")
operation_ids = []
for path, methods in api["paths"].items():
    must(path.startswith("/v1/"), path)
    for method, op in methods.items():
        must(method in ("get", "post"), f"unsupported method {method}")
        operation_ids.append(op["operationId"])
        must(op.get("security") == [{"bearerAuth": []}], f"missing auth {path}")
        must(op.get("x-abc-tenant-source") == "VERIFIED_AUTH_CONTEXT", f"untrusted tenant {path}")
        must(op.get("x-abc-roles"), f"missing RBAC {path}")
        must(op.get("x-abc-policy-guards"), f"missing mandatory policy guard {op['operationId']}")
        must("401" in op["responses"], f"missing authentication failure contract {op['operationId']}")
        must("403" in op["responses"], f"missing role/scope denial contract {op['operationId']}")
        params = op.get("parameters", [])
        for par in params:
            must(par.get("required"), f"optional critical API parameter {path}: {par}")
        if method == "post":
            must(any(p.get("name") == "Idempotency-Key" for p in params), f"missing idempotency {path}")
            body = op.get("requestBody", {})
            must(body.get("required") is True, f"missing body {path}")
            shape = body["content"]["application/json"]["schema"]
            must("tenant_id" not in shape.get("properties", {}), f"body accepts spoofed tenant {path}")
            if "{" in path and not path.endswith("}"):
                pass
            if op["operationId"] not in ("createConsultation","proposeBusinessAction","createClient","createAppointment"):
                must(any(p.get("name") == "X-Expected-State-Version" for p in params),
                    f"missing CAS version guard {path}")
        for response in op["responses"].values():
            schema = response.get("content", {}).get("application/json", {}).get("schema", {})
            refs = []
            def collect(node):
                if isinstance(node, dict):
                    if "$ref" in node: refs.append(node["$ref"])
                    for v in node.values(): collect(v)
                elif isinstance(node, list):
                    for v in node: collect(v)
            collect(schema)
            for ref in refs:
                if ref.startswith("./"):
                    must((CONTRACTS / ref[2:]).exists(), f"unresolved API response ref {ref}")
                else:
                    must(ref == "#/components/schemas/Error", f"unexpected API response ref {ref}")
must(len(operation_ids) == len(set(operation_ids)) == 41, "duplicate API operation IDs")
# No untrusted browser/API declaration can waive approval or claim specialist qualifications.
forbidden_body_fields = {
    "proposeBusinessAction": {"requires_confirmation"},
    "validateTechnicalPlan": {"qualification_id", "specialist_qualification_id"}
}
for path, methods in api["paths"].items():
    for method, op in methods.items():
        if op["operationId"] in forbidden_body_fields:
            body = op["requestBody"]["content"]["application/json"]["schema"]
            for field in forbidden_body_fields[op["operationId"]]:
                must(field not in body.get("properties", {}) and field not in body.get("required", []),
                     f"untrusted client can assert {field} for {op['operationId']}")
consent_api = api["paths"]["/v1/consultations/{session_id}/consents"]["post"]
consent_shape = consent_api["requestBody"]["content"]["application/json"]["schema"]
must("consent_evidence_ref" in consent_shape["required"], "no evidence for recording consent")

must(api["servers"][0]["url"].endswith(".invalid"), "no real deployment URL intended")

outputs = load(CONTRACTS / "output-contract-registry.json")
must([x["output_id"] for x in outputs["legacy_outputs"]] == [f"OUT-{i:02d}" for i in range(1,18)],
     "historical OUT IDs not preserved")
must(len(outputs["productization_new_outputs"]) == 2, "missing new technical outputs")
for x in outputs["legacy_outputs"]:
    must((CONTRACTS / x["typed_payload_ref"]).exists(), x["output_id"])

source = ROOT / "docs/01-product/phase-01/FEATURE_RELEASE_MATRIX.csv"
must(source.exists(), "stacked Phase-01 product baseline missing")
import csv
with source.open(encoding="utf-8", newline="") as f:
    rows=list(csv.DictReader(f))
must(len(rows) == 64, "Phase-01 64 feature traceability rows required")
must(all(x["accountable_owner"] == "saleheebrahimi2029-hub" for x in rows), "single-owner mismatch")


coverage_path=CONTRACTS / "requirements-contract-map.csv"
with coverage_path.open(encoding="utf-8", newline="") as f:
    coverage=list(csv.DictReader(f))
must(len(coverage) == 64 and len({r["requirement_id"] for r in coverage}) == 64,
     "Phase-02 requires 64 mapped product requirements")
must({r["requirement_id"] for r in coverage} == {r["id"] for r in rows},
     "Crosswalk does not match all Phase-01 IDs")
must({r["status"] for r in coverage} <= {"MAPPED_API", "MAPPED_INTERNAL", "DEFERRED_RELEASE"},
     "Invalid contract coverage state")
must(sum(x["status"] == "DEFERRED_RELEASE" for x in coverage)==6,
     "Deferred Salon OS contracts must be explicitly identified")
for row in coverage:
    must(row["accountable_owner"] == "saleheebrahimi2029-hub",row["requirement_id"])
    must(row["implementation_proof_status"] == "NO_RUNTIME_IMPLEMENTATION",row["requirement_id"])
    for name in row["schema_contracts"].split(";"):
        must(name in schemas, f"unknown schema {name} for {row['requirement_id']}")
    for eid in row["engine_ids"].split(";"):
        must(eid in engine_ids, f"unknown engine {eid} for {row['requirement_id']}")
    for event_type in row["event_types"].split(";"):
        if event_type != "NONE":
            must(event_type in {e["event_type"] for e in evtypes},
                 f"unknown event {event_type} for {row['requirement_id']}")
    for op_name in row["api_operations"].split(";"):
        if op_name != "NONE":
            must(op_name in operation_ids,
                 f"unknown API operation {op_name} for {row['requirement_id']}")
    if row["status"] == "MAPPED_API":
        must(row["api_operations"] != "NONE",row["requirement_id"])
    if row["status"] == "MAPPED_INTERNAL":
        must(row["schema_contracts"] and row["engine_ids"],row["requirement_id"])
gate = (CONTRACTS / "gate-02-decision.md").read_text(encoding="utf-8")
must("G02_FORMAL_PASS_PENDING" in gate, "contract gate must remain pending")
print("PHASE-02 CONTRACT TESTS PASS (draft docs): 34 schemas, 33 valid + 39 invalid fixtures plus 25 positive / 77 negative event payload fixtures, 19 engines, 25 events, 5 state machines, 39 API paths / 41 operations, 64 requirement crosswalks, 17 historic outputs, 64 upstream requirements. NO RUNNING ENGINES/FORMAL GATE PASS CLAIMED.")

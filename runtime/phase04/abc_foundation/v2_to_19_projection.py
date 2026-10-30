"""Explicit v2 -> canonical-19 projections. NO runtime migration or dispatch.

Every input must pass the unchanged v2 request/response pair validator.
The output is a scoped, hashed, non-authoritative *review candidate* only.
Review-time v2 logical role labels remain source labels, never new owners.
"""
import hashlib
import json
import os
from pathlib import Path

from jsonschema import Draft202012Validator,FormatChecker

from .engine_v2_contracts import validate_port
from .store import DomainError

_ROOT=Path(__file__).resolve().parents[3]
_REGISTRY=_ROOT/"governance/abc_v2_to_19_adapters.v0.review.json"
_SCHEMA=_ROOT/"contracts/review/v2_to_19_adapter_projection.v0.schema.json"
_PROTOCOL="abc.bridge.v2-to-19.v0.review"


def _digest(value):
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),
                   ensure_ascii=True,allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _validate_pair(req,resp,expected):
    if os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
        raise DomainError(403,"adapter_not_authorized_for_hosted_execution")
    if not isinstance(req,dict) or not isinstance(resp,dict):
        raise DomainError(422,"adapter_source_not_a_v2_envelope")
    validate_port(req,engine=expected)
    validate_port(resp,engine=expected,response=True,request=req)
    r=resp["result"]
    if (expected=="ENG-04" and r["status"]=="BLOCKED"
        and r["candidate_looks"]):
        raise DomainError(403,"blocked_source_cannot_emit_looks")
    if (expected=="ENG-05" and r["status"]=="BLOCKED"
        and r["eligible_looks"]):
        raise DomainError(403,"blocked_source_cannot_emit_eligibility")
    if (expected=="ENG-06" and
        ((r["status"]=="DRAFT_REQUIRES_SPECIALIST_REVIEW") !=
         (r["draft_plan"] is not None))):
        raise DomainError(403,"technical_plan_status_payload_mismatch")
    return r


def _emit(req,resp,adapter_id,payload):
    registry=json.loads(_REGISTRY.read_text())
    entries={e["adapter_id"]:e for e in registry["adapters"]}
    a=entries.get(adapter_id)
    if (registry["decision_status"]!="CODE_REVIEW_ONLY"
        or registry["owner_signoff"] is not False
        or registry["live_dispatch_enabled"] is not False
        or registry["customer_release_approved"] is not False
        or a is None or a["migration_status"]!="UNMIGRATED"
        or a["runtime_enabled"] is not False):
        raise DomainError(403,"adapter_registry_not_approved")
    if a["source_engine"]!=req["engine_id"]:
        raise DomainError(403,"adapter_source_identity_mismatch")
    output={
        "adapter_id":adapter_id,"protocol":_PROTOCOL,
        "source_protocol":req["contract_version"],
        "source_engine":a["source_engine"],
        "target_engine":a["target_engine"],
        "tenant_id":req["tenant_id"],"branch_id":req["branch_id"],
        "session_id":req["session_id"],"state_version":req["state_version"],
        "correlation_id":req["correlation_id"],
        "service_kind":req["payload"]["service_kind"],
        "source_request_sha256":_digest(req),
        "source_response_sha256":_digest(resp),
        "projection_sha256":_digest(payload),
        "projection":payload,
        "status":"REVIEW_ONLY_UNWIRED",
        "provenance_authority_verified":False,
        "downstream_dispatch_authorized":False,
        "professional_validation_complete":False,
        "customer_release_approved":False
    }
    schema=json.loads(_SCHEMA.read_text())
    if not Draft202012Validator(schema,format_checker=FormatChecker()).is_valid(output):
        raise DomainError(422,"adapter_projection_schema_rejected")
    return output


def project_v2_response(req,resp,*,adapter_id):
    allowed={
        "A04_TO_06_DECISION_INPUT":"ENG-04",
        "A04_TO_07_LOOK_SPEC_INPUT":"ENG-04",
        "A05_TO_06_DECISION_EVIDENCE":"ENG-05",
        "A06_TO_15_PLAN_CANDIDATE":"ENG-06"
    }
    source=allowed.get(adapter_id)
    if source is None:
        raise DomainError(403,"unrecognized_v2_adapter")
    r=_validate_pair(req,resp,source)
    if source=="ENG-04":
        looks=r["candidate_looks"]
        if adapter_id=="A04_TO_06_DECISION_INPUT":
            data={"source_status":r["status"],
                  "candidate_looks":[{"look_id":x["look_id"],
                      "spec_digest":x["spec_digest"],
                      "evidence_ids":list(x["evidence_ids"])} for x in looks],
                  "uncertainty":list(r["uncertainty"]),
                  "visual_qa_status":r["visual_qa_status"],
                  "independent_decision_verified":False}
        else:
            data={"source_status":r["status"],
                  "draft_looks":[{"look_id":x["look_id"],
                     "spec_digest":x["spec_digest"],
                     "evidence_ids":list(x["evidence_ids"]),
                     "edit_regions":list(x["edit_regions"]),
                     "feasibility":x["feasibility"]} for x in looks],
                  "look_lock_verified":False,"rendered_visual_exists":False}
    elif source=="ENG-05":
        data={"source_status":r["status"],
              "eligible_look_ids":[x["look_id"] for x in r["eligible_looks"]],
              "excluded_look_ids":[x["look_id"] for x in r["excluded_looks"]],
              "critical_unknowns":list(r["critical_unknowns"]),
              "knowledge_source_digests":[x["digest"] for x in
                                         req["payload"]["knowledge_sources"]],
              "signed_policy_verified":False,
              "specialist_selection_authorized":False}
    else:
        plan=r["draft_plan"]
        data={"source_status":r["status"],
              "selected_look_id":req["payload"]["selected_look_lock"]["look_id"],
              "plan_template_sha256":_digest(plan) if plan is not None else None,
              "missing_requirements":list(r["missing_requirements"]),
              "sop_and_consent_independently_verified":False,
              "specialist_validation_verified":False,
              "technical_procedure_authorized":False}
    return _emit(req,resp,adapter_id,data)

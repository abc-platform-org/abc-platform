"""Strict v2 draft contract admission; never dispatches synthetic v1 engines.

This module validates boundary schemas only. No model calls, storage writes,
customer release, professional authorization or legacy protocol promotion.
"""
import json
import re
import uuid
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from .store import DomainError

VERSION="abc.internal.engine.v2.draft"
ROOT=Path(__file__).with_name("engine_v2")
FILES={
 "ENG-04":"eng04.recommendation.v2.json",
 "ENG-05":"eng05.decision.v2.json",
 "ENG-06":"eng06.technical-plan.v2.json"
}
_UUID={"type":"string","format":"uuid"}
_NAME={"type":"string","minLength":3,"maxLength":96,"pattern":"^[A-Za-z0-9_-]+$"}
_HEX={"type":"string","pattern":"^[0-9a-f]{64}$"}
_FIELDS=("request_id","engine_id","contract_version","consumer_id",
         "tenant_id","branch_id","session_id","state_version",
         "correlation_id","payload")
_RESULT=("request_id","engine_id","contract_version","consumer_id",
         "tenant_id","branch_id","session_id","state_version",
         "correlation_id","result","release_approved","execution_authorized")
_KINDS=frozenset(("HAIRCUT","HAIR_COLOR","BEARD","MAKEUP","NAILS",
 "SKIN","EXTENSIONS","KERATIN","CORRECTIVE"))
_DEFAULT={"format_checker":FormatChecker()}


def _canonical_uuid(value):
    try:
        return str(uuid.UUID(value))==value
    except (TypeError,ValueError,AttributeError):
        return False


def _port(engine):
    if engine not in FILES:
        raise DomainError(400,"unknown_v2_engine")
    cfg=json.loads((ROOT/FILES[engine]).read_text())
    if (cfg.get("engine_id")!=engine or
        cfg.get("status")!="CONTRACT_DRAFT_NO_RUNTIME_RELEASE" or
        cfg.get("contract_id")!={
         "ENG-04":"abc.internal.eng04.recommendation.v2.draft",
         "ENG-05":"abc.internal.eng05.decision.v2.draft",
         "ENG-06":"abc.internal.eng06.technical-plan.v2.draft"}[engine]):
        raise ValueError("port_registry_contract_drift")
    for name in ("request_payload_schema","response_result_schema"):
        Draft202012Validator.check_schema(cfg[name])
    return cfg


def envelope_schema(engine,*,response=False):
    port=_port(engine)
    data_key="result" if response else "payload"
    props={"request_id":_UUID,"engine_id":{"const":engine},
       "contract_version":{"const":VERSION},"consumer_id":_NAME,
       "tenant_id":_NAME,"branch_id":_NAME,"session_id":_UUID,
       "state_version":{"type":"integer","minimum":0},
       "correlation_id":_UUID,
       data_key:port["response_result_schema" if response else "request_payload_schema"]}
    if response:
        props.update({"release_approved":{"const":False},
                      "execution_authorized":{"const":False}})
    return {"$schema":"https://json-schema.org/draft/2020-12/schema",
       "type":"object","additionalProperties":False,
       "required":list(_RESULT if response else _FIELDS),"properties":props}


def validate_port(message,*,engine,response=False,request=None):
    """Check strict schema, canonical scope, frozen v2 identity and provenance."""
    if not isinstance(message,dict) or engine not in FILES:
        raise DomainError(400,"invalid_v2_engine_message")
    spec=envelope_schema(engine,response=response)
    if not Draft202012Validator(spec,**_DEFAULT).is_valid(message):
        raise DomainError(422,"v2_engine_schema_rejected")
    if not all(_canonical_uuid(message[f]) for f in ("request_id","session_id","correlation_id")):
        raise DomainError(422,"v2_noncanonical_uuid")
    if type(message["state_version"]) is not int:
        raise DomainError(422,"v2_invalid_state_version")
    payload=message["result"] if response else message["payload"]
    if not response:
        if payload["service_kind"] not in _KINDS:
            raise DomainError(422,"unapproved_service_kind")
        if engine=="ENG-04":
            if (payload["current_media_ref"] in payload["reference_media_refs"]
                or len(set(x["evidence_id"] for x in payload["evidence"]))!=len(payload["evidence"])):
                raise DomainError(422,"v2_reference_or_evidence_not_isolated")
        if engine=="ENG-05":
            ref=payload["recommendation_ref"]
            if any(ref[f]!=message[f] for f in ("session_id","tenant_id","branch_id")):
                raise DomainError(403,"v2_cross_scope_recommendation_denied")
            if len({x["look_id"] for x in payload["candidate_looks"]})!=len(payload["candidate_looks"]):
                raise DomainError(422,"v2_duplicate_look")
        if engine=="ENG-06":
            verified=(payload["consent_status"]=="VERIFIED_BY_ENG14")
            proof=payload["consent_proof_digest"]
            if verified != (isinstance(proof,str) and bool(re.fullmatch(r"[0-9a-f]{64}",proof))):
                raise DomainError(422,"v2_consent_status_and_proof_disagree")
            for key in ("selected_look_lock","decision_ref"):
                ref=payload[key]
                for f in ("session_id","tenant_id","branch_id","state_version"):
                    if ref[f]!=message[f]:
                        raise DomainError(403,"v2_cross_scope_or_stale_look_denied")
        return {"valid":True,"dispatch_authorized":False,"release_approved":False}
    if not isinstance(request,dict):
        raise DomainError(403,"v2_unbound_engine_response")
    validate_port(request,engine=engine)
    if any(message[f]!=request[f] for f in _FIELDS if f!="payload"):
        raise DomainError(403,"v2_response_scope_or_correlation_mismatch")
    if engine=="ENG-04":
        permitted={x["evidence_id"] for x in request["payload"]["evidence"]}
        regions=set(request["payload"]["edit_regions"])
        for look in payload["candidate_looks"]:
            if not set(look["evidence_ids"])<=permitted or not set(look["edit_regions"])<=regions:
                raise DomainError(403,"v2_recommendation_provenance_or_region_violation")
    if engine=="ENG-05":
        inputs={x["look_id"] for x in request["payload"]["candidate_looks"]}
        output=[x["look_id"] for key in ("eligible_looks","excluded_looks") for x in payload[key]]
        if len(output)!=len(set(output)) or not set(output)<=inputs:
            raise DomainError(403,"v2_decision_candidate_fabrication")
        unreviewed=not request["payload"]["knowledge_sources"] or any(
            source["review_status"]!="SPECIALIST_REVIEWED"
            for source in request["payload"]["knowledge_sources"])
        if (request["payload"]["critical_unknowns"] or unreviewed or
            request["payload"]["policy_gate"]["decision"]=="BLOCK"):
            if payload["eligible_looks"] or payload["status"]!="BLOCKED":
                raise DomainError(403,"v2_unsafe_eligibility")
    if engine=="ENG-06":
        source=request["payload"]
        missing=(source["consent_status"]!="VERIFIED_BY_ENG14"
            or source["approved_sop_ref"] is None
            or not source["professional_findings"]
            or any(item["review_status"]!="SPECIALIST_RECORDED"
                for item in source["professional_findings"]))
        if missing and (payload["draft_plan"] is not None
            or payload["status"]=="DRAFT_REQUIRES_SPECIALIST_REVIEW"):
            raise DomainError(403,"v2_technical_plan_requires_verified_preconditions")
        if payload["status"]=="DRAFT_REQUIRES_SPECIALIST_REVIEW" and payload["draft_plan"] is None:
            raise DomainError(422,"v2_plan_draft_payload_missing")
    return {"valid":True,"dispatch_authorized":False,"release_approved":False}


def error_envelope_schema(engine):
    """Strict v2 error port: no free-text exception, client media or secret echo."""
    port=_port(engine)
    props={key:envelope_schema(engine)["properties"][key]
           for key in _FIELDS if key!="payload"}
    props.update({"error":{"type":"object","additionalProperties":False,
        "required":["code","retryable"],"properties":{
            "code":{"enum":port["errors"]},"retryable":{"const":False}}},
        "release_approved":{"const":False},
        "execution_authorized":{"const":False}})
    return {"$schema":"https://json-schema.org/draft/2020-12/schema",
        "type":"object","additionalProperties":False,
        "required":[x for x in _FIELDS if x!="payload"]+
                   ["error","release_approved","execution_authorized"],
        "properties":props}


def validate_error(message,*,engine,request):
    validate_port(request,engine=engine)
    if not Draft202012Validator(error_envelope_schema(engine),**_DEFAULT).is_valid(message):
        raise DomainError(422,"v2_error_envelope_invalid")
    if any(message[f]!=request[f] for f in _FIELDS if f!="payload"):
        raise DomainError(403,"v2_error_scope_or_correlation_mismatch")
    return True

def stub_response(message,*,engine):
    """Return an exact typed NOT_IMPLEMENTED error. Never call any engine."""
    validate_port(message,engine=engine)
    response={key:message[key] for key in _FIELDS if key!="payload"}
    response.update({"error":{"code":"NOT_IMPLEMENTED","retryable":False},
                     "release_approved":False,"execution_authorized":False})
    validate_error(response,engine=engine,request=message)
    return response

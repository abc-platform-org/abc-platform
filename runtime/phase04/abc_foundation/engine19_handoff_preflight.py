"""Strict prospective handoff preflight for 19-engine architecture.

Local-only static contract checker. Never dispatches an engine call; a verified
certificate/JWT, purpose consent, ENG14 decision, state CAS and signed human
acceptance belong to independent runtime authorities not available here.
"""
import json
import os
import uuid
from pathlib import Path
from jsonschema import Draft202012Validator,FormatChecker
from .store import DomainError

_ROOT=Path(__file__).resolve().parents[3]
_SCHEMA=_ROOT/"contracts/review/engine19_handoff.v0.schema.json"
_GRAPH=_ROOT/"governance/abc_workflow_19.v0.review.json"


def preflight_candidate_handoff(message):
    if os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
        raise DomainError(403,"canonical19_runtime_not_approved")
    if not isinstance(message,dict):
        raise DomainError(422,"invalid_canonical19_handoff")
    schema=json.loads(_SCHEMA.read_text())
    if not Draft202012Validator(schema,format_checker=FormatChecker()).is_valid(message):
        raise DomainError(422,"canonical19_contract_schema_rejected")
    for key in ("handoff_id","session_id","correlation_id"):
        try:
            value=message[key]
            if str(uuid.UUID(value))!=value:
                raise ValueError()
        except (TypeError,ValueError,AttributeError):
            raise DomainError(422,"canonical19_noncanonical_correlation") from None
    if type(message["state_version"]) is not int:
        raise DomainError(422,"canonical19_state_version_not_integer")
    graph=json.loads(_GRAPH.read_text())
    allowed={
        (edge["from"],edge["to"]):edge for edge in graph["handoffs"]
    }
    edge=allowed.get((message["from_engine"],message["to_engine"]))
    if edge is None or message["artifact_kind"]!=edge["artifact"]:
        raise DomainError(403,"canonical19_wrong_producer_or_artifact")
    gates=[
        g for g in graph["required_policy_gates"]
        if g["before_engine"]==message["to_engine"]
    ]
    if gates and not message["policy_proof_ref"]:
        raise DomainError(403,"canonical19_policy_proof_reference_required")
    # A user-provided reference is NOT a signed authorization. No external
    # evidence authority or live engine is invoked in this preflight.
    return {
        "status":"CONTRACT_PREFLIGHT_ONLY",
        "from_engine":message["from_engine"],
        "to_engine":message["to_engine"],
        "required_policy_gates":[g["gate_id"] for g in gates],
        "external_signature_verification_required":True,
        "revocation_and_consent_verification_required":True,
        "runtime_dispatch_authorized":False,
        "professional_plan_authorized":False,
        "customer_release_approved":False,
    }

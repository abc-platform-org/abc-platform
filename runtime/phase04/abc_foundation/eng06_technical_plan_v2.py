"""ENG-06 v2 technical-plan drafter: safe, nonprocedural controlled templates.

No chemical mixture, strength, application timing or executable treatment
sequence is provided. Only an injected verified evidence gate may open a
synthetic draft. No gate means mandatory fail-closed waiting, not self-approval.
"""
import hashlib
import json

_MISSING=(
    "SELECTED_LOOK_PROFESSIONAL_VERIFICATION_REQUIRED",
    "SOURCE_EVIDENCE_AND_SOP_VERIFICATION_REQUIRED",
)
_TEMPLATE={
    "target_definition":"Selected look must be confirmed against the approved visual specification.",
    "baseline_assessment":"Specialist must document condition, history, uncertainties, and contraindications.",
    "procedure_strategy":"No procedure is authorized. A qualified specialist must select an approved service-specific SOP.",
    "step_sequence":["Confirm consent and service scope with the specialist.",
                     "Review the independently approved SOP and current condition.",
                     "Request professional validation before any treatment."],
    "tools_materials":[],
    "quality_checkpoints":["Identity and region match must be independently reviewed.",
                           "Escalate uncertainty to qualified specialist."],
    "stop_conditions":["Stop if evidence, consent, SOP, or specialist authorization is absent.",
                       "Stop and escalate any contraindication or adverse observation."],
    "time_resources":"NOT_EVALUATED; no procedural timing provided.",
    "aftercare":"Specialist to provide SOP-specific aftercare only after separate validation."
}


def _gate_accepted(gate, request):
    if gate is None or not callable(getattr(gate,"verify",None)):
        return False
    # The production gate must authenticate a separate ENG14/02/05 principal,
    # corroborate the evidence ledger, lock signature, revocation and SOP
    # issuer. This interface intentionally has NO in-repo trust root.
    try:
        return gate.verify(
            engine_id="ENG-06",tenant_id=request["tenant_id"],
            branch_id=request["branch_id"],session_id=request["session_id"],
            state_version=request["state_version"],
            selected_look_lock=request["payload"]["selected_look_lock"],
            decision_ref=request["payload"]["decision_ref"],
            consent_proof_digest=request["payload"]["consent_proof_digest"],
            approved_sop_ref=request["payload"]["approved_sop_ref"]) is True
    except (ValueError,TypeError,KeyError,RuntimeError):
        return False


def plan(message,*,evidence_gate=None):
    payload=message["payload"]
    missing=[]
    if payload["consent_status"]!="VERIFIED_BY_ENG14" or not payload["consent_proof_digest"]:
        missing.append("CONSENT_VERIFICATION_REQUIRED")
    if payload["approved_sop_ref"] is None:
        missing.append("APPROVED_SOP_MISSING")
    if not payload["professional_findings"] or any(
        f["review_status"]!="SPECIALIST_RECORDED" for f in payload["professional_findings"]):
        missing.append("SPECIALIST_FINDINGS_NOT_VERIFIED")
    if not payload["current_state_evidence_ids"]:
        missing.append("CURRENT_STATE_EVIDENCE_MISSING")
    if not _gate_accepted(evidence_gate,message):
        missing.append("EXTERNAL_EVIDENCE_GATE_UNAVAILABLE_OR_DENIED")
    if missing:
        return {"status":"AWAITING_SPECIALIST_INPUT",
                "draft_plan":None,"missing_requirements":missing,
                "professional_validation":"NOT_VERIFIED",
                "operational_handoff_authorized":False,
                "execution_authorized":False}
    # This is a non-operational template even with a synthetic *test* gate.
    # No inference model, professional judgement, chemical specifications,
    # procedure authorization, or irreversible action.
    return {"status":"DRAFT_REQUIRES_SPECIALIST_REVIEW",
            "draft_plan":dict(_TEMPLATE),
            "missing_requirements":[],
            "professional_validation":"NOT_VERIFIED",
            "operational_handoff_authorized":False,
            "execution_authorized":False}

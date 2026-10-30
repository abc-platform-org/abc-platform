"""ENG-05 v2: deterministic, explainable denial and *review* classification.

A proposed look is not a verified feasible service. Caller-provided source
review_status is explicitly NOT a cryptographic specialist attestation.
All outputs prohibit specialist selection and real-world execution.
"""

def _external_gate_accepted(gate,message):
    if gate is None or not callable(getattr(gate,"verify",None)):
        return False
    try:
        payload=message["payload"]
        return gate.verify(engine_id="ENG-05",
            tenant_id=message["tenant_id"],branch_id=message["branch_id"],
            session_id=message["session_id"],
            state_version=message["state_version"],
            recommendation_ref=payload["recommendation_ref"],
            candidate_looks=payload["candidate_looks"],
            knowledge_sources=payload["knowledge_sources"],
            policy_gate=payload["policy_gate"]) is True
    except (TypeError,ValueError,KeyError,RuntimeError):
        return False


def decide(message,*,knowledge_policy_gate=None):
    payload=message["payload"]
    reasons=[]
    if payload["policy_gate"]["decision"]=="BLOCK":
        reasons.append("ENG14_POLICY_BLOCK")
    if payload["critical_unknowns"]:
        reasons.append("CRITICAL_EVIDENCE_MISSING")
    sources=payload["knowledge_sources"]
    if not sources or any(s["review_status"]!="SPECIALIST_REVIEWED"
                          for s in sources):
        reasons.append("UNREVIEWED_KNOWLEDGE")
    if not _external_gate_accepted(knowledge_policy_gate,message):
        reasons.append("EXTERNAL_KNOWLEDGE_POLICY_VERIFICATION_REQUIRED")
    candidates=payload["candidate_looks"]
    if not candidates:
        reasons.append("NO_CANDIDATE_LOOKS")
    blocked=bool(reasons)
    excluded=[{"look_id":item["look_id"],
               "reason":reasons[0] if blocked else "UNSPECIFIED"}
              for item in candidates] if blocked else []
    # Even on controlled, fully populated input, candidate eligibility is
    # ONLY eligibility for human review, not evidence of salon feasibility.
    reviewable=[] if blocked else [{
        "look_id":item["look_id"],
        "reason":"SYNTHETIC_ONLY_SPECIALIST_REVIEW_REQUIRED",
        "evidence_ids":sorted(item["evidence_ids"])
    } for item in candidates]
    return {
        "status":"BLOCKED" if blocked else "SPECIALIST_REVIEW_REQUIRED",
        "eligible_looks":reviewable,
        "excluded_looks":excluded,
        "critical_unknowns":sorted(set(payload["critical_unknowns"])),
        "specialist_selection_authorized":False,
        "execution_authorized":False
    }

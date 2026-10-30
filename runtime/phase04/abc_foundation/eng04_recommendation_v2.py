"""ENG-04 v2 controlled recommendations, NEVER computer vision or salon advice.

Only explicit synthetic look templates can be proposed. No media is decoded,
no model is called and every output retains source IDs and immutable region locks.
"""
import hashlib
import json
import uuid

_ALLOWED_INTENTS={
    "cooler brown style preview":"cool-brown",
    "warm copper style preview":"warm-copper",
    "natural dark style preview":"natural-dark",
}
_UNCERTAIN=("VISUAL_IDENTITY_NOT_ASSESSED","REAL_FEASIBILITY_NOT_ASSESSED")


def recommend(message):
    payload=message["payload"]
    findings=list(_UNCERTAIN)
    candidate=[]
    valid_profile=(payload["service_kind"]=="HAIR_COLOR"
        and payload["edit_regions"]==["HAIR"])
    has_unknown=any(e["evidence_class"]=="UNKNOWN" for e in payload["evidence"])
    intent=payload["target_intent"].strip().casefold()
    preset=_ALLOWED_INTENTS.get(intent)
    if not valid_profile:
        findings.append("SERVICE_OR_EDIT_REGION_NOT_IN_CONTROLLED_FIXTURE")
    if has_unknown:
        findings.append("EVIDENCE_UNKNOWN")
    if not preset:
        findings.append("UNSUPPORTED_TARGET_INTENT")
    if valid_profile and not has_unknown and preset:
        # A predictable ID is not a rendered look. Hash the entire scoped
        # request, including immutable image/reference handles and evidence.
        source={"tenant_id":message["tenant_id"],
            "branch_id":message["branch_id"],
            "session_id":message["session_id"],
            "state_version":message["state_version"],
            "service_kind":payload["service_kind"],
            "intent_fixture":preset,
            "media_ref":payload["current_media_ref"],
            "reference_media_refs":sorted(payload["reference_media_refs"]),
            "edit_regions":payload["edit_regions"],
            "evidence":sorted(payload["evidence"],key=lambda x:x["evidence_id"])}
        serialized=json.dumps(source,sort_keys=True,separators=(",",":"),
                              ensure_ascii=True,allow_nan=False)
        fingerprint=hashlib.sha256(serialized.encode()).hexdigest()
        candidate=[{
            "look_id":str(uuid.uuid5(uuid.NAMESPACE_URL,
                       "abc/eng04/controlled-v2/"+fingerprint)),
            "spec_digest":fingerprint,
            "evidence_ids":sorted(e["evidence_id"] for e in payload["evidence"]),
            "edit_regions":["HAIR"],"feasibility":"NOT_VERIFIED"
        }]
        findings.append("SYNTHETIC_STYLE_SPEC_ONLY")
    return {
        "status":"DRAFT_FOR_SPECIALIST_REVIEW" if candidate else "BLOCKED",
        "candidate_looks":candidate,
        "uncertainty":findings,
        "visual_qa_status":"NOT_VERIFIED",
        "professional_approval_verified":False
    }

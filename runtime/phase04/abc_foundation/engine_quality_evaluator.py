"""Completion decisions require signed independent review evidence.

An engine completion decision is separate from product release.
"""
import hashlib
import json

GATES=("G01_ARCHITECTURE","G02_DOMAIN_CAPABILITY","G03_CONTRACTS",
"G04_INDEPENDENCE","G05_SECURITY_PRIVACY","G06_RELIABILITY",
"G07_PERFORMANCE","G08_PROFESSIONAL_VALIDATION",
"G09_OBSERVABILITY_OPERATIONS","G10_INDEPENDENT_SIGNOFF")


def evaluate(engine,evidence=None,reviewer=None):
    result={"engine_id":engine["id"],"status":"IN_PROGRESS",
            "complete":False,"product_release_approved":False}
    if engine.get("critical_blockers") or reviewer is None:
        return result
    if not isinstance(evidence,dict) or set(evidence)!=set(GATES):
        return result
    if any(not isinstance(evidence[k],dict) or
           evidence[k].get("decision")!="PASS" for k in GATES):
        return result
    payload=json.dumps(evidence,sort_keys=True,
                       separators=(",",":"),allow_nan=False).encode()
    manifest_digest=hashlib.sha256(payload).hexdigest()
    # External reviewer must verify signed claims, issuer trust, scope,
    # independent professional and security identities and exact artifacts.
    outcome=reviewer.verify(engine_id=engine["id"],
        manifest_sha256=manifest_digest,gate_ids=GATES)
    if outcome is not True:
        return result
    return {"engine_id":engine["id"],"status":"COMPLETE","complete":True,
            "evidence_sha256":manifest_digest,
            "product_release_approved":False}

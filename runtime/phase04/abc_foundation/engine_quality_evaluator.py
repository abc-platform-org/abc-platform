"""Completion decisions require signed independent review evidence.

An engine completion decision is separate from product release.
"""
import hashlib
import json
import re
from .engine_quality_signatures import SignedEngineReviewer

GATES=("G01_ARCHITECTURE","G02_DOMAIN_CAPABILITY","G03_CONTRACTS",
"G04_INDEPENDENCE","G05_SECURITY_PRIVACY","G06_RELIABILITY",
"G07_PERFORMANCE","G08_PROFESSIONAL_VALIDATION",
"G09_OBSERVABILITY_OPERATIONS","G10_INDEPENDENT_SIGNOFF")


def digest_manifest(evidence):
    return hashlib.sha256(json.dumps(evidence,sort_keys=True,
               separators=(",",":"),allow_nan=False).encode()).hexdigest()


def evaluate(engine,evidence=None,reviewer=None,commit_sha=None):
    result={"engine_id":engine["id"],"status":"IN_PROGRESS",
            "complete":False,"product_release_approved":False}
    if (engine.get("critical_blockers") or
        not isinstance(reviewer,SignedEngineReviewer) or
        not isinstance(commit_sha,str) or
        not re.fullmatch(r"[0-9a-f]{40}",commit_sha)):
        return result
    if not isinstance(evidence,dict) or set(evidence)!=set(GATES):
        return result
    if any(not isinstance(evidence[k],dict) or
           evidence[k].get("decision")!="PASS" or
           not isinstance(evidence[k].get("evidence_ref"),str) or
           not evidence[k]["evidence_ref"].startswith("https://") or
           not isinstance(evidence[k].get("artifact_sha256"),str) or
           not re.fullmatch(r"[a-f0-9]{64}",evidence[k]["artifact_sha256"])
           for k in GATES):
        return result
    manifest_digest=digest_manifest(evidence)
    # External reviewer must verify signed claims, issuer trust, scope,
    # independent professional and security identities and exact artifacts.
    outcome=reviewer.verify(engine_id=engine["id"],
        commit_sha=commit_sha,manifest_sha256=manifest_digest,
        gate_ids=GATES,evidence=evidence)
    if outcome is not True:
        return result
    return {"engine_id":engine["id"],"status":"COMPLETE","complete":True,
            "evidence_sha256":manifest_digest,
            "product_release_approved":False}

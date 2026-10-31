"""ENG05 professional evidence governance V1: deterministic REVIEW-ONLY dossier.

No actual technical salon recommendations, production authority or external
professional sources are bundled. Detached Ed25519 review signatures are
verified against independent, externally supplied credential trust anchors.
"""
from __future__ import annotations
import base64
import hashlib
import json
import re
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

CONTRACT="abc.eng05.professional-source.v1.review"
REVIEW_CONTRACT="abc.eng05.specialist-review.v1.review"
VERSION_RE=re.compile(r"^[1-9][0-9]*\\.[0-9]+\\.[0-9]+$")
SHA_RE=re.compile(r"^[0-9a-f]{64}$")
SCOPE={"HAIRCUT","HAIR_COLOR","BEARD","SKIN_BEAUTY","MAKEUP","NAILS","EXTENSIONS","BRIDAL"}
KIND={"PEER_REVIEWED_RESEARCH","MANUFACTURER_PROTOCOL","PROFESSIONAL_GUIDELINE",
      "LICENSED_TRAINING_MANUAL","CI_SYNTHETIC_FIXTURE"}
STRENGTH={"LOW","MODERATE","HIGH","UNKNOWN"}
OUTCOME={"APPROVE","REJECT","REQUEST_REVISION"}


class SourceGovernanceError(ValueError):
    """Non-sensitive validation denial; callers cannot bypass the review gate."""


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),
                      ensure_ascii=True,allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _exact(value,fields,label):
    if not isinstance(value,dict) or set(value)!=set(fields):
        raise SourceGovernanceError(label+"_shape_invalid")


def _utc(value):
    if not isinstance(value,str):
        raise SourceGovernanceError("timestamp_required")
    try:
        parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise SourceGovernanceError("timestamp_invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SourceGovernanceError("timestamp_must_be_aware")
    return parsed.astimezone(timezone.utc)


def validate_document(doc,*,now=None):
    _exact(doc,("contract","source_id","version","source_type","publisher_id",
        "submitted_by","scope","jurisdiction","publication_ref","published_at",
        "expires_at","license_ref","content_sha256","claims"),"source")
    if doc["contract"]!=CONTRACT:
        raise SourceGovernanceError("source_contract_mismatch")
    if not isinstance(doc["source_id"],str) or not re.fullmatch(
         r"[a-z0-9][a-z0-9._:/-]{5,95}",doc["source_id"]):
        raise SourceGovernanceError("source_id_invalid")
    if not isinstance(doc["version"],str) or not VERSION_RE.fullmatch(doc["version"]):
        raise SourceGovernanceError("source_version_invalid")
    for field in ("publisher_id","submitted_by","jurisdiction","publication_ref",
                  "license_ref"):
        if not isinstance(doc[field],str) or not 3<=len(doc[field])<=200:
            raise SourceGovernanceError(field+"_invalid")
    if doc["source_type"] not in KIND or doc["scope"] not in SCOPE:
        raise SourceGovernanceError("source_type_or_scope_invalid")
    if not isinstance(doc["content_sha256"],str) or not SHA_RE.fullmatch(doc["content_sha256"]):
        raise SourceGovernanceError("content_digest_invalid")
    instant=_utc(now) if isinstance(now,str) else (now or datetime.now(timezone.utc))
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise SourceGovernanceError("now_must_be_aware")
    published=_utc(doc["published_at"])
    expires=_utc(doc["expires_at"])
    if published>instant or expires<=published:
        raise SourceGovernanceError("source_temporal_invalid")
    claims=doc["claims"]
    if not isinstance(claims,list) or not 1<=len(claims)<=48:
        raise SourceGovernanceError("claims_count_invalid")
    seen=set()
    for claim in claims:
        _exact(claim,("claim_id","topic","applicability","assertion",
            "evidence_ref","evidence_sha256","evidence_strength",
            "safety_critical","uncertainty"),"claim")
        for key in ("claim_id","topic","applicability","assertion","evidence_ref"):
            if not isinstance(claim[key],str) or not 3<=len(claim[key])<=512:
                raise SourceGovernanceError("claim_"+key+"_invalid")
        if not isinstance(claim["evidence_sha256"],str) or not SHA_RE.fullmatch(claim["evidence_sha256"]):
            raise SourceGovernanceError("claim_evidence_digest_invalid")
        if claim["evidence_strength"] not in STRENGTH or type(claim["safety_critical"]) is not bool:
            raise SourceGovernanceError("claim_evidence_level_invalid")
        if not isinstance(claim["uncertainty"],list) or len(set(claim["uncertainty"]))!=len(claim["uncertainty"]) or any(
           x not in ("CONTEXT_MISSING","EVIDENCE_LIMITED","NOT_GENERALIZABLE","CONTRAINDICATION_UNKNOWN")
           for x in claim["uncertainty"]):
            raise SourceGovernanceError("claim_uncertainty_invalid")
        if claim["claim_id"] in seen:
            raise SourceGovernanceError("duplicate_claim_id")
        seen.add(claim["claim_id"])
    return {"document_sha256":digest(doc),
        "expired":instant>=expires,"synthetic":doc["source_type"]=="CI_SYNTHETIC_FIXTURE"}


def _verify_review(review,doc,anchors,now):
    _exact(review,("contract","source_sha256","reviewer_id","credential_id",
       "issued_at","decision","reviewed_claim_ids","conflict_of_interest",
       "signature_alg","signature_b64"),"review")
    if review["contract"]!=REVIEW_CONTRACT or review["source_sha256"]!=digest(doc):
        raise SourceGovernanceError("review_document_hash_mismatch")
    if review["decision"] not in OUTCOME or review["signature_alg"]!="Ed25519":
        raise SourceGovernanceError("review_decision_or_algorithm_invalid")
    if type(review["conflict_of_interest"]) is not bool or review["conflict_of_interest"]:
        raise SourceGovernanceError("reviewer_conflict_of_interest")
    if review["reviewer_id"] in (doc["submitted_by"],doc["publisher_id"]):
        raise SourceGovernanceError("reviewer_not_independent")
    if not isinstance(review["reviewed_claim_ids"],list) or set(review["reviewed_claim_ids"])!=set(
          c["claim_id"] for c in doc["claims"]) or len(review["reviewed_claim_ids"])!=len(doc["claims"]):
        raise SourceGovernanceError("review_incomplete_claim_coverage")
    if not isinstance(anchors,dict) or review["credential_id"] not in anchors:
        raise SourceGovernanceError("independent_credential_anchor_missing")
    anchor=anchors[review["credential_id"]]
    _exact(anchor,("reviewer_id","credential_status","scopes","valid_from",
       "valid_until","public_key","authority_attested"),"credential_anchor")
    instant=_utc(now) if isinstance(now,str) else (now or datetime.now(timezone.utc))
    issued=_utc(review["issued_at"])
    if (anchor["reviewer_id"]!=review["reviewer_id"]
        or anchor["credential_status"]!="VERIFIED"
        or anchor["authority_attested"] is not True
        or doc["scope"] not in anchor["scopes"]
        or not _utc(anchor["valid_from"])<=issued<=instant
        or instant>=_utc(anchor["valid_until"])
        or issued>=_utc(anchor["valid_until"])):
        raise SourceGovernanceError("reviewer_qualification_unverified_or_expired")
    payload={k:v for k,v in review.items() if k!="signature_b64"}
    try:
        signature=base64.b64decode(review["signature_b64"],validate=True)
        pub=anchor["public_key"]
        if not isinstance(pub,Ed25519PublicKey):
            raise ValueError("untrusted_public_key")
        pub.verify(signature,canonical(payload))
    except Exception as exc:
        raise SourceGovernanceError("specialist_signature_invalid") from exc
    return True


def adjudicate(documents, reviews, *, trusted_credentials=None, now=None):
    """Return non-executable review dossier: conflicts/unknowns dominate approvals.

    documents may include multiple contradictory published versions; every
    submitted version is evaluated, never silently overridden by recency.
    """
    if not isinstance(documents,list) or not 1<=len(documents)<=64:
        raise SourceGovernanceError("invalid_dossier_count")
    if not isinstance(reviews,list):
        raise SourceGovernanceError("invalid_reviews")
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise SourceGovernanceError("now_must_be_aware")
    anchors=trusted_credentials or {}
    versions=set();statuses=[];unknowns=set();index={};accepted_claims=[]
    for doc in documents:
        facts=validate_document(doc,now=now)
        identity=(doc["source_id"],doc["version"])
        if identity in versions:
            raise SourceGovernanceError("duplicate_source_version")
        versions.add(identity)
        matched=[r for r in reviews if isinstance(r,dict)
                 and r.get("source_sha256")==facts["document_sha256"]]
        reviewers=set()
        rejected=False;qualified=[]
        for review in matched:
            _verify_review(review,doc,anchors,now)
            if review["reviewer_id"] in reviewers:
                raise SourceGovernanceError("reviewer_duplicate_or_replay")
            reviewers.add(review["reviewer_id"])
            if review["decision"]!="APPROVE":
                rejected=True
            qualified.append(review)
        critical=any(c["safety_critical"] for c in doc["claims"])
        required_reviews=2 if critical else 1
        accepted=(not facts["expired"] and not facts["synthetic"] and
           not rejected and len(qualified)>=required_reviews and
           all(r["decision"]=="APPROVE" for r in qualified))
        if facts["synthetic"]:
            unknowns.add("CI_SYNTHETIC_NOT_PROFESSIONAL")
        if facts["expired"]:
            unknowns.add("SOURCE_EXPIRED")
        if rejected:
            unknowns.add("SPECIALIST_REJECTED_OR_REVISION_REQUIRED")
        if len(qualified)<required_reviews:
            unknowns.add("SPECIALIST_APPROVAL_REQUIRED")
        for c in doc["claims"]:
            if c["evidence_strength"]=="UNKNOWN" or c["uncertainty"]:
                unknowns.add("EVIDENCE_UNCERTAIN")
            key=(doc["scope"],c["topic"],c["applicability"])
            index.setdefault(key,[]).append((doc,c,accepted))
            if accepted and c["evidence_strength"]!="UNKNOWN" and not c["uncertainty"]:
                accepted_claims.append((doc,c))
        statuses.append({"source_id":doc["source_id"],"version":doc["version"],
            "source_sha256":facts["document_sha256"],"qualified_reviews":len(qualified),
            "review_gate":"REVIEWED_NON_EXECUTABLE" if accepted else "BLOCKED",
            "required_independent_reviewers":required_reviews})
    conflicts=[]
    for key,entries in sorted(index.items()):
        assertions={c["assertion"] for _,c,_ in entries}
        if len(assertions)>1:
            conflicts.append({"scope":key[0],"topic":key[1],"applicability":key[2],
                "source_versions":sorted({d["source_id"]+"@"+d["version"] for d,_,_ in entries}),
                "severity":"SAFETY_CRITICAL" if any(c["safety_critical"] for _,c,_ in entries)
                          else "MATERIAL","state":"UNRESOLVED"})
    if conflicts:
        unknowns.add("UNRESOLVED_CONFLICT")
        if any(c["severity"]=="SAFETY_CRITICAL" for c in conflicts):
            unknowns.add("SAFETY_CRITICAL_CONFLICT")
    # Even with valid offline signatures, zero operational authority exists
    # until external ADR, managed issuer, consent and specialist deployment.
    return {"contract":"abc.eng05.knowledge-dossier.v1.review",
        "sources":statuses,"conflicts":conflicts,"unknowns":sorted(unknowns),
        "professionally_released_facts":[],
        "review_candidate_count":len(accepted_claims),
        "review_gate":"BLOCKED_CONFLICT" if conflicts else
            ("REVIEWED_NON_EXECUTABLE" if statuses and all(
               s["review_gate"]=="REVIEWED_NON_EXECUTABLE" for s in statuses)
               else "BLOCKED_QUALIFICATION"),
        "eng05_to_eng06_dispatch_authorized":False,
        "customer_release_approved":False,
        "professional_runtime_authorized":False}

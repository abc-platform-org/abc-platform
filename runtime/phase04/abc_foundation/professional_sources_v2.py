"""ENG-05/06 independently pinned, revocable Ed25519 professional source records.

This verifies detached signatures, review scope and reviewer registry dates.
It does not itself certify someone is a qualified beauty specialist: trusted
public keys and qualification roster must be provisioned by an independently
audited authority outside repository/user requests. No real roster shipped.
"""
import base64
import hashlib
import json
import re
from datetime import datetime,timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

_DIGEST=re.compile(r"^[0-9a-f]{64}$")
_TYPES=frozenset(("KNOWLEDGE","SOP"))
_FIELDS=frozenset(("record_ref","record_type","service_kind","version",
    "content_digest","reviewer_id","issuer_id","not_before","expires_at",
    "review_scope","status"))
_SCOPE="ABC_SPECIALIST_SERVICE_SOURCE_V1"


def _time(value):
    if not isinstance(value,str) or not value.endswith("Z"):
        raise ValueError("invalid_expiry")
    parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("naive_expiry")
    return parsed.astimezone(timezone.utc)


def _canonical(payload):
    return json.dumps(payload,sort_keys=True,separators=(",",":"),
                      ensure_ascii=True,allow_nan=False).encode("utf-8")


class ProfessionalSourceRegistry:
    def __init__(self,*,pinned_public_keys,qualified_reviewers,
                 signed_records,approved_content,revoked_refs=(),clock=None):
        """All arguments MUST come from independently governed trust storage.

        Supplying test-generated pins verifies only test fixtures. Neither a
        request payload nor a model may update this registry at runtime.
        """
        if (not isinstance(pinned_public_keys,dict) or not pinned_public_keys
            or not isinstance(qualified_reviewers,dict)
            or not isinstance(signed_records,dict)
            or not isinstance(approved_content,dict)
            or not isinstance(revoked_refs,(list,tuple,set,frozenset))):
            raise ValueError("unprovisioned_external_trust_registry")
        self.keys={}
        for issuer,key in pinned_public_keys.items():
            if (not isinstance(issuer,str) or not issuer.strip()
                or type(key) is not bytes or len(key)!=32):
                raise ValueError("invalid_pinned_external_key")
            self.keys[issuer]=Ed25519PublicKey.from_public_bytes(key)
        self.reviewers=qualified_reviewers
        self.records=signed_records
        self.content=approved_content
        self.revoked=frozenset(revoked_refs)
        self.clock=clock if clock is not None else lambda: datetime.now(timezone.utc)

    def verify(self,*,ref,record_type,service_kind,version=None,digest=None):
        if (not isinstance(ref,str) or record_type not in _TYPES
            or ref in self.revoked):
            return False
        entry=self.records.get(ref)
        if not isinstance(entry,dict) or set(entry)!={"record","signature_b64"}:
            return False
        record=entry["record"]
        if not isinstance(record,dict) or set(record)!=_FIELDS:
            return False
        if (record["record_ref"]!=ref
            or record["record_type"]!=record_type
            or record["service_kind"]!=service_kind
            or record["review_scope"]!=_SCOPE
            or record["status"]!="ACTIVE"
            or (version is not None and record["version"]!=version)
            or (digest is not None and record["content_digest"]!=digest)
            or not isinstance(record["content_digest"],str)
            or not _DIGEST.fullmatch(record["content_digest"])):
            return False
        material=self.content.get(ref)
        if (type(material) is not bytes
            or not 1<=len(material)<=2*1024*1024
            or hashlib.sha256(material).hexdigest()!=record["content_digest"]):
            return False
        issuer=record["issuer_id"]
        key=self.keys.get(issuer)
        reviewer=self.reviewers.get(record["reviewer_id"])
        if key is None or not isinstance(reviewer,dict):
            return False
        if (reviewer.get("issuer_id")!=issuer
            or service_kind not in reviewer.get("service_kinds",())
            or record_type not in reviewer.get("review_types",())):
            return False
        try:
            now=self.clock()
            if not isinstance(now,datetime) or now.tzinfo is None:
                return False
            now=now.astimezone(timezone.utc)
            if not (_time(record["not_before"])<=now
                    <_time(record["expires_at"])
                    and now<_time(reviewer["qualification_valid_until"])):
                return False
            signature=base64.b64decode(entry["signature_b64"],validate=True)
            if len(signature)!=64:
                return False
            key.verify(signature,_canonical(record))
            return True
        except (ValueError,TypeError,KeyError,InvalidSignature,OverflowError):
            return False


class SignedKnowledgePolicyGate:
    """Composition of distinct professional source and ENG14 policy authorities."""
    def __init__(self,registry,policy_authority):
        if not isinstance(registry,ProfessionalSourceRegistry):
            raise ValueError("professional_source_registry_required")
        self.registry=registry
        self.policy=policy_authority

    def verify(self,**claims):
        if (not self.policy or not callable(getattr(self.policy,"verify",None))
            or self.policy.verify(
                tenant_id=claims["tenant_id"],branch_id=claims["branch_id"],
                session_id=claims["session_id"],
                state_version=claims["state_version"],
                recommendation_ref=claims["recommendation_ref"],
                policy_gate=claims["policy_gate"]) is not True):
            return False
        sources=claims["knowledge_sources"]
        if not isinstance(sources,list) or not sources:
            return False
        return all(self.registry.verify(ref=s["source_ref"],
            record_type="KNOWLEDGE",service_kind=claims["service_kind"],
            version=s["version"],digest=s["digest"]) for s in sources)


class SignedSOPConsentGate:
    """Requires a signed SOP AND separate consent/evidence/look/decision authority."""
    def __init__(self,registry,evidence_authority):
        if not isinstance(registry,ProfessionalSourceRegistry):
            raise ValueError("professional_source_registry_required")
        self.registry=registry
        self.evidence=evidence_authority

    def verify(self,**claims):
        ref=claims["approved_sop_ref"]
        if (not self.registry.verify(ref=ref,record_type="SOP",
              service_kind=claims["service_kind"])
            or not self.evidence
            or not callable(getattr(self.evidence,"verify",None))):
            return False
        return self.evidence.verify(**claims) is True

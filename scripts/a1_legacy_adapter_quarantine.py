"""A1 compatibility boundary: validate legacy envelopes, never dispatch.

This intentionally does not transform unapproved historical artifacts into
canonical professional decisions.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ADAPTERS=json.loads((ROOT/"governance/abc_v2_to_19_adapters.v0.review.json").read_text())
IDS={a["adapter_id"] for a in ADAPTERS["adapters"]}
REQUIRED=("tenant_id","branch_id","session_id","source_sha256","consent_decision_id","policy_decision_id","artifact_version","artifact")
class AdapterRejected(ValueError): pass

def inspect_legacy_envelope(adapter_id,envelope):
    if adapter_id not in IDS: raise AdapterRejected("unknown_adapter")
    if not isinstance(envelope,dict): raise AdapterRejected("invalid_envelope")
    if any(k not in envelope for k in REQUIRED): raise AdapterRejected("missing_provenance_or_scope")
    if any(not isinstance(envelope[k],str) or not envelope[k].strip()
           for k in REQUIRED if k!="artifact"): raise AdapterRejected("invalid_scope")
    if envelope["artifact_version"]!="abc.internal.engine.v2.draft":
        raise AdapterRejected("unsupported_source_version")
    if envelope["source_sha256"]!=hashlib.sha256(
            json.dumps(envelope["artifact"],sort_keys=True,separators=(",",":"),
                       ensure_ascii=False).encode()).hexdigest():
        raise AdapterRejected("source_digest_mismatch")
    if envelope.get("customer_release_approved") is not False:
        raise AdapterRejected("release_must_be_explicitly_denied")
    if envelope.get("downstream_dispatch_authorized") is not False:
        raise AdapterRejected("dispatch_must_be_explicitly_denied")
    return {"adapter_id":adapter_id,"status":"QUARANTINED_UNMIGRATED",
            "source_digest_verified":True,"runtime_dispatch":False,
            "customer_release_approved":False}

def dispatch(*_args,**_kwargs):
    raise AdapterRejected("canonical_v3_dispatch_not_authorized")

def build_review_only_canonical_envelope(adapter_id,envelope):
    """Deterministic v2-to-v3 review projection, never operational dispatch.

    The source is retained verbatim, with no inferred professional authority.
    """
    inspect_legacy_envelope(adapter_id,envelope)
    adapter=next(a for a in ADAPTERS["adapters"] if a["adapter_id"]==adapter_id)
    if adapter["runtime_enabled"] or adapter["customer_release_approved"]:
        raise AdapterRejected("adapter_registry_must_remain_disabled")
    return {
        "adapter_id":adapter_id,
        "target_engine":adapter["target_engine"],
        "source_version":envelope["artifact_version"],
        "target_version":ADAPTERS["target_protocol"],
        "tenant_id":envelope["tenant_id"],
        "branch_id":envelope["branch_id"],
        "session_id":envelope["session_id"],
        "source_sha256":envelope["source_sha256"],
        "consent_decision_id":envelope["consent_decision_id"],
        "policy_decision_id":envelope["policy_decision_id"],
        "source_artifact":envelope["artifact"],
        "authority":"UNVERIFIED_REVIEW_ONLY",
        "migration_status":"SHADOW_PROJECTION_ONLY",
        "dispatch_authorized":False,
        "customer_release_approved":False,
    }

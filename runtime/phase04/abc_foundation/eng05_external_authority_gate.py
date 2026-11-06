"""Independent external evidence gate for ENG05. Review only, never dispatch."""
from datetime import datetime, timezone
from .eng05_professional_sources import adjudicate, digest, SourceGovernanceError

def evaluate_external_authority(documents, reviews, *, registry, revoked, legal_receipts, now=None):
    """Reject unknown/revoked credentials; require version-bound legal receipts."""
    now = now or datetime.now(timezone.utc)
    if not callable(registry) or not callable(revoked):
        raise SourceGovernanceError("independent_credential_registry_required")
    if not isinstance(legal_receipts, dict):
        raise SourceGovernanceError("legal_evidence_missing")
    anchors = {}
    for review in reviews:
        credential = review.get("credential_id") if isinstance(review, dict) else None
        if not credential or revoked(credential) is not False:
            raise SourceGovernanceError("credential_revoked_or_unknown")
        anchor = registry(credential)
        if not isinstance(anchor, dict):
            raise SourceGovernanceError("credential_not_independently_attested")
        anchors[credential] = anchor
    dossier = adjudicate(documents, reviews, trusted_credentials=anchors, now=now)
    # A credential revoked during signature adjudication must not survive.
    for credential in anchors:
        if revoked(credential) is not False:
            raise SourceGovernanceError("credential_revoked_during_adjudication")
    rights_ok = all(
        isinstance(legal_receipts.get(digest(doc)), dict)
        and legal_receipts[digest(doc)].get("independent_counsel_verified") is True
        and legal_receipts[digest(doc)].get("commercial_ingestion") is True
        and legal_receipts[digest(doc)].get("jurisdiction") == doc["jurisdiction"]
        and legal_receipts[digest(doc)].get("source_version") == doc["version"]
        for doc in documents
    )
    return {
        "contract": "abc.eng05.external-authority-review.v1",
        "professional_dossier": dossier,
        "rights_evidence_present": rights_ok,
        "eng05_ingestion_authorized": False,
        "eng06_dispatch_authorized": False,
        "customer_release_authorized": False,
        "decision": "BLOCKED_PENDING_GOVERNANCE"
    }

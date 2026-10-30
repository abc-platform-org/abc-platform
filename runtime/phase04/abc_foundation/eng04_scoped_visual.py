"""ENG04 scoped, evidence-gated image QA admission for controlled offline testing.

Real pixels must bind to independently authenticated tenant/session media. The
current v2 JSON contract only permits synthetic media handles and has no
production upload path. This module does NOT create recommendations or access
customer files, cameras, networks, or vision-model inference.
"""
from .eng04_visual_qa import inspect_visual_fidelity,VisualQAError
from .engine_v2_contracts import validate_port
from .store import DomainError


def inspect_scoped_visual(message,*,before_bytes,after_bytes,editable_mask_png,
                          protected_face_mask_png,reference_bytes=(),
                          media_authority=None):
    validate_port(message,engine="ENG-04")
    payload=message["payload"]
    if (payload["service_kind"] not in ("HAIR_COLOR","HAIRCUT")
        or payload["edit_regions"]!=["HAIR"]
        or len(reference_bytes)!=len(payload["reference_media_refs"])):
        raise DomainError(403,"eng04_scoped_media_profile_denied")
    if media_authority is None or not callable(getattr(media_authority,"verify",None)):
        raise DomainError(403,"trusted_media_authority_unavailable")
    result=inspect_visual_fidelity(before_bytes=before_bytes,
         after_bytes=after_bytes,editable_mask_png=editable_mask_png,
         protected_face_mask_png=protected_face_mask_png,
         reference_bytes=reference_bytes)
    try:
        verified=media_authority.verify(
            tenant_id=message["tenant_id"],branch_id=message["branch_id"],
            session_id=message["session_id"],
            state_version=message["state_version"],
            source_media_ref=payload["current_media_ref"],
            reference_media_refs=payload["reference_media_refs"],
            source_pixel_digest=result["source_pixel_digest"],
            reference_pixel_digests=result["reference_pixel_digests"],
            evidence=payload["evidence"])
    except (ValueError,TypeError,KeyError,RuntimeError):
        verified=False
    if verified is not True:
        raise DomainError(403,"scoped_media_provenance_not_verified")
    # Measured fidelity can be reported for human review, NEVER promoted to
    # biometric identity verification or accepted on behalf of the customer.
    return {**result,"tenant_scope_validated_by_injected_authority":True,
            "professional_approval_verified":False,
            "image_realism_verified":False}

"""ENG11 candidate: measured image pixels only, never identity verification."""
from .eng04_visual_qa import inspect_visual_fidelity
from .v2_to_19_projection import _emit,_validate_pair

def project_visual_pixels_to_eng11(*,request,response,before_bytes,
                                  after_bytes,editable_mask_png,
                                  protected_face_mask_png,reference_bytes=()):
    _validate_pair(request,response,"ENG-04")
    r=inspect_visual_fidelity(
        before_bytes=before_bytes,after_bytes=after_bytes,
        editable_mask_png=editable_mask_png,
        protected_face_mask_png=protected_face_mask_png,
        reference_bytes=reference_bytes)
    m=r["measured"]
    payload={
        "source_status":r["status"],
        "source_pixel_digest":r["source_pixel_digest"],
        "candidate_pixel_digest":r["candidate_pixel_digest"],
        "changed_outside_edit_mask":m["changed_outside_edit_mask"],
        "changed_within_protected_face":m["changed_within_protected_face"],
        "edited_within_mask":m["edited_within_mask"],
        "face_mask_verified":False,"identity_verified":False,
        "reference_provenance_verified":False,
        "independent_visual_review_complete":False}
    return _emit(request,response,"A04_PIXEL_TO_11_QA_EVIDENCE",payload)

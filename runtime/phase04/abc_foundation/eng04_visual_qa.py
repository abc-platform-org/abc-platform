"""ENG-04: real decoded-image visual QA (PNG/JPEG), not facial recognition.

This measures pixel fidelity, editable-region masks, protected-face changes,
reference-image copying, sharpness and exposure. It does NOT locate a face,
authenticate a mask, verify a person's identity or generate an edited image.
Production requires trusted segmentation, image/evidence authorization and
independent specialist visual QA. No media is stored or uploaded.
"""
import hashlib
import io
from dataclasses import dataclass

from PIL import Image, ImageChops, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError

MAX_ENCODED_BYTES=8*1024*1024
MAX_PIXELS=2048*2048
MIN_DIM=32
FORMATS=frozenset(("PNG","JPEG"))
# Exact original-pixel preservation is the only threshold accepted by this
# offline candidate review. JPEG re-encoding may therefore fail closed.
MAX_LOCKED_PIXEL_CHANGES=0
MAX_PROTECTED_FACE_CHANGES=0
MIN_EDITED_PIXELS=1


class VisualQAError(ValueError):
    """Non-sensitive, bounded error identifier only."""


def _decode(encoded,*,mask=False):
    if not isinstance(encoded,bytes) or not 1<=len(encoded)<=MAX_ENCODED_BYTES:
        raise VisualQAError("INVALID_OR_OVERSIZED_IMAGE")
    try:
        with Image.open(io.BytesIO(encoded)) as original:
            if (original.format not in (("PNG",) if mask else FORMATS)
                or getattr(original,"n_frames",1)!=1
                or not MIN_DIM<=original.width<=2048
                or not MIN_DIM<=original.height<=2048
                or original.width*original.height>MAX_PIXELS):
                raise VisualQAError("UNSUPPORTED_IMAGE_DIMENSIONS_OR_FORMAT")
            result=ImageOps.exif_transpose(original)
            result.load()
            if mask:
                if result.mode!="L":
                    raise VisualQAError("MASK_MUST_BE_GRAYSCALE_PNG")
                counts=result.histogram()
                if any(counts[1:255]):
                    raise VisualQAError("MASK_MUST_BE_BINARY")
            else:
                if result.mode not in ("RGB","L"):
                    raise VisualQAError("UNSUPPORTED_COLOR_OR_TRANSPARENCY")
                result=result.convert("RGB")
            return result.copy()
    except VisualQAError:
        raise
    except (OSError,ValueError,UnidentifiedImageError,Image.DecompressionBombError):
        raise VisualQAError("CORRUPT_OR_UNTRUSTED_IMAGE") from None


def _mask_count(mask):
    return mask.histogram()[255]


def _changed_pixels(before,after):
    difference=ImageChops.difference(before,after)
    red,green,blue=difference.split()
    return ImageChops.lighter(ImageChops.lighter(red,green),blue).point(
        lambda v:255 if v>0 else 0)


def _pixel_digest(image):
    # Hash normalized, decoded image pixels; metadata and EXIF are irrelevant.
    return hashlib.sha256(
        image.width.to_bytes(4,"big")+image.height.to_bytes(4,"big")+
        image.tobytes()).hexdigest()


def _image_metrics(image):
    gray=image.convert("L")
    hist=gray.histogram()
    n=image.width*image.height
    edge=gray.filter(ImageFilter.FIND_EDGES)
    edge_std=ImageStat.Stat(edge).stddev[0]
    return {"mean_luminance_8bit":round(ImageStat.Stat(gray).mean[0],2),
        "edge_variance_proxy":round(edge_std**2,2),
        "clipped_dark_fraction":round(sum(hist[:6])/n,6),
        "clipped_bright_fraction":round(sum(hist[250:])/n,6)}


@dataclass(frozen=True)
class VisualQABudget:
    """Explicit acceptance limits for pixel guards; NOT a visual ML SLO."""
    locked_pixel_tolerance: int=MAX_LOCKED_PIXEL_CHANGES
    face_pixel_tolerance: int=MAX_PROTECTED_FACE_CHANGES
    minimum_edit_pixels: int=MIN_EDITED_PIXELS

    def __post_init__(self):
        if (self.locked_pixel_tolerance!=0 or
            self.face_pixel_tolerance!=0 or
            self.minimum_edit_pixels!=1):
            raise VisualQAError("UNAPPROVED_QA_THRESHOLD_OVERRIDE")


def inspect_visual_fidelity(*,before_bytes,after_bytes,editable_mask_png,
                            protected_face_mask_png,reference_bytes=(),
                            budget=None):
    """Measure real pixel edits with fail-closed hard limits.

    Masks are caller-provided *untrusted* annotations, not segmentation proof.
    A guarded result is not identity recognition, authorized hair treatment,
    reference interpretation or an independent specialist sign-off.
    """
    limit=budget if budget is not None else VisualQABudget()
    if not isinstance(limit,VisualQABudget):
        raise VisualQAError("INVALID_QA_BUDGET")
    if not isinstance(reference_bytes,(tuple,list)) or len(reference_bytes)>6:
        raise VisualQAError("INVALID_REFERENCE_SET")
    before=_decode(before_bytes)
    after=_decode(after_bytes)
    edit=_decode(editable_mask_png,mask=True)
    face=_decode(protected_face_mask_png,mask=True)
    size=before.size
    if after.size!=size or edit.size!=size or face.size!=size:
        raise VisualQAError("IMAGE_OR_MASK_DIMENSION_MISMATCH")
    if edit.mode!="L" or face.mode!="L":
        raise VisualQAError("UNTRUSTED_MASK_FORMAT")
    n=size[0]*size[1]
    editable=_mask_count(edit)
    protected=_mask_count(face)
    if (not 0<editable<=int(n*0.85) or
        not 0<protected<=int(n*0.5) or
        ImageChops.multiply(edit,face).getbbox() is not None):
        raise VisualQAError("MISSING_OR_OVERLAPPING_REGION_PROTECTION")
    # Strict face control is an exact pixel invariant inside the supplied
    # face mask. It CANNOT establish that the mask actually covers a face.
    changed=_changed_pixels(before,after)
    all_changed=_mask_count(changed)
    editable_changed=_mask_count(ImageChops.multiply(changed,edit))
    face_changed=_mask_count(ImageChops.multiply(changed,face))
    locked_changed=all_changed-editable_changed
    before_digest=_pixel_digest(before)
    after_digest=_pixel_digest(after)
    seen=set()
    copied_reference=False
    for item in reference_bytes:
        ref=_decode(item)
        digest=_pixel_digest(ref)
        if digest in seen or digest==before_digest or digest==after_digest:
            copied_reference=True
        seen.add(digest)
    failures=[]
    if locked_changed>limit.locked_pixel_tolerance:
        failures.append("LOCKED_REGION_PIXELS_CHANGED")
    if face_changed>limit.face_pixel_tolerance:
        failures.append("PROTECTED_FACE_PIXELS_CHANGED")
    if editable_changed<limit.minimum_edit_pixels:
        failures.append("NO_EDIT_WITHIN_ALLOWED_REGION")
    if copied_reference:
        failures.append("REFERENCE_IMAGE_DUPLICATED_OR_COPIED")
    return {
        "engine_id":"ENG-04",
        "algorithm":"abc.visualqa.pixel-fidelity.v1",
        "status":"BLOCKED" if failures else "PIXEL_GUARDS_PASSED_REVIEW_REQUIRED",
        "visual_qa_status":"FAILED" if failures else "REQUIRES_REVIEW",
        "identity_verified":False,
        "face_region_annotation_verified":False,
        "reference_provenance_verified":False,
        "source_pixel_digest":before_digest,
        "candidate_pixel_digest":after_digest,
        "reference_pixel_digests":sorted(seen),
        "image_size":{"width":size[0],"height":size[1]},
        "measured":{
            "total_changed_pixels":all_changed,
            "editable_pixels":editable,
            "edited_within_mask":editable_changed,
            "changed_outside_edit_mask":locked_changed,
            "protected_face_pixels":protected,
            "changed_within_protected_face":face_changed,
            "changed_outside_fraction":round(locked_changed/n,8),
            "before":_image_metrics(before),
            "after":_image_metrics(after)
        },
        "thresholds":{
            "maximum_changed_outside_mask":0,
            "maximum_changed_in_face_mask":0,
            "minimum_changed_inside_mask":1,
            "copy_of_reference_forbidden":True
        },
        "failures":failures,
        "release_approved":False,
        "execution_authorized":False
    }

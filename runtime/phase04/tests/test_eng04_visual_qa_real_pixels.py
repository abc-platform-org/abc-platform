"""Real pixel tests with in-memory RGB PNG/JPEG, no personal image data."""
import io
import unittest

from PIL import Image, ImageDraw
from abc_foundation.eng04_visual_qa import (
    inspect_visual_fidelity,VisualQAError,VisualQABudget)


def png(image):
    b=io.BytesIO()
    image.save(b,format="PNG")
    return b.getvalue()


class RealPixelVisualQATests(unittest.TestCase):
    def setUp(self):
        self.before=Image.new("RGB",(64,64),(74,93,117))
        painter=ImageDraw.Draw(self.before)
        for i in range(64):
            painter.line((0,i,63,i),fill=(i+50,93,117))
        self.edit=Image.new("L",(64,64),0)
        ImageDraw.Draw(self.edit).rectangle((4,4,24,24),fill=255)
        self.face=Image.new("L",(64,64),0)
        ImageDraw.Draw(self.face).rectangle((30,20,45,43),fill=255)
        self.after=self.before.copy()
        ImageDraw.Draw(self.after).rectangle((10,10,20,20),
                                           fill=(198,104,92))

    def run_qa(self,after=None,edit=None,face=None,refs=()):
        return inspect_visual_fidelity(
            before_bytes=png(self.before),
            after_bytes=png(after or self.after),
            editable_mask_png=png(edit or self.edit),
            protected_face_mask_png=png(face or self.face),
            reference_bytes=refs
        )

    def test_positive_real_decoding_with_exact_region_preservation(self):
        r=self.run_qa()
        self.assertEqual(r["status"],"PIXEL_GUARDS_PASSED_REVIEW_REQUIRED")
        self.assertEqual(r["visual_qa_status"],"REQUIRES_REVIEW")
        self.assertEqual(r["failures"],[])
        self.assertEqual(r["measured"]["changed_outside_edit_mask"],0)
        self.assertEqual(r["measured"]["changed_within_protected_face"],0)
        self.assertEqual(r["measured"]["edited_within_mask"],121)
        self.assertEqual(r["image_size"],{"width":64,"height":64})
        self.assertFalse(r["identity_verified"])
        self.assertFalse(r["face_region_annotation_verified"])
        self.assertFalse(r["reference_provenance_verified"])
        self.assertGreater(r["measured"]["after"]["mean_luminance_8bit"],0)
        self.assertIn("edge_variance_proxy",r["measured"]["after"])
        self.assertFalse(r["release_approved"])

    def test_outside_region_and_protected_face_are_independent_hard_failures(self):
        wrong=self.after.copy()
        wrong.putpixel((55,55),(1,2,3))
        wrong.putpixel((35,31),(4,5,6))
        result=self.run_qa(after=wrong)
        self.assertEqual(result["status"],"BLOCKED")
        self.assertEqual(result["measured"]["changed_outside_edit_mask"],2)
        self.assertEqual(result["measured"]["changed_within_protected_face"],1)
        self.assertIn("LOCKED_REGION_PIXELS_CHANGED",result["failures"])
        self.assertIn("PROTECTED_FACE_PIXELS_CHANGED",result["failures"])

    def test_no_real_edit_and_excessive_mask_are_blocked(self):
        r=self.run_qa(after=self.before)
        self.assertIn("NO_EDIT_WITHIN_ALLOWED_REGION",r["failures"])
        overbroad=Image.new("L",(64,64),255)
        with self.assertRaisesRegex(VisualQAError,"MISSING_OR_OVERLAPPING"):
            self.run_qa(edit=overbroad)

    def test_reference_copy_and_same_source_detected(self):
        self.assertIn("REFERENCE_IMAGE_DUPLICATED_OR_COPIED",
                      self.run_qa(refs=(png(self.after),))["failures"])
        self.assertIn("REFERENCE_IMAGE_DUPLICATED_OR_COPIED",
                      self.run_qa(refs=(png(self.before),))["failures"])
        self.assertEqual(self.run_qa(refs=(
            png(Image.new("RGB",(64,64),(4,5,6))),))["failures"],[])

    def test_mask_overlap_nonbinary_and_shape_errors_fail_closed(self):
        face=self.face.copy()
        face.putpixel((10,10),255)
        with self.assertRaisesRegex(VisualQAError,"MISSING_OR_OVERLAPPING"):
            self.run_qa(face=face)
        invalid=self.edit.copy()
        invalid.putpixel((0,0),100)
        with self.assertRaisesRegex(VisualQAError,"MASK_MUST_BE_BINARY"):
            self.run_qa(edit=invalid)
        other=Image.new("RGB",(80,64),(1,2,3))
        with self.assertRaisesRegex(VisualQAError,"DIMENSION_MISMATCH"):
            self.run_qa(after=other)

    def test_corrupted_image_and_wrong_format_fail_closed(self):
        with self.assertRaises(VisualQAError):
            inspect_visual_fidelity(before_bytes=b"fake",after_bytes=png(self.after),
                editable_mask_png=png(self.edit),
                protected_face_mask_png=png(self.face))
        b=io.BytesIO()
        self.edit.save(b,format="JPEG")
        with self.assertRaises(VisualQAError):
            inspect_visual_fidelity(before_bytes=png(self.before),
                after_bytes=png(self.after),editable_mask_png=b.getvalue(),
                protected_face_mask_png=png(self.face))
        with self.assertRaisesRegex(VisualQAError,"OVERSIZED"):
            inspect_visual_fidelity(before_bytes=b"x"*(8*1024*1024+1),
                after_bytes=png(self.after),editable_mask_png=png(self.edit),
                protected_face_mask_png=png(self.face))

    def test_no_unapproved_threshold_relaxation(self):
        with self.assertRaisesRegex(VisualQAError,"UNAPPROVED_QA_THRESHOLD"):
            VisualQABudget(locked_pixel_tolerance=1)
        self.assertEqual(self.run_qa()["thresholds"]["maximum_changed_outside_mask"],0)


if __name__=="__main__":
    unittest.main()

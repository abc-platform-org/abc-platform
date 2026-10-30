"""ENG04 authenticated-media boundary: no caller-supplied source ref trusted alone."""
import unittest
from PIL import Image
from abc_foundation.eng04_scoped_visual import inspect_scoped_visual
from abc_foundation.store import DomainError
from test_engine_v2_contracts import request
from test_eng04_visual_qa_real_pixels import RealPixelVisualQATests,png


class ScopedPixelEvidenceTests(unittest.TestCase):
    def setUp(self):
        fixture=RealPixelVisualQATests()
        fixture.setUp()
        self.files={
            "before_bytes":png(fixture.before),
            "after_bytes":png(fixture.after),
            "editable_mask_png":png(fixture.edit),
            "protected_face_mask_png":png(fixture.face),
            "reference_bytes":(png(Image.new("RGB",(64,64),(9,10,11))),)
        }
        self.req=request("ENG-04")

    def test_no_implicit_media_trust_and_positive_trusted_test_only_scope(self):
        with self.assertRaisesRegex(DomainError,"trusted_media_authority_unavailable"):
            inspect_scoped_visual(self.req,**self.files)
        class TestOnlyPinnedAuthority:
            def verify(self,**kw):
                return (kw["tenant_id"]=="tenant-test"
                    and kw["source_media_ref"]=="synthetic:original-hair"
                    and kw["reference_media_refs"]==["synthetic:reference-one"]
                    and kw["source_pixel_digest"].isalnum())
        result=inspect_scoped_visual(self.req,**self.files,
                          media_authority=TestOnlyPinnedAuthority())
        self.assertEqual(result["status"],"PIXEL_GUARDS_PASSED_REVIEW_REQUIRED")
        self.assertTrue(result["tenant_scope_validated_by_injected_authority"])
        self.assertFalse(result["identity_verified"])
        self.assertFalse(result["professional_approval_verified"])

        other=dict(self.req)
        other["tenant_id"]="other-tenant"
        with self.assertRaisesRegex(DomainError,"scoped_media_provenance_not_verified"):
            inspect_scoped_visual(other,**self.files,
                          media_authority=TestOnlyPinnedAuthority())

    def test_reference_count_wrong_service_and_unsupported_regions_rejected(self):
        class AlwaysTrueTestGate:
            def verify(self,**kw):
                return True
        with self.assertRaises(DomainError):
            inspect_scoped_visual(self.req,**{**self.files,"reference_bytes":()},
                media_authority=AlwaysTrueTestGate())
        wrong=request("ENG-04")
        wrong["payload"]["service_kind"]="MAKEUP"
        with self.assertRaises(DomainError):
            inspect_scoped_visual(wrong,**self.files,
                media_authority=AlwaysTrueTestGate())
        wrong=request("ENG-04")
        wrong["payload"]["edit_regions"]=["HAIR","SKIN"]
        with self.assertRaises(DomainError):
            inspect_scoped_visual(wrong,**self.files,
                media_authority=AlwaysTrueTestGate())


if __name__=="__main__":
    unittest.main()

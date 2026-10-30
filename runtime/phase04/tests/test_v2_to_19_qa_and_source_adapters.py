"""Synthetic bytes and ephemeral keys only; ENG11/ENG16 never approve a service."""
import io
import os
import unittest
from unittest.mock import patch
from PIL import Image,ImageDraw
from abc_foundation.store import DomainError
from abc_foundation.v2_to_19_pixel_projection import project_visual_pixels_to_eng11
from abc_foundation.v2_to_19_source_projection import project_signed_source_to_eng16
from test_engine_v2_contracts import request,response

def png(image):
    b=io.BytesIO()
    image.save(b,format="PNG")
    return b.getvalue()

class AdapterQualityEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{"ABC_ENV":"LOCAL_INTEGRATION_ONLY"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_pixel_measured_but_identity_not_claimed(self):
        before=Image.new("RGB",(64,64),(55,63,74))
        after=before.copy()
        ImageDraw.Draw(after).rectangle((5,5,15,15),fill=(100,110,120))
        edit=Image.new("L",(64,64),0)
        ImageDraw.Draw(edit).rectangle((2,2,24,24),fill=255)
        face=Image.new("L",(64,64),0)
        ImageDraw.Draw(face).rectangle((34,24,49,40),fill=255)
        q=request("ENG-04");r=response(q)
        def project(image):
            return project_visual_pixels_to_eng11(
                request=q,response=r,before_bytes=png(before),after_bytes=png(image),
                editable_mask_png=png(edit),protected_face_mask_png=png(face))
        x=project(after)
        self.assertEqual(x["target_engine"],"ENG-11")
        self.assertEqual(x["projection"]["source_status"],
                         "PIXEL_GUARDS_PASSED_REVIEW_REQUIRED")
        self.assertFalse(x["projection"]["identity_verified"])
        self.assertFalse(x["projection"]["face_mask_verified"])
        self.assertFalse(x["provenance_authority_verified"])
        bad=after.copy()
        bad.putpixel((36,27),(0,0,0))
        self.assertEqual(project(bad)["projection"]["source_status"],"BLOCKED")

    def test_sop_signature_is_not_a_specialist_decision(self):
        from test_eng05_06_signed_professional_sources import (
            SignedProfessionalSourceTests,SOP)
        fixture=SignedProfessionalSourceTests(
            "test_registry_positive_exact_signature_digest_and_scope")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        req=request("ENG-06")
        req["payload"]["approved_sop_ref"]=SOP
        resp=response(req)
        x=project_signed_source_to_eng16(
            request=req,response=resp,registry=fixture.registry())
        self.assertEqual(x["target_engine"],"ENG-16")
        self.assertTrue(x["projection"]["signed_source_content_verified"])
        self.assertFalse(x["projection"]["independent_specialist_qualification_verified"])
        self.assertFalse(x["projection"]["professional_validation_complete"])
        self.assertFalse(x["professional_validation_complete"])
        revoked=project_signed_source_to_eng16(
            request=req,response=resp,registry=fixture.registry(revoked=[SOP]))
        self.assertFalse(revoked["projection"]["signed_source_content_verified"])
        with self.assertRaises(DomainError):
            project_signed_source_to_eng16(request=req,response=resp,
                                            registry=object())

    def test_missing_sop_cannot_be_converted_to_validated_specialist(self):
        req=request("ENG-06")
        resp=response(req)
        from test_eng05_06_signed_professional_sources import SignedProfessionalSourceTests
        fixture=SignedProfessionalSourceTests(
            "test_registry_positive_exact_signature_digest_and_scope")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        with self.assertRaises(DomainError):
            project_signed_source_to_eng16(
                request=req,response=resp,registry=fixture.registry())

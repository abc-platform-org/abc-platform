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

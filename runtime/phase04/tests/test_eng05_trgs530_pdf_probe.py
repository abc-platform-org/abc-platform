"""Offline adversarial checks for official TRGS530 PDF provenance probe.

CI generates mock *synthetic* PDFs; never stores/copies a real third-party PDF.
"""
import importlib.util
import io
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from pypdf import PdfWriter
from pypdf.generic import NameObject,DictionaryObject,DecodedStreamObject

ROOT=Path(__file__).resolve().parents[3]
SPEC=importlib.util.spec_from_file_location(
 "eng05_trgs530_pdf_byte_probe",
 ROOT/"scripts/eng05_trgs530_pdf_byte_probe.py")
probe=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def synthetic_pdf(*,pages=15,identity=True):
    writer=PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612,height=792)
    if identity:
        page=writer.pages[0]
        font=DictionaryObject({
          NameObject("/Type"):NameObject("/Font"),
          NameObject("/Subtype"):NameObject("/Type1"),
          NameObject("/BaseFont"):NameObject("/Helvetica")})
        res=DictionaryObject({NameObject("/Font"):DictionaryObject({
           NameObject("/F1"):writer._add_object(font)})})
        page[NameObject("/Resources")]=res
        st=DecodedStreamObject()
        st.set_data(b"BT /F1 12 Tf 72 700 Td "
          b"(TRGS 530 Friseurhandwerk 20.04.2023) Tj ET")
        page[NameObject("/Contents")]=writer._add_object(st)
    # A PDF with a large metadata field exercises bounded-byte policy,
    # not a valid recreation of the actual official source.
    writer.add_metadata({"/ABC_CI_SYNTHETIC_PADDING":"X"*40000})
    buf=io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


class Trgs530ByteProbeTests(unittest.TestCase):
    def test_allowed_origins_are_exact_and_non_substitutable(self):
        for url in probe.OFFICIAL.values():
            self.assertEqual(probe._allowed(url),url)
        for url in ("http://www.baua.de/foo",
          "https://www.baua.de.evil.com/anything",
          "https://attacker@www.bgw-online.de/resource/blob/20628/a",
          "https://www.bgw-online.de:443/resource/blob/20628/a",
          "https://www.bgw-online.de/resource/blob/20628/different.pdf"):
            with self.assertRaises(probe.SourceFetchError):
                probe._allowed(url)

    def test_actual_synthetic_pdf_bytes_produce_non_release_digest_receipt(self):
        data=synthetic_pdf()
        result=probe.verify_pdf_bytes(data,
           requested_url=probe.OFFICIAL["BGW"],
           resolved_url=probe.OFFICIAL["BGW"])
        import hashlib
        self.assertEqual(result["source_document_sha256"],
           hashlib.sha256(data).hexdigest())
        self.assertEqual(result["pdf_pages"],15)
        self.assertFalse(result["rights_cleared"])
        self.assertEqual(result["expert_signatures_verified"],0)
        self.assertFalse(result["eng05_to_eng06_dispatch_authorized"])
        self.assertFalse(result["customer_release_approved"])

    def test_incomplete_pdf_html_pdf_mimic_or_wrong_edition_denied(self):
        url=probe.OFFICIAL["BAUA"]
        with self.assertRaises(probe.SourceFetchError):
            probe.verify_pdf_bytes(b"%PDF-" + b"x"*40000,
                                  requested_url=url,resolved_url=url)
        for kwargs in ({"pages":14,"identity":True},
                       {"pages":15,"identity":False}):
            data=synthetic_pdf(**kwargs)
            with self.assertRaises(probe.SourceFetchError):
                probe.verify_pdf_bytes(data,requested_url=url,resolved_url=url)

    def test_pinned_redirects_refuse_official_looking_evil_host(self):
        from urllib.request import Request
        opener=probe.BoundedRedirects()
        req=Request(probe.OFFICIAL["BGW"])
        with self.assertRaises(probe.SourceFetchError):
            opener.redirect_request(req,None,302,"redirect",{},
                "https://www.bgw-online.de.evil.com/example.pdf")

    def test_probe_transport_failure_has_no_hash_or_authority(self):
        with patch.object(probe,"download_one",side_effect=probe.SourceFetchError(
              "official_source_transport_unavailable")):
            result=probe.probe()
        self.assertEqual(result["verification_status"],"NO_VERIFIED_PDF_BYTES")
        self.assertIsNone(result["source_document_sha256"])
        self.assertFalse(result["source_bytes_verified"])
        self.assertEqual(len(result["attempts"]),2)
        self.assertFalse(result["eng05_to_eng06_dispatch_authorized"])


if __name__=="__main__":
    unittest.main()

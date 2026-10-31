"""Offline hostile-input checks for standalone TRGS530 source acquisition."""
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT=Path(__file__).resolve().parents[3]/"scripts/attest_eng05_trgs530_source.py"
spec=importlib.util.spec_from_file_location("abc_trgs530_provenance",SCRIPT)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class RemoteSourceAttestationTests(unittest.TestCase):
    def test_only_exact_https_allowlisted_sources_accepted(self):
        for original in [url for _,url in mod.SOURCES]:
            self.assertEqual(mod.check_url(original),original)
        for fake in ("http://www.baua.de/trgs.pdf",
                     "https://www.baua.de.evil.com/a.pdf",
                     "https://attacker@www.baua.de/a.pdf",
                     "https://www.baua.de:8443/a.pdf",
                     "https://other.gov.de/TRGS-530.pdf",
                     "https://www.bgw-online.de/#fraud"):
            with self.assertRaises(ValueError):
                mod.check_url(fake)

    def test_provenance_requires_exact_15_pages_title_and_2023(self):
        sample="TRGS 530 (Fassung 20.04.2023) Friseurhandwerk"
        self.assertTrue(mod.check_identity(sample,15))
        for sample_text,pages in (
             (sample,14),("TRGS 530 20.04.2023 Kosmetik",15),
             ("TRGS 530 Friseurhandwerk 20.04.2007",15),
             ("TRGS 500 Friseurhandwerk 20.04.2023",15)):
            with self.assertRaises(ValueError):
                mod.check_identity(sample_text,pages)

    def test_pdf_prefix_suffix_and_size_are_necessary(self):
        for bad in (b"%PDF-1.4",b"<html>"+b"x"*11000,
                    b"%PDF-1.4"+b"x"*12000,
                    b"x"*12000+b"%%EOF"):
            with self.assertRaises(ValueError):
                mod.inspect_pdf(bad)

    def test_sha_is_from_actual_supplied_bytes_not_url_or_summary(self):
        from hashlib import sha256
        raw=b"%PDF-1.7\n"+b"AUTHORITY-CI-BYTES"*900+b"\n%%EOF\n"
        def process(command,**kwargs):
            if command[0]=="pdfinfo":
                return SimpleNamespace(stdout="Pages:          15\n")
            if command[0]=="pdftotext":
                return SimpleNamespace(stdout="TRGS 530 (Fassung 20.04.2023) Friseurhandwerk")
            raise AssertionError("unexpected parser")
        with patch.object(mod.subprocess,"run",side_effect=process):
            report=mod.inspect_pdf(raw)
        self.assertEqual(report["sha256_actual_pdf_bytes"],sha256(raw).hexdigest())
        self.assertEqual(report["byte_count"],len(raw))
        self.assertEqual(report["page_count"],15)
        self.assertTrue(report["first_page_edition_verified"])

    def test_observed_bgw_hash_is_a_specific_real_file_not_a_generic_approval(self):
        import json
        root=Path(__file__).resolve().parents[3]
        record=json.loads((root/"governance/abc_eng05_trgs530_bgw_raw_pdf_provenance_2026-10-31.v1.review.json").read_text())
        sha=record["sha256_of_actual_bgw_pdf_bytes"]
        self.assertEqual(sha,mod.BGW_FIRST_VERIFIED_SHA256)
        self.assertEqual(record["downloaded_bytes"],741429)
        self.assertEqual(record["pdf_pages"],15)
        self.assertFalse(record["cross_host_pdf_byte_identity_proven"])
        self.assertFalse(record["professional_source_release_authorized"])
        self.assertFalse(record["eng05_to_eng06_dispatch_authorized"])
        self.assertFalse(record["individual_credential_verified"])
        self.assertIsNone(record["alternate_urls"][0]["binary_sha256"])

    def test_changed_bgw_mirror_bytes_are_rejected_even_if_title_matches(self):
        class Response:
            headers={"Content-Length":"11000","Content-Type":"application/pdf"}
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def geturl(self): return mod.SOURCES[2][1]
            def getcode(self): return 200
            def read(self,n): return b"%PDF-1.7\n"+b"x"*12000+b"%%EOF"
        class FakeOpener:
            def open(self,*args,**kwargs): return Response()
        with patch.object(mod.urllib.request,"build_opener",return_value=FakeOpener()):
            with patch.object(mod,"inspect_pdf",return_value={
               "sha256_actual_pdf_bytes":"0"*64,
               "byte_count":12014,"page_count":15,
               "first_page_edition_verified":True}):
                with self.assertRaisesRegex(ValueError,"bytes_changed"):
                    mod.acquire("BGW_OFFICIAL",mod.SOURCES[2][1])

    def test_missing_network_never_creates_fake_hash_or_authority(self):
        with patch.object(mod,"acquire",side_effect=OSError("CI test offline")):
            r=mod.run()
        self.assertEqual(r["status"],"BLOCKED_SOURCE_BYTES_UNAVAILABLE")
        self.assertFalse(r["original_pdf_hash_available"])
        self.assertEqual(r["verified_downloads"],[])
        self.assertEqual(len(r["attempts"]),3)
        self.assertFalse(r["legal_reuse_clearance"])
        self.assertEqual(r["real_specialist_signatures"],0)
        self.assertFalse(r["eng05_to_eng06_dispatch_authorized"])
        self.assertFalse(r["customer_release_approved"])

if __name__=="__main__":
    unittest.main()

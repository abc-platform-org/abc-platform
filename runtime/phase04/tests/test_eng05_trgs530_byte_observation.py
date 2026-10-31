"""Offline-only TRGS530 PDF hash observation; no licensed corpus or signed source."""
import copy
import hashlib
import json
import os
import tempfile
import unittest
import uuid
from datetime import datetime,timezone,timedelta
from pathlib import Path
from abc_foundation.eng05_professional_sources import SourceGovernanceError,canonical
from abc_foundation.eng05_first_source_acceptance import EXPECTED_CASE
from abc_foundation.eng05_trgs530_byte_observation import (
 ALLOWED_URLS,inspect_pdf_file,review_receipt_from_observation)

NOW=datetime(2026,10,31,16,0,tzinfo=timezone.utc)
SOURCE=sorted(ALLOWED_URLS)[0]
FAKE_PDF=(b"%PDF-1.7\n"+(b"%ABC-CI-NOT-AN-OFFICIAL-PDF\n"*60)+b"startxref\n0\n%%EOF\n")


class ByteObservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"source.pdf"
        self.path.write_bytes(FAKE_PDF)

    def inspect(self,**kwargs):
        return inspect_pdf_file(
          kwargs.get("pdf_path",self.path),
          source_url=kwargs.get("source_url",SOURCE),
          retrieved_at=kwargs.get("retrieved_at",NOW.isoformat()),
          now=kwargs.get("now",NOW))

    def test_actual_local_bytes_are_hashed_not_url_or_summary(self):
        obs=self.inspect()
        self.assertEqual(obs["raw_document_sha256"],hashlib.sha256(FAKE_PDF).hexdigest())
        self.assertEqual(obs["pdf_byte_size"],len(FAKE_PDF))
        self.assertEqual(obs["case_id"],EXPECTED_CASE)
        self.assertTrue(obs["header_eof_magic_present"])
        self.assertFalse(obs["pdf_full_parser_validated"])
        self.assertFalse(obs["byte_origin_independently_attested"])
        self.assertFalse(obs["commercial_ingestion_rights_approved"])
        self.assertFalse(obs["professional_reviewer_approved"])
        self.assertFalse(obs["eng05_to_eng06_dispatch_authorized"])
        self.assertFalse(obs["customer_release_approved"])

    def test_receipt_is_reproducible_and_non_authoritative(self):
        obs=self.inspect()
        receipt=review_receipt_from_observation(obs)
        self.assertEqual(receipt,review_receipt_from_observation(copy.deepcopy(obs)))
        self.assertFalse(receipt["professional_release_authorized"])
        self.assertFalse(receipt["eng05_to_eng06_dispatch_authorized"])
        self.assertEqual(receipt["legal_review_status"],"AWAITING_INDEPENDENT_LEGAL_OPINION")

    def test_reject_non_pdf_missing_eof_and_bogus_magic(self):
        for data in (b"https://www.baua.de"*80,b"NOT-A-PDF"*180,
                     b"%PDF-1.7\n"+b"x"*2000,
                     b"%PDF-3.2\n"+b"x"*1800+b"%%EOF"):
            self.path.write_bytes(data)
            with self.assertRaises(SourceGovernanceError):
                self.inspect()

    def test_reject_symlink_and_oversized_untrusted_path(self):
        alias=Path(self.tmp.name)/"symlink.pdf"
        alias.symlink_to(self.path)
        with self.assertRaises(SourceGovernanceError):
            self.inspect(pdf_path=alias)
        self.path.write_bytes(b"%PDF-1.7\n%%EOF")
        with self.assertRaises(SourceGovernanceError):
            self.inspect()
        with self.assertRaises(SourceGovernanceError):
            self.inspect(pdf_path=Path(self.tmp.name)/"does-not-exist.pdf")

    def test_reject_host_confusion_and_unsigned_timestamp(self):
        for url in ("https://www.baua.de.evil.invalid/foo",
                    "http://www.baua.de/DE/Angebote",
                    "https://www.baua.de/@attacker/pdf"):
            with self.assertRaises(SourceGovernanceError):
                self.inspect(source_url=url)
        with self.assertRaises(SourceGovernanceError):
            self.inspect(retrieved_at="2026-10-31T16:00:00")
        with self.assertRaises(SourceGovernanceError):
            self.inspect(retrieved_at=(NOW+timedelta(minutes=1)).isoformat())

    def test_forged_independent_attestation_rights_or_eng06_is_denied(self):
        good=self.inspect()
        for key in ("pdf_full_parser_validated","byte_origin_independently_attested",
                    "publisher_checksum_verified","current_version_independently_attested",
                    "commercial_ingestion_rights_approved","professional_reviewer_approved",
                    "eng05_runtime_ingestion_authorized","eng05_to_eng06_dispatch_authorized",
                    "customer_release_approved"):
            forged=copy.deepcopy(good)
            forged[key]=True
            with self.assertRaises(SourceGovernanceError):
                review_receipt_from_observation(forged)
        forged=copy.deepcopy(good)
        forged["new_approval_secret"]="CI"
        with self.assertRaises(SourceGovernanceError):
            review_receipt_from_observation(forged)


class ByteObservationPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin=os.environ.get("ABC_TEST_PG_ADMIN_DSN")
        cls.eng05=os.environ.get("ABC_TEST_PG_ENG05_LOGIN_DSN")
        if not cls.admin or not cls.eng05 or os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
            raise unittest.SkipTest("disposable PostgreSQL integration only")

    def setUp(self):
        import psycopg
        from abc_foundation.eng05_first_source_acceptance import EXPECTED_CASE
        self.case=EXPECTED_CASE
        self.url=next(iter(ALLOWED_URLS))
        raw=canonical({
         "case":self.case,"metadata":"CI not the original TRGS530 document",
         "version":"2023-04-20","scope":"DE employee occupational safety",
         "gate":"UNVERIFIED"})
        from pathlib import Path
        case_json=json.loads((Path(__file__).resolve().parents[3]/
           "governance/abc_eng05_trgs530_first_professional_source_intake.v1.review.json").read_text())
        doc=canonical(case_json)
        with psycopg.connect(self.admin) as con:
            con.execute("""INSERT INTO abc.eng05_external_document_acceptance_cases(
                case_id,jurisdiction,service_scope,technical_domain,
                normative_reference,official_edition,official_url,
                source_metadata_bytes,source_metadata_sha256)
                VALUES(%s,'DE','HAIR_COLOR',
                'SALON_EMPLOYEE_OCCUPATIONAL_CHEMICAL_SAFETY','TRGS 530',
                '2023-04-20',%s,%s,%s)
                ON CONFLICT(case_id) DO NOTHING""",
                (self.case,case_json["primary_url"],doc,
                 hashlib.sha256(doc).hexdigest()))
        self.observed_sha=hashlib.sha256(FAKE_PDF).hexdigest()

    def test_provenance_snapshot_requires_no_claimed_authentication(self):
        import psycopg
        from psycopg import errors
        body=canonical({
          "contract":"abc.eng05.pdf-byte-observation.v1.review",
          "case_id":self.case,"source":self.url,
          "sha256":self.observed_sha,
          "scope":"CI_INVALID_AS_OFFICIAL_DOCUMENT",
          "authorized":False,"synthetic_test_padding":"z"*420})
        key=uuid.uuid4()
        with psycopg.connect(self.admin) as con:
            con.execute("""INSERT INTO abc.eng05_trgs530_byte_observations(
              observation_id,case_id,claimed_source_url,
              observed_document_sha256,observed_pdf_bytes,
              observation_metadata_bytes,observation_metadata_sha256)
              VALUES(%s,%s,%s,%s,%s,%s,%s)""",
              (key,self.case,self.url,self.observed_sha,len(FAKE_PDF),
               body,hashlib.sha256(body).hexdigest()))
            row=con.execute("""SELECT status,byte_origin_independently_attested,
             legal_clearance_granted,specialist_signature_accepted,
             eng05_runtime_ingestion_authorized,eng06_dispatch_authorized
             FROM abc.eng05_trgs530_byte_observations WHERE observation_id=%s""",
             (key,)).fetchone()
            self.assertEqual(row,("HASH_OBSERVATION_PENDING_INDEPENDENT_PROVENANCE",
                False,False,False,False,False))
            with self.assertRaises(errors.InsufficientPrivilege):
                with con.transaction():
                    con.execute("""UPDATE abc.eng05_trgs530_byte_observations
                       SET byte_origin_independently_attested=true
                       WHERE observation_id=%s""",(key,))
            with self.assertRaises(errors.CheckViolation):
                with con.transaction():
                    con.execute("""INSERT INTO abc.eng05_trgs530_byte_observations(
                      observation_id,case_id,claimed_source_url,observed_document_sha256,
                      observed_pdf_bytes,observation_metadata_bytes,
                      observation_metadata_sha256,eng06_dispatch_authorized)
                      VALUES(%s,%s,%s,%s,%s,%s,%s,true)""",
                      (uuid.uuid4(),self.case,self.url,self.observed_sha,
                       len(FAKE_PDF),body,hashlib.sha256(body).hexdigest()))
        with psycopg.connect(self.eng05) as con:
            con.execute("SET LOCAL ROLE abc_eng05_worker")
            with self.assertRaises(errors.InsufficientPrivilege):
                con.execute("SELECT * FROM abc.eng05_trgs530_byte_observations")

    def test_force_rls_and_tampered_observation_metadata_denied(self):
        import psycopg
        from psycopg import errors
        raw=canonical({"metadata":"x"*510})
        with psycopg.connect(self.admin) as con:
            flags=con.execute("""SELECT relrowsecurity,relforcerowsecurity
                FROM pg_class WHERE oid='abc.eng05_trgs530_byte_observations'::regclass""").fetchone()
            self.assertEqual(flags,(True,True))
            with self.assertRaises(errors.CheckViolation):
                with con.transaction():
                    con.execute("""INSERT INTO abc.eng05_trgs530_byte_observations(
                       observation_id,case_id,claimed_source_url,
                       observed_document_sha256,observed_pdf_bytes,
                       observation_metadata_bytes,observation_metadata_sha256)
                       VALUES(%s,%s,%s,%s,1200,%s,%s)""",
                       (uuid.uuid4(),self.case,self.url,self.observed_sha,raw,"a"*64))


if __name__=="__main__":
    unittest.main()

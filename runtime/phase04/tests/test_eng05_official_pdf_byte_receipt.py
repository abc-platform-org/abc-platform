"""Tests for the first authentic official PDF SHA receipt; no authority upgrade."""
import copy
import hashlib
import json
import os
import unittest
import uuid
from pathlib import Path
from abc_foundation.eng05_professional_sources import canonical

ROOT=Path(__file__).resolve().parents[3]
CASE=json.loads((ROOT/"governance/abc_eng05_trgs530_first_professional_source_intake.v1.review.json").read_text())
RECEIPT=json.loads((ROOT/"governance/abc_eng05_trgs530_bgw_pdf_byte_receipt_2026-10-31.v1.review.json").read_text())
EXPECTED="356fc7d7ef4d4dc56ae687c72dfbf00d156b65ae494553f15f0060d7b46b5628"


class VerifiedPDFReceiptTests(unittest.TestCase):
    def test_actual_byte_hash_exact_and_not_metadata_digest(self):
        r=RECEIPT
        self.assertEqual(r["contract"],"abc.eng05.actual-source-byte-receipt.v1.review")
        self.assertEqual(r["case_id"],CASE["candidate_id"])
        self.assertEqual(r["raw_pdf_bytes_sha256"],EXPECTED)
        self.assertEqual(r["raw_pdf_byte_count"],741429)
        self.assertEqual(r["pdf_page_count"],15)
        self.assertNotEqual(r["raw_pdf_bytes_sha256"],hashlib.sha256(canonical(CASE)).hexdigest())
        self.assertEqual(r["retrieval_status"],"ACTUAL_SOURCE_BYTES_VERIFIED_BY_EPHEMERAL_CI")
        self.assertTrue(r["provenance"]["source_pdf_committed_to_repository"] is False)
        self.assertEqual(r["provenance"]["workflow_run_id"],41233336210)
        self.assertEqual(r["provenance"]["exact_code_commit_sha"],
                         "f7cb9609661ba829cc70b909f8d18d89cb4f5872")

    def test_technical_receipt_does_not_claim_license_expert_or_release(self):
        r=RECEIPT
        self.assertFalse(r["evidence_caveats"]["independently_publisher_signed_file_hash_verified"])
        self.assertFalse(r["evidence_caveats"]["licensing_and_commercial_ingestion_rights_cleared"])
        self.assertEqual(r["evidence_caveats"]["independently_qualified_specialist_reviewers"],0)
        self.assertEqual(r["evidence_caveats"]["professional_claims_accepted"],0)
        for flag in ("eng05_review_worker_connected",
                     "eng05_to_eng06_dispatch_authorized","customer_release_approved"):
            self.assertIs(r["acceptance"][flag],False)
        self.assertIsNone(CASE["source_pdf_sha256"])
        self.assertEqual(CASE["acceptance"]["overall_status"],
                        "CANDIDATE_ONLY_NOT_PROFESSIONALLY_APPROVED")


class VerifiedPDFReceiptPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin=os.environ.get("ABC_TEST_PG_ADMIN_DSN")
        cls.eng05=os.environ.get("ABC_TEST_PG_ENG05_LOGIN_DSN")
        if not cls.admin or not cls.eng05 or os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
            raise unittest.SkipTest("disposable PostgreSQL only")

    def _ensure_case(self,con):
        payload=canonical(CASE)
        con.execute("""INSERT INTO abc.eng05_external_document_acceptance_cases(
          case_id,jurisdiction,service_scope,technical_domain,
          normative_reference,official_edition,official_url,
          source_metadata_bytes,source_metadata_sha256)
          VALUES(%s,'DE','HAIR_COLOR',
          'SALON_EMPLOYEE_OCCUPATIONAL_CHEMICAL_SAFETY',
          'TRGS 530','2023-04-20',%s,%s,%s)
          ON CONFLICT(case_id) DO NOTHING""",(
            CASE["candidate_id"],CASE["primary_url"],payload,
            hashlib.sha256(payload).hexdigest()))

    def test_durable_authentic_hash_receipt_and_immutable_provenance(self):
        import psycopg
        from psycopg import errors
        receipt_bytes=canonical(RECEIPT)
        receipt_id=uuid.uuid4()
        with psycopg.connect(self.admin) as con:
            self._ensure_case(con)
            con.execute("""INSERT INTO abc.eng05_official_pdf_byte_receipts(
                receipt_id,case_id,source_edition,source_publisher,
                retrieved_source_url,source_pdf_sha256,source_size_bytes,
                pdf_page_count,verification_run_id,verification_commit_sha,
                receipt_metadata_bytes,receipt_metadata_sha256)
                VALUES(%s,%s,'TRGS530_FASSUNG_20_04_2023','BGW',%s,%s,
                %s,15,41233336210,%s,%s,%s)""",(
                receipt_id,RECEIPT["case_id"],RECEIPT["source_url"],
                EXPECTED,RECEIPT["raw_pdf_byte_count"],
                RECEIPT["provenance"]["exact_code_commit_sha"],
                receipt_bytes,hashlib.sha256(receipt_bytes).hexdigest()))
            row=con.execute("""SELECT source_pdf_sha256,source_size_bytes,
              source_commercial_rights_verified,specialist_review_verified,
              runtime_knowledge_ingestion_authorized,eng06_dispatch_authorized
              FROM abc.eng05_official_pdf_byte_receipts
              WHERE receipt_id=%s""",(receipt_id,)).fetchone()
            self.assertEqual(row,(EXPECTED,741429,False,False,False,False))
            original=con.execute("""SELECT source_document_sha256,review_state
              FROM abc.eng05_external_document_acceptance_cases
              WHERE case_id=%s""",(CASE["candidate_id"],)).fetchone()
            self.assertEqual(original,(None,"CANDIDATE_ONLY_NOT_PROFESSIONALLY_APPROVED"))
            with self.assertRaises(errors.InsufficientPrivilege):
                with con.transaction():
                    con.execute("""UPDATE abc.eng05_official_pdf_byte_receipts
                      SET specialist_review_verified=true WHERE receipt_id=%s""",
                      (receipt_id,))
            with self.assertRaises(errors.CheckViolation):
                with con.transaction():
                    con.execute("""INSERT INTO abc.eng05_official_pdf_byte_receipts(
                      receipt_id,case_id,source_edition,source_publisher,
                      retrieved_source_url,source_pdf_sha256,source_size_bytes,
                      pdf_page_count,verification_run_id,verification_commit_sha,
                      receipt_metadata_bytes,receipt_metadata_sha256,
                      eng06_dispatch_authorized)
                      VALUES(%s,%s,'TRGS530_FASSUNG_20_04_2023','BGW',
                      %s,%s,%s,15,41233336210,%s,%s,%s,true)""",(
                       uuid.uuid4(),CASE["candidate_id"],RECEIPT["source_url"],
                       EXPECTED,741429,RECEIPT["provenance"]["exact_code_commit_sha"],
                       receipt_bytes,hashlib.sha256(receipt_bytes).hexdigest()))
            attrs=con.execute("""SELECT relrowsecurity,relforcerowsecurity
              FROM pg_class WHERE oid='abc.eng05_official_pdf_byte_receipts'::regclass""").fetchone()
            self.assertEqual(attrs,(True,True))
        with psycopg.connect(self.eng05) as con:
            con.execute("SET LOCAL ROLE abc_eng05_worker")
            with self.assertRaises(errors.InsufficientPrivilege):
                con.execute("SELECT * FROM abc.eng05_official_pdf_byte_receipts")


if __name__=="__main__":
    unittest.main()

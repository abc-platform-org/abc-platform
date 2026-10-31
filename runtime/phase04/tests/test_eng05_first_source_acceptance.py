"""ABC ENG05: real public TRGS 530 source approval is NOT claimed by tests."""
import copy
import hashlib
import json
import os
import unittest
import uuid
from pathlib import Path
from abc_foundation.eng05_professional_sources import canonical,SourceGovernanceError
from abc_foundation.eng05_first_source_acceptance import (
  validate_first_source_case,local_pdf_evidence_hash,
  create_external_review_requests,REQUIRED_APPROVALS)

ROOT=Path(__file__).resolve().parents[3]
CASE_PATH=ROOT/"governance/abc_eng05_trgs530_first_professional_source_intake.v1.review.json"
SOURCE=json.loads(CASE_PATH.read_text())


class FirstSourceGovernanceTests(unittest.TestCase):
    def test_verified_official_reference_not_professionally_approved(self):
        v=validate_first_source_case(SOURCE)
        self.assertEqual(v["candidate_id"],SOURCE["candidate_id"])
        self.assertTrue(v["official_document"])
        self.assertFalse(v["original_pdf_bytes_verified"])
        self.assertFalse(v["legal_commercial_rights_cleared"])
        self.assertFalse(v["specialist_credential_verified"])
        self.assertFalse(v["eng05_to_eng06_dispatch_authorized"])
        self.assertEqual(v["professionally_released_facts"],[])

    def test_requests_cover_independent_human_checks_and_release_nothing(self):
        a=create_external_review_requests(SOURCE)
        self.assertEqual(tuple(r["approval_domain"] for r in a),REQUIRED_APPROVALS)
        self.assertEqual(len({r["case_sha256"] for r in a}),1)
        self.assertEqual(len(a),6)
        for r in a:
            self.assertEqual(r["approval_status"],"EXTERNAL_EVIDENCE_MISSING")
            self.assertFalse(r["grants_professional_facts"])
            self.assertFalse(r["eng06_dispatch_authorized"])

    def test_forged_source_pdf_digest_rejected(self):
        forged=copy.deepcopy(SOURCE)
        forged["source_pdf_sha256"]="0"*64
        with self.assertRaises(SourceGovernanceError):
            validate_first_source_case(forged)
        forged=copy.deepcopy(SOURCE)
        forged["source_byte_access"]="PDF_DOWNLOADED_CONFIRMED"
        with self.assertRaises(SourceGovernanceError):
            validate_first_source_case(forged)

    def test_false_rights_license_or_republication_denied(self):
        for field in ("commercial_reuse_cleared","machine_ingestion_rights_cleared",
                      "redistribution_rights_cleared"):
            forged=copy.deepcopy(SOURCE)
            forged["rights_provenance"][field]=True
            with self.assertRaises(SourceGovernanceError):
                validate_first_source_case(forged)
        forged=copy.deepcopy(SOURCE)
        forged["rights_provenance"]["rights_basis_evidence"]="ci-unverified"
        with self.assertRaises(SourceGovernanceError):
            validate_first_source_case(forged)

    def test_fake_reviewer_or_specialist_signature_denied(self):
        for field,value in (("reviewer_identity","unknown-test-person"),
                            ("individual_license_verified",True),
                            ("specialist_signed_claims",[{"fake":True}]),
                            ("independent_pinned_signing_root_sha256","f"*64)):
            forged=copy.deepcopy(SOURCE)
            forged["independent_professional_review"][field]=value
            with self.assertRaises(SourceGovernanceError):
                validate_first_source_case(forged)

    def test_runtime_and_eng06_cannot_be_enabled_by_metadata(self):
        for field in ("professional_claim_release_authorized",
                      "eng05_review_worker_connected",
                      "eng05_to_eng06_dispatch_authorized","customer_release_approved"):
            forged=copy.deepcopy(SOURCE)
            forged["acceptance"][field]=True
            with self.assertRaises(SourceGovernanceError):
                validate_first_source_case(forged)

    def test_scope_or_sections_or_client_formula_laundering_rejected(self):
        forged=copy.deepcopy(SOURCE)
        forged["professional_domain"]="PERSONALIZED_CLIENT_HAIR_COLOUR_RECIPE"
        with self.assertRaises(SourceGovernanceError):
            validate_first_source_case(forged)
        forged=copy.deepcopy(SOURCE)
        forged["excluded_use"].remove("dye_mix_formula_or_ratio")
        with self.assertRaises(SourceGovernanceError):
            validate_first_source_case(forged)
        forged=copy.deepcopy(SOURCE)
        forged["provenance_evidence"][1]["pdf_page"]=99
        with self.assertRaises(SourceGovernanceError):
            validate_first_source_case(forged)

    def test_actual_file_bytes_only_for_pdf_digest_never_authority(self):
        with self.assertRaises(SourceGovernanceError):
            local_pdf_evidence_hash(b"https://www.baua.de/test")
        with self.assertRaises(SourceGovernanceError):
            local_pdf_evidence_hash(b"URL"*200)
        sample=b"%PDF-1.7\n"+b"CI-NOT-A-REAL-TRGS530-PDF\n"*7
        result=local_pdf_evidence_hash(sample)
        self.assertEqual(result["source_document_sha256"],
          hashlib.sha256(sample).hexdigest())
        self.assertFalse(result["legal_use_authorized"])
        self.assertFalse(result["specialist_approved"])
        self.assertFalse(result["runtime_ingestion_authorized"])


class FirstSourcePostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin=os.environ.get("ABC_TEST_PG_ADMIN_DSN")
        cls.eng05=os.environ.get("ABC_TEST_PG_ENG05_LOGIN_DSN")
        if not cls.admin or not cls.eng05 or os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
            raise unittest.SkipTest("disposable PG CI fixture only")

    def test_insert_real_reference_metadata_not_unsigned_professional_approval(self):
        import psycopg
        from psycopg import errors
        raw=canonical(SOURCE)
        case_id=SOURCE["candidate_id"]
        with psycopg.connect(self.admin) as con:
            con.execute("""INSERT INTO abc.eng05_external_document_acceptance_cases(
                case_id,jurisdiction,service_scope,technical_domain,
                normative_reference,official_edition,official_url,
                source_metadata_bytes,source_metadata_sha256)
                VALUES(%s,'DE','HAIR_COLOR',
                'SALON_EMPLOYEE_OCCUPATIONAL_CHEMICAL_SAFETY',
                'TRGS 530','2023-04-20',%s,%s,%s)""",
                (case_id,SOURCE["primary_url"],raw,hashlib.sha256(raw).hexdigest()))
            status=con.execute("""SELECT review_state,source_document_sha256,
                  redistribution_rights_cleared,individual_specialist_license_verified,
                  human_professional_release_authorized,eng06_dispatch_authorized
                FROM abc.eng05_external_document_acceptance_cases WHERE case_id=%s""",
                (case_id,)).fetchone()
            self.assertEqual(status,(
                "CANDIDATE_ONLY_NOT_PROFESSIONALLY_APPROVED",None,
                 False,False,False,False))
            requests=create_external_review_requests(SOURCE)
            for request in requests:
                data=canonical(request)
                con.execute("""INSERT INTO abc.eng05_external_approval_requests(
                   request_id,case_id,approval_domain,request_metadata_bytes,
                   request_metadata_sha256)
                   VALUES(%s,%s,%s,%s,%s)""",
                   (uuid.uuid4(),case_id,request["approval_domain"],
                    data,hashlib.sha256(data).hexdigest()))
            self.assertEqual(con.execute("""SELECT count(*) FROM
                abc.eng05_external_approval_requests WHERE case_id=%s""",
                (case_id,)).fetchone()[0],6)
            with self.assertRaises(errors.InsufficientPrivilege):
                with con.transaction():
                    con.execute("""UPDATE abc.eng05_external_document_acceptance_cases
                      SET human_professional_release_authorized=true
                      WHERE case_id=%s""",(case_id,))
            with self.assertRaises(errors.CheckViolation):
                with con.transaction():
                    con.execute("""INSERT INTO abc.eng05_external_approval_requests(
                      request_id,case_id,approval_domain,request_metadata_bytes,
                      request_metadata_sha256,authorizes_eng06)
                      VALUES(%s,%s,'LEGAL_RIGHTS',%s,%s,true)""",
                      (uuid.uuid4(),case_id,canonical(requests[0]),
                       hashlib.sha256(canonical(requests[0])).hexdigest()))
        with psycopg.connect(self.eng05) as con:
            con.execute("SET LOCAL ROLE abc_eng05_worker")
            with self.assertRaises(errors.InsufficientPrivilege):
                con.execute("SELECT * FROM abc.eng05_external_document_acceptance_cases")

    def test_enforced_rls_and_untrusted_digest_rejection(self):
        import psycopg
        from psycopg import errors
        raw=canonical(SOURCE)
        with psycopg.connect(self.admin) as con:
            for t in ("eng05_external_document_acceptance_cases",
                      "eng05_external_approval_requests"):
                v=con.execute("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid=%s::regclass",
                    ("abc."+t,)).fetchone()
                self.assertEqual(v,(True,True))
            with self.assertRaises(errors.CheckViolation):
                with con.transaction():
                    con.execute("""INSERT INTO abc.eng05_external_document_acceptance_cases(
                        case_id,jurisdiction,service_scope,technical_domain,
                        normative_reference,official_edition,official_url,
                        source_metadata_bytes,source_metadata_sha256)
                        VALUES(%s,'DE','HAIR_COLOR',
                        'SALON_EMPLOYEE_OCCUPATIONAL_CHEMICAL_SAFETY',
                        'TRGS 530','2023-04-20',%s,%s,%s)""",
                        (SOURCE["candidate_id"],SOURCE["primary_url"],raw,"f"*64))


if __name__=="__main__":
    unittest.main()

"""ENG05 reconciliation tests: public official record is NOT a legal/expert grant."""
import copy
import hashlib
import json
import os
import unittest
import uuid
from pathlib import Path
from abc_foundation.eng05_professional_sources import canonical,SourceGovernanceError
from abc_foundation.eng05_external_evidence_reconciliation import (
    verify_reconciliation,EXPECTED_APPROVALS)

ROOT=Path(__file__).resolve().parents[3]
PACKET=json.loads((ROOT/"governance/abc_eng05_trgs530_external_evidence_reconciliation.v1.review.json").read_text())


class ReconciliationReviewTests(unittest.TestCase):
    def test_current_registered_edition_observed_but_not_professional(self):
        v=verify_reconciliation(PACKET)
        self.assertEqual(v["official_registry_current_edition_observed"],"2023-04-20")
        self.assertFalse(v["raw_document_sha256_verified"])
        self.assertFalse(v["legal_rights_cleared"])
        self.assertEqual(v["qualified_specialists_verified"],0)
        self.assertFalse(v["eng05_to_eng06_dispatch_authorized"])
        self.assertEqual(tuple(v["pending_approval_domains"]),tuple(EXPECTED_APPROVALS))

    def test_false_pdf_digest_or_claimed_download_is_denied(self):
        for field,value in (("document_sha256","f"*64),
                            ("verified_raw_file_bytes",True),
                            ("document_reuse_permitted",True),
                            ("response_headers_sha256","a"*64)):
            p=copy.deepcopy(PACKET)
            p["primary_pdf"][field]=value
            with self.assertRaises(SourceGovernanceError):
                verify_reconciliation(p)
        p=copy.deepcopy(PACKET)
        p["primary_pdf"]["execution_download_attempts"][0]["content_sha256"]="f"*64
        with self.assertRaises(SourceGovernanceError):
            verify_reconciliation(p)

    def test_registered_current_version_is_not_signed_amendment_proof(self):
        p=copy.deepcopy(PACKET)
        p["official_current_edition"]["independent_human_version_signoff"]=True
        with self.assertRaises(SourceGovernanceError):
            verify_reconciliation(p)
        p=copy.deepcopy(PACKET)
        p["official_current_edition"]["publication_edition"]="2026-04-20"
        with self.assertRaises(SourceGovernanceError):
            verify_reconciliation(p)

    def test_official_work_copyright_exception_not_automatic_licence(self):
        for key,value in (("written_professional_legal_opinion_received",True),
                          ("rights_holder_explicit_permission_received",True),
                          ("approved_use_modes",["COMMERCIAL_FULL_TEXT_RAG"])):
            p=copy.deepcopy(PACKET)
            p["legal_rights"][key]=value
            with self.assertRaises(SourceGovernanceError):
                verify_reconciliation(p)
        p=copy.deepcopy(PACKET)
        p["legal_rights"]["publisher_terms"]["actual_scope_of_copyright_exception"]="AUTHORIZED"
        with self.assertRaises(SourceGovernanceError):
            verify_reconciliation(p)

    def test_imaginary_professional_signatures_and_contact_reply_denied(self):
        for key,value in (("verified_personnel_count",1),
                          ("independent_signer_pinned",True),
                          ("accepted_signatures",1),
                          ("human_conflict_resolution_completed",True)):
            p=copy.deepcopy(PACKET)
            p["professional_credential"][key]=value
            with self.assertRaises(SourceGovernanceError):
                verify_reconciliation(p)
        p=copy.deepcopy(PACKET)
        p["contact_channels"][0]["message_status"]="RESPONSE_RECEIVED"
        with self.assertRaises(SourceGovernanceError):
            verify_reconciliation(p)

    def test_cannot_advance_eng05_or_eng06_or_approval_ledger(self):
        for key in ("professional_runtime_authorized",
                    "eng05_to_eng06_dispatch_authorized",
                    "customer_release_approved","external_messages_sent"):
            p=copy.deepcopy(PACKET)
            p[key]=True
            with self.assertRaises(SourceGovernanceError):
                verify_reconciliation(p)
        p=copy.deepcopy(PACKET)
        p["approval_ledger"]["SOURCE_BYTES"]="ACCEPTED"
        with self.assertRaises(SourceGovernanceError):
            verify_reconciliation(p)


class ReconciliationDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin=os.environ.get("ABC_TEST_PG_ADMIN_DSN")
        cls.eng05=os.environ.get("ABC_TEST_PG_ENG05_LOGIN_DSN")
        if not cls.admin or not cls.eng05 or os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
            raise unittest.SkipTest("isolated local PostgreSQL only")
        # A distinct test method may execute first; ensure the immutable
        # parent source-case exists before any FK/constraint negative tests.
        import psycopg
        case=json.loads((ROOT/"governance/abc_eng05_trgs530_first_professional_source_intake.v1.review.json").read_text())
        content=canonical(case)
        with psycopg.connect(cls.admin) as con:
            con.execute("""INSERT INTO abc.eng05_external_document_acceptance_cases(
              case_id,jurisdiction,service_scope,technical_domain,
              normative_reference,official_edition,official_url,
              source_metadata_bytes,source_metadata_sha256)
              VALUES(%s,'DE','HAIR_COLOR',
                'SALON_EMPLOYEE_OCCUPATIONAL_CHEMICAL_SAFETY',
                'TRGS 530','2023-04-20',%s,%s,%s)
              ON CONFLICT(case_id) DO NOTHING""",
              (case["candidate_id"],case["primary_url"],content,
               hashlib.sha256(content).hexdigest()))

    def test_immutable_provenance_sha_and_worker_denied(self):
        import psycopg
        from psycopg import errors
        case=json.loads((ROOT/"governance/abc_eng05_trgs530_first_professional_source_intake.v1.review.json").read_text())
        raw_case=canonical(case)
        packet=canonical(PACKET)
        key=str(uuid.uuid4())
        with psycopg.connect(self.admin) as con:
            con.execute("""INSERT INTO abc.eng05_external_document_acceptance_cases(
              case_id,jurisdiction,service_scope,technical_domain,
              normative_reference,official_edition,official_url,
              source_metadata_bytes,source_metadata_sha256)
              VALUES(%s,'DE','HAIR_COLOR',
              'SALON_EMPLOYEE_OCCUPATIONAL_CHEMICAL_SAFETY',
              'TRGS 530','2023-04-20',%s,%s,%s)
              ON CONFLICT(case_id) DO NOTHING""",
              (case["candidate_id"],case["primary_url"],
               raw_case,hashlib.sha256(raw_case).hexdigest()))
            con.execute("""INSERT INTO abc.eng05_external_evidence_reconciliations(
              evidence_id,case_id,checked_date,provenance_packet,
              provenance_sha256,public_register_state)
              VALUES(%s,%s,%s,%s,%s,'CURRENT_EDITION_PUBLICLY_OBSERVED_ONLY')""",
              (key,PACKET["case_id"],PACKET["checked_on_utc"],packet,
               hashlib.sha256(packet).hexdigest()))
            row=con.execute("""SELECT official_pdf_digest,
                 commercial_legal_rights_granted,independent_professional_identity_verified,
                 independent_specialist_signed_reviews,eng05_production_knowledge_authorized,
                 eng06_dispatch_authorized,evidence_approval_state
               FROM abc.eng05_external_evidence_reconciliations
               WHERE evidence_id=%s""",(key,)).fetchone()
            self.assertEqual(row,(None,False,False,0,False,False,"AWAITING_EXTERNAL_EVIDENCE"))
            with self.assertRaises(errors.InsufficientPrivilege):
                with con.transaction():
                    con.execute("""UPDATE abc.eng05_external_evidence_reconciliations
                      SET eng06_dispatch_authorized=true WHERE evidence_id=%s""",(key,))
        with psycopg.connect(self.eng05) as con:
            con.execute("SET LOCAL ROLE abc_eng05_worker")
            with self.assertRaises(errors.InsufficientPrivilege):
                con.execute("SELECT * FROM abc.eng05_external_evidence_reconciliations")
        with psycopg.connect(self.admin) as con:
            v=con.execute("""SELECT relrowsecurity,relforcerowsecurity
               FROM pg_class WHERE oid='abc.eng05_external_evidence_reconciliations'::regclass""").fetchone()
            self.assertEqual(v,(True,True))

    def test_digest_mismatch_or_false_approval_cannot_be_inserted(self):
        import psycopg
        from psycopg import errors
        raw=canonical(PACKET)
        with psycopg.connect(self.admin) as con:
            for field,value in (("provenance_sha256","0"*64),
                                ("eng05_production_knowledge_authorized",True),
                                ("eng06_dispatch_authorized",True)):
                with self.assertRaises(errors.CheckViolation):
                    with con.transaction():
                        attrs="provenance_sha256"
                        vals="%s"
                        params=[hashlib.sha256(raw).hexdigest()]
                        if field=="provenance_sha256":
                            params=["0"*64]
                        else:
                            attrs+=", "+field
                            vals+=", %s"
                            params.append(value)
                        statement=("INSERT INTO abc.eng05_external_evidence_reconciliations("
                          "evidence_id,case_id,checked_date,provenance_packet,"
                          +attrs+",public_register_state) VALUES(%s,%s,%s,%s,"
                          +vals+",'CURRENT_EDITION_PUBLICLY_OBSERVED_ONLY')")
                        con.execute(statement,(uuid.uuid4(),PACKET["case_id"],
                          PACKET["checked_on_utc"],raw,*params))


if __name__=="__main__":
    unittest.main()

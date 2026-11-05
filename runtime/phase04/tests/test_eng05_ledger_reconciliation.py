"""No migration-number reuse and no professional release through an offline observation."""
import hashlib
import json
import os
import unittest
import uuid
from pathlib import Path
from abc_foundation.eng05_professional_sources import canonical
from abc_foundation.staging_migrate import FILENAMES, planned_migrations

ROOT=Path(__file__).resolve().parents[3]
CASE=json.loads((ROOT/"governance/abc_eng05_trgs530_first_professional_source_intake.v1.review.json").read_text())
RECEIPT=json.loads((ROOT/"governance/abc_eng05_trgs530_bgw_pdf_byte_receipt_2026-10-31.v1.review.json").read_text())
BGW="https://www.bgw-online.de/resource/blob/20628/29cbf999ca5c2d91e741fa6964c6c619/trgs530-gefahrstoffe-friseurhandwerk-data.pdf"

class SchemaLineageTests(unittest.TestCase):
    def test_0029_canonical_digest_preserved_and_0030_additive(self):
        self.assertEqual(FILENAMES[28:30],(
            "0029_eng05_official_pdf_byte_receipts.sql",
            "0030_eng05_trgs530_byte_observations.sql"))
        self.assertEqual(len(planned_migrations()),len(FILENAMES))
        self.assertEqual(FILENAMES[30],"0031_a1_six_adapter_bridge_quarantine.sql")
        self.assertEqual(FILENAMES[31:],("0032_a2_g05_atomic_consent_replay_gate.sql",
                                         "0033_a2_g05_synthetic_certificate_revocation.sql"))
        self.assertEqual(RECEIPT["raw_pdf_bytes_sha256"],
          "356fc7d7ef4d4dc56ae687c72dfbf00d156b65ae494553f15f0060d7b46b5628")
        self.assertFalse(RECEIPT["acceptance"]["eng05_to_eng06_dispatch_authorized"])
        self.assertIsNone(CASE["source_pdf_sha256"])
        m=ROOT/"runtime/phase04/migrations/0030_eng05_trgs530_byte_observations.sql"
        sql=m.read_text()
        for required in ("FORCE ROW LEVEL SECURITY","BEFORE UPDATE OR DELETE",
                         "CHECK(eng06_dispatch_authorized=false)",
                         "CHECK(legal_clearance_granted=false)",
                         "CHECK(specialist_signature_accepted=false)"):
            self.assertIn(required,sql)

class DatabaseLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dsn=os.environ.get("ABC_TEST_PG_ADMIN_DSN")
        cls.worker=os.environ.get("ABC_TEST_PG_ENG05_LOGIN_DSN")
        if os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY" or not cls.dsn or not cls.worker:
            raise unittest.SkipTest("ephemeral PostgreSQL only")
    def test_immutable_untrusted_observation_and_eng06_denied(self):
        import psycopg
        from psycopg import errors
        data=canonical(CASE)
        meta=canonical({"case":CASE["candidate_id"],"description":"synthetic untrusted input",
                         "padding":"x"*600,"legal":False,"reviewed":False})
        digest=hashlib.sha256(meta).hexdigest()
        obs=uuid.uuid4()
        with psycopg.connect(self.dsn) as con:
            con.execute("""INSERT INTO abc.eng05_external_document_acceptance_cases(
              case_id,jurisdiction,service_scope,technical_domain,normative_reference,
              official_edition,official_url,source_metadata_bytes,source_metadata_sha256)
              VALUES(%s,'DE','HAIR_COLOR','SALON_EMPLOYEE_OCCUPATIONAL_CHEMICAL_SAFETY',
              'TRGS 530','2023-04-20',%s,%s,%s) ON CONFLICT(case_id) DO NOTHING""",
              (CASE["candidate_id"],CASE["primary_url"],data,hashlib.sha256(data).hexdigest()))
            con.execute("""INSERT INTO abc.eng05_trgs530_byte_observations(
              observation_id,case_id,claimed_source_url,observed_document_sha256,
              observed_pdf_bytes,observation_metadata_bytes,observation_metadata_sha256)
              VALUES(%s,%s,%s,%s,2048,%s,%s)""",
              (obs,CASE["candidate_id"],BGW,hashlib.sha256(b"synthetic-only").hexdigest(),meta,digest))
            row=con.execute("""SELECT status,byte_origin_independently_attested,
              legal_clearance_granted,specialist_signature_accepted,
              eng05_runtime_ingestion_authorized,eng06_dispatch_authorized
              FROM abc.eng05_trgs530_byte_observations WHERE observation_id=%s""",
              (obs,)).fetchone()
            self.assertEqual(row,("HASH_OBSERVATION_PENDING_INDEPENDENT_PROVENANCE",
                                  False,False,False,False,False))
            for t in ("eng05_official_pdf_byte_receipts","eng05_trgs530_byte_observations"):
                self.assertEqual(con.execute("""SELECT relrowsecurity,relforcerowsecurity
                    FROM pg_class WHERE oid=to_regclass(%s)""",("abc."+t,)).fetchone(),(True,True))
            with self.assertRaises(errors.InsufficientPrivilege):
                with con.transaction():
                    con.execute("DELETE FROM abc.eng05_trgs530_byte_observations WHERE observation_id=%s",(obs,))
            with self.assertRaises(errors.CheckViolation):
                with con.transaction():
                    con.execute("""INSERT INTO abc.eng05_trgs530_byte_observations(
                      observation_id,case_id,claimed_source_url,observed_document_sha256,
                      observed_pdf_bytes,observation_metadata_bytes,
                      observation_metadata_sha256,eng06_dispatch_authorized)
                      VALUES(%s,%s,%s,%s,2048,%s,%s,true)""",
                      (uuid.uuid4(),CASE["candidate_id"],BGW,
                       hashlib.sha256(b"bad-claim").hexdigest(),meta,digest))
            self.assertEqual(con.execute("""SELECT source_document_sha256,review_state
                FROM abc.eng05_external_document_acceptance_cases WHERE case_id=%s""",
                (CASE["candidate_id"],)).fetchone(),
                (None,"CANDIDATE_ONLY_NOT_PROFESSIONALLY_APPROVED"))
        with psycopg.connect(self.worker) as con:
            con.execute("SET LOCAL ROLE abc_eng05_worker")
            for t in ("eng05_official_pdf_byte_receipts","eng05_trgs530_byte_observations"):
                with self.assertRaises(errors.InsufficientPrivilege):
                    with con.transaction():
                        con.execute("SELECT * FROM abc."+t)

if __name__=="__main__":
    unittest.main()

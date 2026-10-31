"""Real schema integration: ENG05 append-only source/review, replay, RLS, ENG14.

Only ephemeral LOCAL_INTEGRATION_ONLY PostgreSQL; no external authority is asserted.
"""
import hashlib
import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone

class ProfessionalAuthorityDatabaseIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dsn=os.getenv("ABC_TEST_PG_ADMIN_DSN")
        if os.getenv("ABC_ENV")!="LOCAL_INTEGRATION_ONLY" or not cls.dsn:
            raise unittest.SkipTest("disposable PostgreSQL only")

    def test_real_source_and_review_tables_replay_and_immutable(self):
        import psycopg
        from psycopg import errors
        source_id="ci-"+uuid.uuid4().hex
        candidate=uuid.uuid4()
        review=uuid.uuid4()
        source_bytes=(b'{"synthetic":true,"professional_release":false,"padding":"' +
                      b'x'*128+b'"}')
        sha=hashlib.sha256(source_bytes).hexdigest()
        attestation=b'{"synthetic":true,"signature_verified":false,"padding":"' + b'y'*128+b'"}'
        with psycopg.connect(self.dsn) as con:
            con.execute("""INSERT INTO abc.eng05_professional_source_candidates
              (candidate_id,source_id,source_version,service_scope,source_sha256,
               source_bytes,source_type)
              VALUES(%s,%s,'1.0.0','HAIRCUT',%s,%s,'CI_SYNTHETIC_FIXTURE')""",
              (candidate,source_id,sha,source_bytes))
            con.execute("""INSERT INTO abc.eng05_professional_review_attestations
              (review_id,candidate_id,reviewer_id,credential_id,reviewed_source_sha256,
               decision,detached_signature_sha256,attestation)
              VALUES(%s,%s,%s,%s,%s,'REQUEST_REVISION',%s,%s)""",
              (review,candidate,"ci-reviewer-"+source_id,"ci-credential-"+source_id,
               sha,hashlib.sha256(attestation).hexdigest(),attestation))
            self.assertEqual(con.execute("""SELECT trust_state,
                professional_release_authorized,eng06_dispatch_authorized
                FROM abc.eng05_professional_source_candidates
                WHERE candidate_id=%s""",(candidate,)).fetchone(),
                ("UNVERIFIED_EXTERNAL_AUTHORITY",False,False))
            self.assertEqual(con.execute("""SELECT verification_state,authority_released
                FROM abc.eng05_professional_review_attestations
                WHERE review_id=%s""",(review,)).fetchone(),
                ("AWAITING_EXTERNAL_CREDENTIAL_ISSUER",False))
            with self.assertRaises(errors.UniqueViolation):
                with con.transaction():
                    con.execute("""INSERT INTO abc.eng05_professional_source_candidates
                        (candidate_id,source_id,source_version,service_scope,source_sha256,
                         source_bytes,source_type)
                        VALUES(%s,%s,'1.0.0','HAIRCUT',%s,%s,'CI_SYNTHETIC_FIXTURE')""",
                        (uuid.uuid4(),source_id,sha,source_bytes))
            with self.assertRaises(errors.InsufficientPrivilege):
                with con.transaction():
                    con.execute("""UPDATE abc.eng05_professional_review_attestations
                        SET decision='APPROVE' WHERE review_id=%s""",(review,))
            with self.assertRaises(errors.InsufficientPrivilege):
                with con.transaction():
                    con.execute("""DELETE FROM abc.eng05_professional_source_candidates
                        WHERE candidate_id=%s""",(candidate,))
            with self.assertRaises(errors.CheckViolation):
                with con.transaction():
                    con.execute("""INSERT INTO abc.eng05_professional_source_candidates
                        (candidate_id,source_id,source_version,service_scope,source_sha256,
                         source_bytes,source_type,eng06_dispatch_authorized)
                        VALUES(%s,%s,'2.0.0','HAIRCUT',%s,%s,'CI_SYNTHETIC_FIXTURE',true)""",
                        (uuid.uuid4(),source_id,sha,source_bytes))
            for name in ("eng05_professional_source_candidates",
                         "eng05_professional_review_attestations",
                         "eng05_professional_conflict_dossiers",
                         "eng14_v2_replay_ledger"):
                self.assertEqual(con.execute("""SELECT relrowsecurity,relforcerowsecurity
                    FROM pg_class WHERE oid=to_regclass(%s)""",
                    ("abc."+name,)).fetchone(),(True,True))
        worker=os.getenv("ABC_TEST_PG_ENG05_LOGIN_DSN")
        if worker:
            with psycopg.connect(worker) as con:
                with self.assertRaises(errors.InsufficientPrivilege):
                    with con.transaction():
                        con.execute("SELECT * FROM abc.eng05_professional_review_attestations")

    def test_eng14_real_replay_gate_rejects_untrusted_principal(self):
        import psycopg
        from psycopg import errors
        worker=os.getenv("ABC_TEST_PG_ENG05_LOGIN_DSN")
        if not worker:
            self.skipTest("dedicated ENG05 login absent")
        with psycopg.connect(worker) as con:
            with self.assertRaises(errors.InsufficientPrivilege):
                with con.transaction():
                    con.execute("""SELECT abc.eng14_claim_v2_jti(
                      %s,%s,%s,%s,%s)""",
                      ("ci-tenant","https://ci.invalid/issuer","abc-eng05",
                       uuid.uuid4(),datetime.now(timezone.utc)+timedelta(minutes=2)))

if __name__=="__main__":
    unittest.main()

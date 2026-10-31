"""ENG05 source qualification + independent Ed25519 specialist review tests.

All content and reviewers in these tests are fictitious. The in-memory
trust anchors NEVER authorize deployed salon guidance or ENG06 dispatch.
"""
import base64
import copy
import hashlib
import os
import unittest
import uuid
from datetime import datetime,timedelta,timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from abc_foundation.eng05_professional_sources import (
    CONTRACT,REVIEW_CONTRACT,SourceGovernanceError,adjudicate,
    canonical,digest,validate_document)

NOW=datetime(2026,10,31,12,0,tzinfo=timezone.utc)


class ProfessionalSourceContractTests(unittest.TestCase):
    def setUp(self):
        self.doc=self.document()
        self.keys={}
        self.trust={}

    @staticmethod
    def document(*,ident="ci.fake-publisher/source-0001",value="CI_ASSERTION_A",
                 scope="HAIR_COLOR",critical=False,kind="PROFESSIONAL_GUIDELINE",
                 expiration=30,uncertainty=None):
        return {
            "contract":CONTRACT,"source_id":ident,"version":"1.0.0",
            "source_type":kind,"publisher_id":"ci-fake-publisher",
            "submitted_by":"ci-original-author","scope":scope,
            "jurisdiction":"CI-NO-REAL_JURISDICTION",
            "publication_ref":"ci:fake-evidence-locator",
            "published_at":(NOW-timedelta(days=7)).isoformat(),
            "expires_at":(NOW+timedelta(days=expiration)).isoformat(),
            "license_ref":"ci:synthetic-distribution-only",
            "content_sha256":"a"*64,
            "claims":[{"claim_id":"ci-claim-a","topic":"ci-synthetic-topic",
                "applicability":"ci-synthetic-client-attribute",
                "assertion":value,"evidence_ref":"ci:fake-evidence-page-1",
                "evidence_sha256":"b"*64,"evidence_strength":"MODERATE",
                "safety_critical":critical,"uncertainty":uncertainty or []}]
        }

    def signer(self,reviewer,scope="HAIR_COLOR",expiry=60,verified=True):
        key=Ed25519PrivateKey.generate()
        cred="ci-credential-"+reviewer
        self.keys[reviewer]=key
        self.trust[cred]={
            "reviewer_id":reviewer,"credential_status":"VERIFIED" if verified else "REVOKED",
            "scopes":[scope],
            "valid_from":(NOW-timedelta(days=3)).isoformat(),
            "valid_until":(NOW+timedelta(days=expiry)).isoformat(),
            "public_key":key.public_key(),
            "authority_attested":True}
        return cred

    def approve(self,doc,reviewer,decision="APPROVE",scope="HAIR_COLOR"):
        cred=self.signer(reviewer,scope=scope)
        data={
            "contract":REVIEW_CONTRACT,"source_sha256":digest(doc),
            "reviewer_id":reviewer,"credential_id":cred,
            "issued_at":NOW.isoformat(),"decision":decision,
            "reviewed_claim_ids":[c["claim_id"] for c in doc["claims"]],
            "conflict_of_interest":False,"signature_alg":"Ed25519"}
        signature=self.keys[reviewer].sign(canonical(data))
        return {**data,"signature_b64":base64.b64encode(signature).decode()}

    def test_contract_is_versioned_and_hash_stable(self):
        output=validate_document(self.doc,now=NOW)
        self.assertEqual(output["document_sha256"],digest(self.doc))
        self.assertFalse(output["expired"])
        self.assertFalse(output["synthetic"])
        self.assertEqual(canonical(self.doc),canonical(copy.deepcopy(self.doc)))

    def test_no_anchor_denies_approval_and_no_review_blocks(self):
        result=adjudicate([self.doc],[],now=NOW)
        self.assertEqual(result["review_gate"],"BLOCKED_QUALIFICATION")
        self.assertIn("SPECIALIST_APPROVAL_REQUIRED",result["unknowns"])
        self.assertFalse(result["eng05_to_eng06_dispatch_authorized"])
        self.assertEqual(result["professionally_released_facts"],[])
        fake=self.approve(self.doc,"ci-reviewer-one")
        with self.assertRaises(SourceGovernanceError):
            adjudicate([self.doc],[fake],trusted_credentials={},now=NOW)

    def test_signed_independent_review_only_not_operational_release(self):
        review=self.approve(self.doc,"ci-reviewer-one")
        result=adjudicate([self.doc],[review],trusted_credentials=self.trust,now=NOW)
        self.assertEqual(result["review_gate"],"REVIEWED_NON_EXECUTABLE")
        self.assertEqual(result["review_candidate_count"],1)
        self.assertEqual(result["professionally_released_facts"],[])
        self.assertFalse(result["professional_runtime_authorized"])
        self.assertFalse(result["customer_release_approved"])

    def test_safety_critical_requires_two_distinct_independent_reviews(self):
        self.doc["claims"][0]["safety_critical"]=True
        one=self.approve(self.doc,"ci-reviewer-one")
        blocked=adjudicate([self.doc],[one],trusted_credentials=self.trust,now=NOW)
        self.assertEqual(blocked["review_gate"],"BLOCKED_QUALIFICATION")
        self.assertEqual(blocked["sources"][0]["required_independent_reviewers"],2)
        two=self.approve(self.doc,"ci-reviewer-two")
        ready=adjudicate([self.doc],[one,two],trusted_credentials=self.trust,now=NOW)
        self.assertEqual(ready["review_gate"],"REVIEWED_NON_EXECUTABLE")
        self.assertFalse(ready["eng05_to_eng06_dispatch_authorized"])

    def test_two_reviewer_ids_sharing_one_signing_key_never_count_as_two(self):
        from cryptography.hazmat.primitives import serialization
        self.doc["claims"][0]["safety_critical"]=True
        a=self.approve(self.doc,"ci-reviewer-one")
        b=self.approve(self.doc,"ci-reviewer-two")
        self.trust[b["credential_id"]]["public_key"]=self.keys[
            "ci-reviewer-one"].public_key()
        signed={k:v for k,v in b.items() if k!="signature_b64"}
        b["signature_b64"]=base64.b64encode(self.keys[
            "ci-reviewer-one"].sign(canonical(signed))).decode()
        with self.assertRaises(SourceGovernanceError):
            adjudicate([self.doc],[a,b],trusted_credentials=self.trust,now=NOW)

    def test_signed_approval_does_not_cover_modified_document(self):
        review=self.approve(self.doc,"ci-reviewer-one")
        tampered=copy.deepcopy(self.doc)
        tampered["claims"][0]["assertion"]="INVENTED"
        with self.assertRaises(SourceGovernanceError):
            adjudicate([tampered],[review],trusted_credentials=self.trust,now=NOW)

    def test_bad_signature_and_replay_reviewer_denied(self):
        review=self.approve(self.doc,"ci-reviewer-one")
        invalid=dict(review)
        invalid["signature_b64"]=base64.b64encode(b"0"*64).decode()
        with self.assertRaises(SourceGovernanceError):
            adjudicate([self.doc],[invalid],trusted_credentials=self.trust,now=NOW)
        with self.assertRaises(SourceGovernanceError):
            adjudicate([self.doc],[review,review],trusted_credentials=self.trust,now=NOW)

    def test_revoked_expired_out_of_scope_credential_denied(self):
        review=self.approve(self.doc,"ci-reviewer-one")
        self.trust[review["credential_id"]]["credential_status"]="REVOKED"
        with self.assertRaises(SourceGovernanceError):
            adjudicate([self.doc],[review],trusted_credentials=self.trust,now=NOW)
        self.trust[review["credential_id"]]["credential_status"]="VERIFIED"
        self.trust[review["credential_id"]]["scopes"]=["NAILS"]
        with self.assertRaises(SourceGovernanceError):
            adjudicate([self.doc],[review],trusted_credentials=self.trust,now=NOW)
        self.trust[review["credential_id"]]["scopes"]=["HAIR_COLOR"]
        self.trust[review["credential_id"]]["valid_until"]=(NOW-timedelta(days=1)).isoformat()
        with self.assertRaises(SourceGovernanceError):
            adjudicate([self.doc],[review],trusted_credentials=self.trust,now=NOW)

    def test_submitter_and_publisher_cannot_sign_own_source(self):
        for reviewer in ("ci-original-author","ci-fake-publisher"):
            self.trust={}
            review=self.approve(self.doc,reviewer)
            with self.assertRaises(SourceGovernanceError):
                adjudicate([self.doc],[review],trusted_credentials=self.trust,now=NOW)

    def test_rejection_blocks_even_when_another_qualified_reviewer_approves(self):
        a=self.approve(self.doc,"ci-reviewer-one")
        b=self.approve(self.doc,"ci-reviewer-two",decision="REJECT")
        result=adjudicate([self.doc],[a,b],trusted_credentials=self.trust,now=NOW)
        self.assertEqual(result["review_gate"],"BLOCKED_QUALIFICATION")
        self.assertIn("SPECIALIST_REJECTED_OR_REVISION_REQUIRED",result["unknowns"])

    def test_conflicting_sources_do_not_rank_or_silently_pick_newest(self):
        other=self.document(ident="ci.another-publisher/source-2",
                            value="CI_CONTRADICTORY_ASSERTION",critical=True)
        a=self.approve(self.doc,"ci-reviewer-one")
        b=self.approve(other,"ci-reviewer-two")
        c=self.approve(other,"ci-reviewer-three")
        result=adjudicate([self.doc,other],[a,b,c],
                          trusted_credentials=self.trust,now=NOW)
        self.assertEqual(result["review_gate"],"BLOCKED_CONFLICT")
        self.assertIn("SAFETY_CRITICAL_CONFLICT",result["unknowns"])
        self.assertEqual(result["conflicts"][0]["state"],"UNRESOLVED")
        self.assertEqual(result["conflicts"][0]["severity"],"SAFETY_CRITICAL")
        self.assertEqual(result["professionally_released_facts"],[])

    def test_expired_source_never_qualifies_even_signed(self):
        self.doc=self.document(expiration=-1)
        r=self.approve(self.doc,"ci-reviewer-one")
        result=adjudicate([self.doc],[r],trusted_credentials=self.trust,now=NOW)
        self.assertIn("SOURCE_EXPIRED",result["unknowns"])
        self.assertEqual(result["review_gate"],"BLOCKED_QUALIFICATION")

    def test_synthetic_source_never_becomes_professionally_qualified(self):
        self.doc=self.document(kind="CI_SYNTHETIC_FIXTURE")
        r=self.approve(self.doc,"ci-reviewer-one")
        result=adjudicate([self.doc],[r],trusted_credentials=self.trust,now=NOW)
        self.assertIn("CI_SYNTHETIC_NOT_PROFESSIONAL",result["unknowns"])
        self.assertEqual(result["review_gate"],"BLOCKED_QUALIFICATION")

    def test_uncertain_claim_is_never_released_as_grounded_fact(self):
        self.doc=self.document(uncertainty=["CONTEXT_MISSING"])
        r=self.approve(self.doc,"ci-reviewer-one")
        result=adjudicate([self.doc],[r],trusted_credentials=self.trust,now=NOW)
        self.assertIn("EVIDENCE_UNCERTAIN",result["unknowns"])
        self.assertEqual(result["review_candidate_count"],0)
        self.assertEqual(result["professionally_released_facts"],[])

    def test_extra_fields_missing_evidence_and_version_malformed_denied(self):
        for field,value in (("version","1x0x0"),("content_sha256","f"*63),
                            ("scope","UNSCOPED"),("publisher_id","")):
            bad=copy.deepcopy(self.doc)
            bad[field]=value
            with self.assertRaises(SourceGovernanceError):
                validate_document(bad,now=NOW)
        bad=copy.deepcopy(self.doc)
        bad["claims"][0]["claim_id"]="x"
        with self.assertRaises(SourceGovernanceError):
            validate_document(bad,now=NOW)
        bad=copy.deepcopy(self.doc)
        bad["unrecognized_recommendation"]="never accepted"
        with self.assertRaises(SourceGovernanceError):
            validate_document(bad,now=NOW)


class ProfessionalSourcePostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin=os.environ.get("ABC_TEST_PG_ADMIN_DSN")
        cls.eng05=os.environ.get("ABC_TEST_PG_ENG05_LOGIN_DSN")
        if not cls.admin or not cls.eng05 or os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
            raise unittest.SkipTest("isolated CI PostgreSQL only")

    def test_immutable_candidate_and_review_dossiers_no_engine_dml(self):
        import psycopg
        from psycopg import errors
        doc=ProfessionalSourceContractTests.document(kind="CI_SYNTHETIC_FIXTURE")
        data=canonical(doc)
        sha=hashlib.sha256(data).hexdigest()
        ident=str(uuid.uuid4())
        with psycopg.connect(self.admin) as con:
            con.execute("""INSERT INTO abc.eng05_professional_source_candidates(
                candidate_id,source_id,source_version,service_scope,
                source_sha256,source_bytes,source_type)
                VALUES(%s,%s,%s,%s,%s,%s,%s)""",(
                  ident,doc["source_id"],doc["version"],doc["scope"],sha,data,
                  doc["source_type"]))
            review_id=str(uuid.uuid4())
            att=canonical({"contract":REVIEW_CONTRACT,
                   "source_sha256":sha,"reviewer_id":"ci-disposable-not-professional",
                   "decision":"REQUEST_REVISION","signature":"ci-not-attested"})
            con.execute("""INSERT INTO abc.eng05_professional_review_attestations(
                review_id,candidate_id,reviewer_id,credential_id,
                reviewed_source_sha256,decision,detached_signature_sha256,attestation)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
                (review_id,ident,"ci-disposable-not-professional",
                 "ci-disposable-no-issuer",sha,"REQUEST_REVISION",
                 hashlib.sha256(att).hexdigest(),att))
            for tbl,col,val in (
                 ("eng05_professional_source_candidates","candidate_id",ident),
                 ("eng05_professional_review_attestations","review_id",review_id)):
                self.assertEqual(con.execute(
                    "SELECT count(*) FROM abc."+tbl+" WHERE "+col+"=%s",
                    (val,)).fetchone()[0],1)
                with self.assertRaises(errors.InsufficientPrivilege):
                    with con.transaction():
                        con.execute("UPDATE abc."+tbl+
                          " SET inserted_at=clock_timestamp() WHERE "+col+"=%s",(val,))
            row=con.execute("""SELECT trust_state,professional_release_authorized,
                eng06_dispatch_authorized FROM abc.eng05_professional_source_candidates
                WHERE candidate_id=%s""",(ident,)).fetchone()
            self.assertEqual(row,("UNVERIFIED_EXTERNAL_AUTHORITY",False,False))
            attested=con.execute("""SELECT verification_state,authority_released
                FROM abc.eng05_professional_review_attestations
                WHERE review_id=%s""",(review_id,)).fetchone()
            self.assertEqual(attested,("AWAITING_EXTERNAL_CREDENTIAL_ISSUER",False))
        with psycopg.connect(self.eng05) as con:
            con.execute("SET LOCAL ROLE abc_eng05_worker")
            with self.assertRaises(errors.InsufficientPrivilege):
                con.execute("SELECT * FROM abc.eng05_professional_source_candidates")
        with psycopg.connect(self.admin) as con:
            for table in ("eng05_professional_source_candidates",
                  "eng05_professional_review_attestations",
                  "eng05_professional_conflict_dossiers"):
                result=con.execute("""SELECT relrowsecurity,relforcerowsecurity
                    FROM pg_class WHERE oid=%s::regclass""",
                    ("abc."+table,)).fetchone()
                self.assertEqual(result,(True,True))

    def test_conflict_dossier_is_immutable_and_never_dispatchable(self):
        import psycopg
        from psycopg import errors
        a=ProfessionalSourceContractTests.document(
            ident="ci.fake-publisher/source-x",value="CI_ASSERTION_A")
        b=ProfessionalSourceContractTests.document(
            ident="ci.other-publisher/source-y",value="CI_CONTRADICTORY_B",critical=True)
        dossier=adjudicate([a,b],[],now=NOW)
        self.assertEqual(dossier["review_gate"],"BLOCKED_CONFLICT")
        data=canonical(dossier)
        source_set=digest(sorted([digest(a),digest(b)]))
        key=str(uuid.uuid4())
        with psycopg.connect(self.admin) as con:
            con.execute("""INSERT INTO abc.eng05_professional_conflict_dossiers(
                 dossier_id,source_set_sha256,dossier_bytes,dossier_sha256,status)
                 VALUES(%s,%s,%s,%s,%s)""",(
                  key,source_set,data,hashlib.sha256(data).hexdigest(),
                  dossier["review_gate"]))
            row=con.execute("""SELECT status,eng06_release_authorized
                FROM abc.eng05_professional_conflict_dossiers
                WHERE dossier_id=%s""",(key,)).fetchone()
            self.assertEqual(row,("BLOCKED_CONFLICT",False))
            with self.assertRaises(errors.InsufficientPrivilege):
                with con.transaction():
                    con.execute("""UPDATE abc.eng05_professional_conflict_dossiers
                      SET status='REVIEWED_NON_EXECUTABLE' WHERE dossier_id=%s""",(key,))
            with self.assertRaises(errors.InsufficientPrivilege):
                with con.transaction():
                    con.execute("""DELETE FROM abc.eng05_professional_conflict_dossiers
                      WHERE dossier_id=%s""",(key,))

    def test_wrong_digest_and_attempt_to_promote_are_denied(self):
        import psycopg
        from psycopg import errors
        doc=ProfessionalSourceContractTests.document(kind="CI_SYNTHETIC_FIXTURE")
        raw=canonical(doc)
        with psycopg.connect(self.admin) as con:
            with self.assertRaises(errors.CheckViolation):
                with con.transaction():
                    con.execute("""INSERT INTO abc.eng05_professional_source_candidates(
                        candidate_id,source_id,source_version,service_scope,
                        source_sha256,source_bytes,source_type)
                        VALUES(%s,%s,'1.0.0','HAIR_COLOR',%s,%s,'CI_SYNTHETIC_FIXTURE')""",
                        (uuid.uuid4(),"ci.bad-digest/"+uuid.uuid4().hex,"0"*64,raw))
            with self.assertRaises(errors.CheckViolation):
                with con.transaction():
                    con.execute("""INSERT INTO abc.eng05_professional_source_candidates(
                        candidate_id,source_id,source_version,service_scope,
                        source_sha256,source_bytes,source_type,professional_release_authorized)
                        VALUES(%s,%s,'1.0.0','HAIR_COLOR',%s,%s,
                          'CI_SYNTHETIC_FIXTURE',true)""",
                        (uuid.uuid4(),"ci.bad-release/"+uuid.uuid4().hex,
                         hashlib.sha256(raw).hexdigest(),raw))


if __name__=="__main__":
    unittest.main()

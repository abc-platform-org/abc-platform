"""ENG05 external issuer discovery, detached signature and negative DB tests.

Ephemeral issuer keys and specialists here are CI fixtures, not real licences.
"""
import base64
import copy
import hashlib
import json
import os
import unittest
import uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from abc_foundation.eng05_professional_sources import SourceGovernanceError,canonical,digest
from abc_foundation.eng05_external_authority import (
    ISSUER_CONTRACT,validate_discovery_catalog,verify_external_credential_manifest,
    review_only_external_dossier)
from test_eng05_professional_sources import ProfessionalSourceContractTests,NOW

ROOT=Path(__file__).resolve().parents[3]
CATALOG=json.loads((ROOT/"governance/abc_eng05_hair_color_eu_official_references.v1.review.json").read_text())


class ExternalAuthoritySignatureTests(unittest.TestCase):
    def setUp(self):
        self.fixture=ProfessionalSourceContractTests()
        self.fixture.setUp()
        self.issuer=Ed25519PrivateKey.generate()
        self.root=self.issuer.public_key().public_bytes(
           encoding=serialization.Encoding.Raw,
           format=serialization.PublicFormat.Raw)
        self.root_b64=base64.b64encode(self.root).decode()
        self.pin=hashlib.sha256(self.root).hexdigest()

    def _packet(self,*,reviewers=("ci-reviewer-one",),scope="HAIR_COLOR"):
        rows=[]
        for reviewer in reviewers:
            credential=self.fixture.signer(reviewer,scope=scope)
            anchor=self.fixture.trust[credential]
            raw=anchor["public_key"].public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw)
            rows.append({
              "credential_id":credential,"reviewer_id":reviewer,
              "credential_status":"VERIFIED","scopes":[scope],"jurisdiction":"EU",
              "valid_from":anchor["valid_from"],"valid_until":anchor["valid_until"],
              "reviewer_public_key_b64":base64.b64encode(raw).decode(),
              "verification_ref":"https://single-market-economy.ec.europa.eu/single-market/services/free-movement-professionals/database-regulated-professions_en",
              "independent_verifier_ref":"https://www.gesetze-im-internet.de/hwo/BJNR014110953.html"})
        manifest={
         "contract":ISSUER_CONTRACT,"issuer_id":"ci-fake-external-credential-issuer",
         "version":"1.0.0","issued_at":NOW.isoformat(),
         "expires_at":(NOW+timedelta(days=7)).isoformat(),
         "jurisdiction":"EU","credential_records":rows,
         "revoked_credentials":[],"signature_alg":"Ed25519"}
        return self._sign(manifest)

    def _sign(self,payload):
        return {**payload,"signature_b64":
            base64.b64encode(self.issuer.sign(canonical(payload))).decode()}

    def verify(self,packet,**kwargs):
        return verify_external_credential_manifest(packet,
            trusted_root_key_b64=kwargs.get("root",self.root_b64),
            independently_pinned_root_sha256=kwargs.get("pin",self.pin),
            now=kwargs.get("now",NOW))

    def test_curated_real_eu_urls_are_only_unverified_discovery(self):
        result=validate_discovery_catalog(CATALOG)
        self.assertEqual(result["references_identified"],3)
        self.assertEqual(result["qualified_source_documents"],0)
        self.assertEqual(result["credential_issuers_connected"],0)
        self.assertFalse(result["release_authorized"])
        self.assertEqual(len(CATALOG["professional_credential_authority_refs"]),2)

    def test_reference_url_confusion_and_false_approval_fail_closed(self):
        for url in (
            "http://single-market-economy.ec.europa.eu/fake",
            "https://single-market-economy.ec.europa.eu.evil.com/hair",
            "https://attacker:password@echa.europa.eu/evil",
            "https://echa.europa.eu:443/evil",
        ):
            bad=copy.deepcopy(CATALOG)
            bad["references"][0]["url"]=url
            with self.assertRaises(SourceGovernanceError):
                validate_discovery_catalog(bad)
        for key,value in (
            ("license_to_copy_verified",True),
            ("raw_document_sha256","f"*64),
            ("expert_verified",True),
            ("status","PROFESSIONALLY_APPROVED"),
        ):
            bad=copy.deepcopy(CATALOG)
            bad["references"][0][key]=value
            with self.assertRaises(SourceGovernanceError):
                validate_discovery_catalog(bad)
        bad=copy.deepcopy(CATALOG)
        bad["eng05_to_eng06_dispatch_authorized"]=True
        with self.assertRaises(SourceGovernanceError):
            validate_discovery_catalog(bad)

    def test_issuer_root_pinned_out_of_band_and_signed_manifest(self):
        packet=self._packet()
        result=self.verify(packet)
        self.assertEqual(result["qualifying_user_records_count"],1)
        self.assertFalse(result["professional_runtime_authorized"])
        self.assertFalse(result["eng05_to_eng06_dispatch_authorized"])
        with self.assertRaises(SourceGovernanceError):
            self.verify(packet,pin="0"*64)
        fake=Ed25519PrivateKey.generate()
        raw=fake.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw)
        with self.assertRaises(SourceGovernanceError):
            self.verify(packet,root=base64.b64encode(raw).decode())

    def test_injected_credential_or_tampered_signature_denied(self):
        packet=self._packet()
        tampered=copy.deepcopy(packet)
        tampered["credential_records"][0]["credential_status"]="VERIFIED"
        tampered["credential_records"][0]["reviewer_id"]="ci-fraud-reviewer"
        with self.assertRaises(SourceGovernanceError):
            self.verify(tampered)
        tampered=copy.deepcopy(packet)
        tampered["signature_b64"]=base64.b64encode(b"x"*64).decode()
        with self.assertRaises(SourceGovernanceError):
            self.verify(tampered)

    def test_revocation_and_expired_roster_deny_qualified_anchors(self):
        packet=self._packet()
        original={k:v for k,v in packet.items() if k!="signature_b64"}
        revoked=copy.deepcopy(original)
        revoked["revoked_credentials"]=[
            revoked["credential_records"][0]["credential_id"]]
        receipt=self.verify(self._sign(revoked))
        self.assertEqual(receipt["qualifying_user_records_count"],0)
        with self.assertRaises(SourceGovernanceError):
            self.verify(packet,now=NOW+timedelta(days=9))
        invalid=copy.deepcopy(original)
        invalid["revoked_credentials"]=["unknown-ci-credential"]
        with self.assertRaises(SourceGovernanceError):
            self.verify(self._sign(invalid))

    def test_duplicate_credential_ids_and_scope_denied(self):
        packet=self._packet()
        payload={k:v for k,v in packet.items() if k!="signature_b64"}
        dup=copy.deepcopy(payload)
        dup["credential_records"].append(copy.deepcopy(dup["credential_records"][0]))
        with self.assertRaises(SourceGovernanceError):
            self.verify(self._sign(dup))
        wrong=copy.deepcopy(payload)
        wrong["credential_records"][0]["scopes"]=["SKIN_BEAUTY"]
        with self.assertRaises(SourceGovernanceError):
            self.verify(self._sign(wrong))

    def test_genuinely_signed_ci_issuer_and_specialist_still_no_real_release(self):
        doc=self.fixture.doc
        credential=self.fixture.signer("ci-reviewer-one")
        review=self.fixture.approve(doc,"ci-reviewer-one")
        # approve() creates a new key, therefore create the issuer packet only
        # after creating the detached review with the final reviewer key.
        packet=self._issuer_for_existing(("ci-reviewer-one",))
        dossier=review_only_external_dossier(
            [doc],[review],packet,
            trusted_root_key_b64=self.root_b64,
            independently_pinned_root_sha256=self.pin,now=NOW)
        self.assertEqual(dossier["review_gate"],"REVIEWED_NON_EXECUTABLE")
        self.assertEqual(dossier["professionally_released_facts"],[])
        self.assertFalse(dossier["eng05_to_eng06_dispatch_authorized"])
        self.assertFalse(dossier["professional_runtime_authorized"])

    def _issuer_for_existing(self,reviewers):
        records=[]
        for reviewer in reviewers:
            cred="ci-credential-"+reviewer
            a=self.fixture.trust[cred]
            raw=a["public_key"].public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw)
            records.append({
              "credential_id":cred,"reviewer_id":reviewer,
              "credential_status":"VERIFIED",
              "scopes":a["scopes"],"jurisdiction":"EU",
              "valid_from":a["valid_from"],"valid_until":a["valid_until"],
              "reviewer_public_key_b64":base64.b64encode(raw).decode(),
              "verification_ref":"https://single-market-economy.ec.europa.eu/single-market/services/free-movement-professionals/database-regulated-professions_en",
              "independent_verifier_ref":"https://www.gesetze-im-internet.de/hwo/BJNR014110953.html"})
        return self._sign({
          "contract":ISSUER_CONTRACT,"issuer_id":"ci-fake-external-credential-issuer",
          "version":"1.0.0","issued_at":NOW.isoformat(),
          "expires_at":(NOW+timedelta(days=7)).isoformat(),
          "jurisdiction":"EU","credential_records":records,
          "revoked_credentials":[],"signature_alg":"Ed25519"})


class ExternalRegistryPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin=os.environ.get("ABC_TEST_PG_ADMIN_DSN")
        cls.eng05=os.environ.get("ABC_TEST_PG_ENG05_LOGIN_DSN")
        if not cls.admin or not cls.eng05 or os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
            raise unittest.SkipTest("disposable PostgreSQL CI only")

    def test_official_url_reference_immutable_and_not_engine_readable(self):
        import psycopg
        from psycopg import errors
        reference=CATALOG["references"][0]
        metadata=canonical(reference)
        sha=hashlib.sha256(metadata).hexdigest()
        with psycopg.connect(self.admin) as con:
            con.execute("""INSERT INTO abc.eng05_official_reference_discovery(
                reference_id,scope,jurisdiction,publisher,source_url,
                reference_sha256,reference_bytes)
                VALUES(%s,'HAIR_COLOR','EU',%s,%s,%s,%s)""",(
                  reference["reference_id"],reference["publisher"],reference["url"],
                  sha,metadata))
            result=con.execute("""SELECT documentation_state,source_bytes_verified,
                republication_rights_verified,specialist_approved,engagement_authorized
                FROM abc.eng05_official_reference_discovery WHERE reference_id=%s""",
                (reference["reference_id"],)).fetchone()
            self.assertEqual(result,("REFERENCE_ONLY",False,False,False,False))
            with self.assertRaises(errors.InsufficientPrivilege):
                with con.transaction():
                    con.execute("""UPDATE abc.eng05_official_reference_discovery
                        SET specialist_approved=true WHERE reference_id=%s""",
                        (reference["reference_id"],))
        with psycopg.connect(self.eng05) as con:
            con.execute("SET LOCAL ROLE abc_eng05_worker")
            with self.assertRaises(errors.InsufficientPrivilege):
                con.execute("SELECT * FROM abc.eng05_official_reference_discovery")
        with psycopg.connect(self.admin) as con:
            for name in ("eng05_official_reference_discovery",
                         "eng05_external_issuer_review_packets"):
                v=con.execute("""SELECT relrowsecurity,relforcerowsecurity
                   FROM pg_class WHERE oid=%s::regclass""",
                   ("abc."+name,)).fetchone()
                self.assertEqual(v,(True,True))

    def test_unsigned_real_world_authority_not_accepted_by_db(self):
        import psycopg
        from psycopg import errors
        content=canonical({"issuer_id":"ci-not-real","status":"PENDING",
                          "public_source":"EU_DISCOVERY_ONLY"})
        with psycopg.connect(self.admin) as con:
            con.execute("""INSERT INTO abc.eng05_external_issuer_review_packets(
                packet_id,issuer_id,issuer_manifest_sha256,issuer_manifest_bytes,
                submitted_signature,issuer_public_key_fingerprint)
                VALUES(%s,%s,%s,%s,%s,%s)""",
                (uuid.uuid4(),"ci-not-real",hashlib.sha256(content).hexdigest(),
                 content,b"z"*64,"f"*64))
            row=con.execute("""SELECT external_authority_verified,
                professional_signoff_accepted,eng06_release_authorized
                FROM abc.eng05_external_issuer_review_packets
                WHERE issuer_id='ci-not-real'""").fetchone()
            self.assertEqual(row,(False,False,False))
            with self.assertRaises(errors.CheckViolation):
                with con.transaction():
                    con.execute("""INSERT INTO abc.eng05_external_issuer_review_packets(
                        packet_id,issuer_id,issuer_manifest_sha256,issuer_manifest_bytes,
                        submitted_signature,issuer_public_key_fingerprint,
                        professional_signoff_accepted)
                        VALUES(%s,%s,%s,%s,%s,%s,true)""",
                        (uuid.uuid4(),"ci-not-real",hashlib.sha256(content).hexdigest(),
                         content,b"z"*64,"f"*64))
            with self.assertRaises(errors.CheckViolation):
                with con.transaction():
                    con.execute("""INSERT INTO abc.eng05_external_issuer_review_packets(
                        packet_id,issuer_id,issuer_manifest_sha256,issuer_manifest_bytes,
                        submitted_signature,issuer_public_key_fingerprint,
                        eng06_release_authorized)
                        VALUES(%s,%s,%s,%s,%s,%s,true)""",
                        (uuid.uuid4(),"ci-not-real",hashlib.sha256(content).hexdigest(),
                         content,b"z"*64,"f"*64))


if __name__=="__main__":
    unittest.main()

"""Signed independent review evidence cannot self-authorize product release."""
import unittest
import uuid
from datetime import datetime,timezone
from types import SimpleNamespace

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from abc_foundation.independent_signoff_gate import IndependentSignoffEvidenceGate
from abc_foundation.store import DomainError


class _Keys:
    def __init__(self,public):self.public=public
    def get_signing_key_from_jwt(self,token):
        return SimpleNamespace(key=self.public)


class IndependentSignoffTests(unittest.TestCase):
    def setUp(self):
        self.keys={}
        self.issuers={}
        authorities={}
        for kind in ("professional","security"):
            private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
            issuer="https://"+kind+".abc-ci.example"
            self.keys[kind]=private
            self.issuers[kind]=issuer
            authorities[kind]={
                "issuer":issuer,"jwks_uri":issuer+"/.well-known/jwks.json",
                "jwks_client":_Keys(private.public_key())
            }
        self.gate=IndependentSignoffEvidenceGate(authorities=authorities)
        self.head="a"*40
        self.digest="b"*64
        self.scope="ABC_PHASE04_SYNTHETIC_PRIVATE_STAGING"

    def token(self,kind,**changes):
        now=int(datetime.now(timezone.utc).timestamp())
        claims={"iss":self.issuers[kind],
            "aud":"abc-phase04-signoff:"+kind,
            "iat":now,"nbf":now,"exp":now+300,"jti":str(uuid.uuid4()),
            "sub":"reviewer-"+kind+"-external",
            "reviewer_role":kind.upper(),
            "decision":"APPROVED","head_sha":self.head,
            "evidence_digest":self.digest,"scope":self.scope,
            "approval_id":str(uuid.uuid4())}
        if kind=="professional":
            claims.update(qualification_ref="professional-registry:ci",
                          sop_version="signed-sop-ci")
        else:
            claims.update(security_review_ref="security-review:ci")
        claims.update(changes)
        return jwt.encode(claims,self.keys[kind],algorithm="RS256",
                          headers={"kid":"ci-test-only"})

    def run_gate(self,tokens):
        return self.gate.evaluate(tokens=tokens,head_sha=self.head,
            evidence_digest=self.digest,scope=self.scope)

    def test_absent_signatures_block_release(self):
        r=self.run_gate(None)
        self.assertFalse(r["release_approved"])
        self.assertEqual(r["verified_signoffs"],0)

    def test_distinct_signed_reviews_are_evidence_not_release_authority(self):
        r=self.run_gate({"professional":self.token("professional"),
                         "security":self.token("security")})
        self.assertEqual(r["verified_signoffs"],2)
        self.assertEqual(len(r["review_ids"]),2)
        self.assertFalse(r["release_approved"])

    def test_expired_rejected_wrong_scope_and_unqualified_review_all_fail(self):
        for kind in ("professional","security"):
            examples=[
                {"head_sha":"c"*40},
                {"scope":"ABC_PRODUCTION"},
                {"evidence_digest":"d"*64},
                {"exp":int(datetime.now(timezone.utc).timestamp())-200},
                {"reviewer_role":"SYSTEM"},
                {"decision":"CONDITIONALLY_APPROVED"},
            ]
            if kind=="professional":examples.append({"qualification_ref":""})
            if kind=="security":examples.append({"security_review_ref":""})
            for extra in examples:
                tokens={"professional":self.token("professional"),
                        "security":self.token("security")}
                tokens[kind]=self.token(kind,**extra)
                with self.subTest(kind=kind,change=extra),self.assertRaises(DomainError):
                    self.run_gate(tokens)

    def test_same_person_cannot_fill_professional_and_security_roles(self):
        person="same-operator-subject"
        tokens={"professional":self.token("professional",sub=person),
                "security":self.token("security",sub=person)}
        with self.assertRaises(DomainError):
            self.run_gate(tokens)

    def test_wrong_issuer_signature_rejected(self):
        tokens={"professional":self.token("security"),
                "security":self.token("security")}
        with self.assertRaises(DomainError):
            self.run_gate(tokens)

    def test_production_scope_never_accepted(self):
        with self.assertRaises(DomainError):
            self.gate.evaluate(tokens=None,head_sha=self.head,
                evidence_digest=self.digest,scope="ABC_PRODUCTION")

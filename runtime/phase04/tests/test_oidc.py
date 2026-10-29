"""Asymmetric OIDC tests: keys generated inside test process; no third-party live IdP."""
import time
import unittest
from types import SimpleNamespace

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from abc_foundation.oidc import OIDCVerifier, IdentityError, Principal

ISS = "https://identity.example.test/realms/abc"
AUD = "abc-api"
URI = "https://identity.example.test/realms/abc/protocol/openid-connect/certs"

class StaticJWKS:
    def __init__(self, public): self.public = public
    def get_signing_key_from_jwt(self, token):
        h = jwt.get_unverified_header(token)
        if h.get("kid") != "p04-test-rsa":
            raise jwt.PyJWKClientError("unknown_kid")
        return SimpleNamespace(key=self.public)

class OIDCTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.verifier = OIDCVerifier(issuer=ISS, audience=AUD, jwks_uri=URI,
                                   jwks_client=StaticJWKS(cls.private.public_key()))

    def token(self, *, sign=None, header=None, **override):
        now = int(time.time())
        claims = {"iss": ISS, "aud": AUD, "sub": "specialist-1",
                  "iat": now - 2, "nbf": now - 2, "exp": now + 300,
                  "roles": ["ORG_OWNER"], "tenant_id": "attacker-tenant",
                  "branch_ids": ["attacker-branch"]}
        claims.update(override)
        return jwt.encode(claims, sign or self.private, algorithm="RS256",
                          headers=header or {"kid": "p04-test-rsa"})

    def test_valid_rs256_returns_identity_not_claimed_authority(self):
        p = self.verifier.verify("Bearer "+self.token())
        self.assertEqual(p, Principal("specialist-1", ISS))
        self.assertFalse(hasattr(p, "roles"))
        self.assertFalse(hasattr(p, "tenant_id"))

    def test_wrong_audience_denied(self):
        with self.assertRaises(IdentityError):
            self.verifier.verify("Bearer "+self.token(aud="elsewhere"))

    def test_wrong_issuer_denied(self):
        with self.assertRaises(IdentityError):
            self.verifier.verify("Bearer "+self.token(iss="https://evil.example.test/"))

    def test_expired_denied(self):
        with self.assertRaises(IdentityError):
            self.verifier.verify("Bearer "+self.token(exp=int(time.time())-100))

    def test_future_nbf_denied(self):
        with self.assertRaises(IdentityError):
            self.verifier.verify("Bearer "+self.token(nbf=int(time.time())+600))

    def test_wrong_key_denied(self):
        bad = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        with self.assertRaises(IdentityError):
            self.verifier.verify("Bearer "+self.token(sign=bad))

    def test_unknown_key_id_denied(self):
        with self.assertRaises(IdentityError):
            self.verifier.verify("Bearer "+self.token(header={"kid":"no-such-key"}))

    def test_no_kid_denied(self):
        with self.assertRaises(IdentityError):
            self.verifier.verify("Bearer "+self.token(header={"typ":"JWT","kid":""}))

    def test_required_claim_absent_denied(self):
        tok = self.token(sub=None)
        with self.assertRaises(IdentityError):
            self.verifier.verify("Bearer "+tok)

    def test_non_bearer_denied(self):
        with self.assertRaises(IdentityError):
            self.verifier.verify("Basic abc")

    def test_jwks_ssrf_host_restriction(self):
        with self.assertRaises(ValueError):
            OIDCVerifier(issuer=ISS, audience=AUD, jwks_uri="https://attacker.test/jwks")
        with self.assertRaises(ValueError):
            OIDCVerifier(issuer=ISS, audience=AUD, jwks_uri="http://identity.example.test/jwks")
        with self.assertRaises(ValueError):
            OIDCVerifier(issuer=ISS, audience=AUD, jwks_uri="https://identity.example.test@attacker.test/jwks")

    def test_hs256_algorithm_confusion_denied(self):
        tok = jwt.encode({"iss":ISS,"aud":AUD,"sub":"a","exp":int(time.time())+300},
                         "malicious",algorithm="HS256",headers={"kid":"p04-test-rsa"})
        with self.assertRaises(IdentityError):
            self.verifier.verify("Bearer "+tok)

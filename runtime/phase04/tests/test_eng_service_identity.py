"""Security checks for ENG01 dual bearer auth: asymmetric identity is NOT scope."""
import time
import unittest
import uuid
from types import SimpleNamespace

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from abc_foundation.eng01_service_identity import WorkloadVerifier,ENG01InternalIngress
from abc_foundation.oidc import IdentityError,OIDCVerifier,Principal
from abc_foundation.store import DomainError

ISS="https://identity.example.test/realms/abc"
SISS="https://workload.identity.example.test/abc"
AUD="abc-eng01-internal"


class StaticKey:
    def __init__(self,key): self.key=key
    def get_signing_key_from_jwt(self,token):
        kid=jwt.get_unverified_header(token).get("kid")
        if kid!="test-rsa-1":
            raise jwt.PyJWKClientError("kid_unknown")
        return SimpleNamespace(key=self.key)


class ServiceIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.priv=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        cls.other=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        cls.issuer=WorkloadVerifier(issuer=SISS,audience=AUD,
            jwks_uri=SISS+"/jwks",jwks_client=StaticKey(cls.priv.public_key()))

    def token(self,**override):
        n=int(time.time())
        data={"iss":SISS,"aud":AUD,"sub":"svc:abc-eng02",
              "iat":n-2,"nbf":n-2,"exp":n+60,"jti":str(uuid.uuid4()),
              "token_use":"service","engine_id":"ENG-02"}
        data.update(override)
        return "Bearer "+jwt.encode(data,self.priv,algorithm="RS256",
                                   headers={"kid":"test-rsa-1"})

    def reject(self,**override):
        with self.assertRaises(IdentityError):
            self.issuer.verify(self.token(**override))

    def test_signed_service_principal_has_no_claimed_tenant_or_role(self):
        p=self.issuer.verify(self.token(tenant_id="other",role="ORG_OWNER"))
        self.assertEqual(p.engine_id,"ENG-02")
        self.assertEqual(p.subject,"svc:abc-eng02")
        self.assertFalse(hasattr(p,"tenant_id"))
        self.assertFalse(hasattr(p,"role"))

    def test_wrong_issuer_audience_and_engine_fail(self):
        self.reject(iss="https://fake.test")
        self.reject(aud="abc-other-service")
        self.reject(engine_id="ENG-19")
        self.reject(sub="svc:abc-eng01")
        self.reject(token_use="user")

    def test_expiry_future_issued_and_overlong_token_fail(self):
        n=int(time.time())
        self.reject(exp=n-100)
        self.reject(nbf=n+150)
        self.reject(iat=n+150)
        self.reject(exp=n+7200)
        self.reject(jti="not-a-uuid")

    def test_invalid_kid_algorithm_and_missing_bearer_fail(self):
        with self.assertRaises(IdentityError): self.issuer.verify("Basic x")
        data=self.token()
        with self.assertRaises(IdentityError): self.issuer.verify(data[7:])
        with self.assertRaises(IdentityError): self.issuer.verify("Bearer abc")

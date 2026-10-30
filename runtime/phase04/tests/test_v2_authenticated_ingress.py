"""Local only: never mistake injected test fixtures for real external identity."""
import os
import uuid
import unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch

from abc_foundation.eng01_v2_authenticated_ingress import ScopedV2Ingress
from abc_foundation.store import DomainError
from test_engine_v2_contracts import request


class FakeVerifiedIdentity:
    def __init__(self,patches=None):
        self.patches=patches or {}
    def verify(self,token,cert,*,expected_engine,expected_consumer):
        if token!="SIGNED_TEST_ONLY" or cert!=b"CA_VERIFIED_DER_TEST_ONLY":
            raise DomainError(401,"mutual_workload_authentication_failed")
        return {"verified":True,"engine_id":expected_engine,
            "consumer_id":expected_consumer,
            "issuer":"https://issuer.abc.example.test",
            "audience":"abc-engine:ENG-04",
            "token_id":str(uuid.uuid4()),
            "cert_sha256":"a"*64,
            "expires_at":datetime.now(timezone.utc)+timedelta(seconds=90),
            **self.patches}

class FakeScopeAuthority:
    def __init__(self,allowed=True):self.allowed=allowed
    def verify(self,**claims):
        return (self.allowed and claims["tenant_id"]=="tenant-test"
            and claims["state_version"]==2
            and claims["target_engine"]=="ENG-04"
            and claims["caller_engine"]=="ENG-03"
            and claims["certificate_sha256"]=="a"*64)

class RecordingReplay:
    def __init__(self):self.calls=[];self.ids=set()
    def claim(self,**kwargs):
        self.calls.append(kwargs)
        jti=kwargs["jti"]
        if jti in self.ids:
            raise DomainError(409,"distributed_replay_detected")
        self.ids.add(jti)
        return {"admitted":True}


class V2AuthenticatedIngressTests(unittest.TestCase):
    def setUp(self):
        self.patch=patch.dict(os.environ,{"ABC_ENV":"LOCAL_INTEGRATION_ONLY"})
        self.patch.start();self.addCleanup(self.patch.stop)
        self.replay=RecordingReplay()

    def ingress(self,identity=None,scope=None):
        return ScopedV2Ingress(identity_verifier=identity or FakeVerifiedIdentity(),
            scope_authority=scope or FakeScopeAuthority(),
            replay_ledger=self.replay,caller_engine="ENG-03",
            consumer_id="test-worker")

    def submit(self,ingress,req=None,**patches):
        data={"message":req or request("ENG-04"),
              "token":"SIGNED_TEST_ONLY",
              "verified_peer_certificate_der":b"CA_VERIFIED_DER_TEST_ONLY"}
        data.update(patches)
        return ingress.submit(**data)

    def test_approved_scoped_local_request_reaches_eng04_only(self):
        output=self.submit(self.ingress())
        self.assertEqual(output["result"]["status"],"DRAFT_FOR_SPECIALIST_REVIEW")
        self.assertFalse(output["execution_authorized"])
        self.assertEqual(len(self.replay.calls),1)
        self.assertEqual(self.replay.calls[0]["tenant_id"],"tenant-test")
        self.assertEqual(self.replay.calls[0]["issuer"],"https://issuer.abc.example.test")

    def test_policy_denial_happens_before_replay_claim(self):
        with self.assertRaisesRegex(DomainError,"v2_session_policy_scope_denied"):
            self.submit(self.ingress(scope=FakeScopeAuthority(False)))
        self.assertEqual(self.replay.calls,[])

    def test_no_browser_supplied_tenant_or_scope_can_authorize(self):
        req=request("ENG-04")
        req["tenant_id"]="tenant-other"
        with self.assertRaisesRegex(DomainError,"v2_session_policy_scope_denied"):
            self.submit(self.ingress(),req)
        self.assertEqual(self.replay.calls,[])

    def test_invalid_cert_or_untrusted_proof_fails_closed(self):
        for kwargs in (
            {"token":"UNTRUSTED"},
            {"verified_peer_certificate_der":b"BAD_PEER_DER"},
            {"verified_peer_certificate_der":b""},
        ):
            with self.subTest(kwargs=kwargs),self.assertRaises(DomainError):
                self.submit(self.ingress(),**kwargs)
        for claim in ({"verified":False},{"consumer_id":"other"},
                      {"cert_sha256":None},{"token_id":None},
                      {"expires_at":datetime.now(timezone.utc).replace(tzinfo=None)}):
            with self.subTest(claim=claim),self.assertRaises(DomainError):
                self.submit(self.ingress(identity=FakeVerifiedIdentity(claim)))

    def test_persistent_jti_reuse_rejected(self):
        shared=str(uuid.uuid4())
        auth=self.ingress(identity=FakeVerifiedIdentity({"token_id":shared}))
        self.submit(auth)
        with self.assertRaisesRegex(DomainError,"distributed_replay_detected"):
            self.submit(auth)

    def test_real_workload_staging_not_enabled_by_local_gates(self):
        with patch.dict(os.environ,{"ABC_ENV":"STAGING_PRIVATE"}):
            with self.assertRaisesRegex(DomainError,"v2_live_dispatch_requires_separate_review"):
                self.submit(self.ingress())
        self.assertEqual(self.replay.calls,[])

    def test_missing_external_authorities_refused(self):
        with self.assertRaises(ValueError):
            ScopedV2Ingress(identity_verifier=None,scope_authority=FakeScopeAuthority(),
                replay_ledger=self.replay,caller_engine="ENG-03",
                consumer_id="test-worker")


if __name__=="__main__":
    unittest.main()

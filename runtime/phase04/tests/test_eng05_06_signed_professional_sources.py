"""Detached cryptographic professional sources: test keys are ephemeral only.

No real salon specialist credentials or approvals are created by these tests.
"""
import base64
import copy
import json
import os
import unittest
from datetime import datetime,timezone
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat

from abc_foundation.professional_sources_v2 import (
    ProfessionalSourceRegistry,SignedKnowledgePolicyGate,SignedSOPConsentGate)
from abc_foundation.engine_v2_runtime import execute
from test_engine_v2_contracts import request

NOW=datetime(2026,10,30,12,0,0,tzinfo=timezone.utc)
REF="synthetic:catalog-entry"
SOP="synthetic:unreleased-sop"


class SignedProfessionalSourceTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{"ABC_ENV":"LOCAL_INTEGRATION_ONLY"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.private=Ed25519PrivateKey.generate()
        self.pub=self.private.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
        self.entries={}
        self.reviewers={"specialist-test-reviewer":{
            "issuer_id":"test-professional-issuer",
            "service_kinds":["HAIR_COLOR"],
            "review_types":["KNOWLEDGE","SOP"],
            "qualification_valid_until":"2027-06-01T00:00:00Z"}}
        self.add_record(REF,"KNOWLEDGE","draft-v2","a"*64)
        self.add_record(SOP,"SOP","v2-sop-1","c"*64)

    def add_record(self,ref,kind,version,digest,expires="2027-02-01T00:00:00Z"):
        record={"record_ref":ref,"record_type":kind,"service_kind":"HAIR_COLOR",
           "version":version,"content_digest":digest,
           "reviewer_id":"specialist-test-reviewer",
           "issuer_id":"test-professional-issuer",
           "not_before":"2026-01-01T00:00:00Z",
           "expires_at":expires,
           "review_scope":"ABC_SPECIALIST_SERVICE_SOURCE_V1",
           "status":"ACTIVE"}
        canonical=json.dumps(record,sort_keys=True,separators=(",",":")).encode()
        self.entries[ref]={"record":record,"signature_b64":base64.b64encode(
            self.private.sign(canonical)).decode()}

    def registry(self,**changes):
        return ProfessionalSourceRegistry(
            pinned_public_keys=changes.get("keys",{"test-professional-issuer":self.pub}),
            qualified_reviewers=changes.get("reviewers",self.reviewers),
            signed_records=changes.get("entries",self.entries),
            revoked_refs=changes.get("revoked",()),
            clock=changes.get("clock",lambda:NOW))

    def test_registry_positive_exact_signature_digest_and_scope(self):
        reg=self.registry()
        self.assertTrue(reg.verify(ref=REF,record_type="KNOWLEDGE",
            service_kind="HAIR_COLOR",version="draft-v2",digest="a"*64))
        self.assertTrue(reg.verify(ref=SOP,record_type="SOP",
            service_kind="HAIR_COLOR"))
        self.assertFalse(reg.verify(ref=SOP,record_type="KNOWLEDGE",
            service_kind="HAIR_COLOR"))
        self.assertFalse(reg.verify(ref=REF,record_type="KNOWLEDGE",
            service_kind="SKIN",version="draft-v2",digest="a"*64))

    def test_tampered_content_fake_signature_and_unknown_issuer_denied(self):
        for mutation in ("wrong_digest","wrong_reviewer","bad_signature",
                         "revoked","wrong_pin","unqualified","expired"):
            entries=copy.deepcopy(self.entries)
            reviewers=copy.deepcopy(self.reviewers)
            keys={"test-professional-issuer":self.pub}
            revoked=[]
            clock=lambda:NOW
            if mutation=="wrong_digest":
                entries[REF]["record"]["content_digest"]="b"*64
            if mutation=="wrong_reviewer":
                entries[REF]["record"]["reviewer_id"]="untrusted-specialist"
            if mutation=="bad_signature":
                entries[REF]["signature_b64"]="AAAAAAAAAAAAAAAAAAAAAA=="
            if mutation=="revoked":
                revoked=[REF]
            if mutation=="wrong_pin":
                other=Ed25519PrivateKey.generate()
                keys={"test-professional-issuer":other.public_key().public_bytes(
                    Encoding.Raw,PublicFormat.Raw)}
            if mutation=="unqualified":
                reviewers["specialist-test-reviewer"]["service_kinds"]=["SKIN"]
            if mutation=="expired":
                clock=lambda: datetime(2028,1,1,tzinfo=timezone.utc)
            with self.subTest(mutation=mutation):
                reg=self.registry(entries=entries,reviewers=reviewers,
                                  keys=keys,revoked=revoked,clock=clock)
                self.assertFalse(reg.verify(ref=REF,
                    record_type="KNOWLEDGE",service_kind="HAIR_COLOR",
                    version="draft-v2",digest="a"*64))

    def test_eng05_requires_signed_catalog_and_separate_policy_verifier(self):
        req=request("ENG-05")
        req["payload"]["knowledge_sources"][0]["review_status"]="SPECIALIST_REVIEWED"
        req["payload"]["critical_unknowns"]=[]
        req["payload"]["policy_gate"]["decision"]="REVIEW_REQUIRED"
        # Caller string review_status alone is not a trusted signature.
        self.assertEqual(execute(req,engine="ENG-05")["result"]["status"],"BLOCKED")
        class FakeSeparatePolicy:
            def verify(self,**kw):
                return (kw["tenant_id"]=="tenant-test"
                   and kw["policy_gate"]["decision"]=="REVIEW_REQUIRED")
        gate=SignedKnowledgePolicyGate(self.registry(),FakeSeparatePolicy())
        result=execute(req,engine="ENG-05",knowledge_policy_gate=gate)["result"]
        self.assertEqual(result["status"],"SPECIALIST_REVIEW_REQUIRED")
        self.assertFalse(result["execution_authorized"])
        denied=SignedKnowledgePolicyGate(self.registry(revoked=[REF]),
                                         FakeSeparatePolicy())
        self.assertEqual(execute(req,engine="ENG-05",
            knowledge_policy_gate=denied)["result"]["status"],"BLOCKED")
        no_policy=SignedKnowledgePolicyGate(self.registry(),None)
        self.assertEqual(execute(req,engine="ENG-05",
            knowledge_policy_gate=no_policy)["result"]["status"],"BLOCKED")

    def test_eng06_signed_sop_plus_separate_consent_and_evidence_gate(self):
        req=request("ENG-06")
        req["payload"]["approved_sop_ref"]=SOP
        req["payload"]["consent_status"]="VERIFIED_BY_ENG14"
        req["payload"]["consent_proof_digest"]="c"*64
        req["payload"]["professional_findings"][0]["review_status"]="SPECIALIST_RECORDED"
        class FakeExternalEvidence:
            def verify(self,**kw):
                return (kw["tenant_id"]=="tenant-test"
                  and kw["consent_proof_digest"]=="c"*64)
        gate=SignedSOPConsentGate(self.registry(),FakeExternalEvidence())
        result=execute(req,engine="ENG-06",evidence_gate=gate)["result"]
        self.assertEqual(result["status"],"DRAFT_REQUIRES_SPECIALIST_REVIEW")
        self.assertIsNotNone(result["draft_plan"])
        self.assertFalse(result["operational_handoff_authorized"])
        denied=SignedSOPConsentGate(self.registry(revoked=[SOP]),
                                    FakeExternalEvidence())
        self.assertEqual(execute(req,engine="ENG-06",
            evidence_gate=denied)["result"]["status"],"AWAITING_SPECIALIST_INPUT")
        no_evidence=SignedSOPConsentGate(self.registry(),None)
        self.assertIsNone(execute(req,engine="ENG-06",
            evidence_gate=no_evidence)["result"]["draft_plan"])


if __name__=="__main__":
    unittest.main()

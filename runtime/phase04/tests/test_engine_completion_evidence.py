"""Disposable signer fixtures exercise gate cryptography; NOT real approvals."""
import base64
import copy
import json
import unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from abc_foundation.engine_quality_evaluator import GATES,evaluate
from abc_foundation.engine_quality_signatures import SignedEngineReviewer,SCOPE

HEAD="a"*40
ENGINE="ENG-04"


class EngineCompletionEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.keys={role:Ed25519PrivateKey.generate() for role in (
            "ENGINE_AUDITOR","PROFESSIONAL","SECURITY")}
        self.public={role:k.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)
            for role,k in self.keys.items()}
        self.engine={"id":ENGINE,"critical_blockers":[]}
        self.evidence={g:{"decision":"PASS","artifact_sha256":"b"*64,
                        "evidence_ref":"https://github.com/abc/ci/"+g}
                       for g in GATES}
        self.reviews={}

    def signed(self,sha=HEAD):
        from abc_foundation.engine_quality_evaluator import digest_manifest
        digest=digest_manifest(self.evidence)
        for gate in GATES:
            required=("ENGINE_AUDITOR","PROFESSIONAL","SECURITY") if (
                gate=="G10_INDEPENDENT_SIGNOFF") else ("ENGINE_AUDITOR",)
            self.reviews[gate]={}
            for role in required:
                reviewer="fixture-reviewer-"+role.lower()
                msg=json.dumps({"scope":SCOPE,"engine_id":ENGINE,
                    "commit_sha":sha,"manifest_sha256":digest,
                    "gate_id":gate,"reviewer_id":reviewer,"role":role,
                    "evidence_ref":self.evidence[gate]["evidence_ref"]},
                    sort_keys=True,separators=(",",":")).encode()
                signature=self.keys[role].sign(msg)
                self.reviews[gate][role]={
                    "reviewer_id":reviewer,
                    "signature_b64":base64.b64encode(signature).decode()}
        return SignedEngineReviewer(self.public,self.reviews)

    def test_open_baseline_cannot_be_promoted(self):
        self.engine["critical_blockers"]=["missing real infrastructure"]
        r=evaluate(self.engine,self.evidence,self.signed(),HEAD)
        self.assertFalse(r["complete"])
        self.assertFalse(r["product_release_approved"])
        self.assertEqual(r["status"],"IN_PROGRESS")

    def test_only_all_exact_signed_gates_allow_evaluated_completion(self):
        r=evaluate(self.engine,self.evidence,self.signed(),HEAD)
        self.assertTrue(r["complete"])
        self.assertEqual(r["status"],"COMPLETE")
        self.assertFalse(r["product_release_approved"])

    def test_missing_or_tampered_proof_is_rejected(self):
        reviewer=self.signed()
        self.reviews["G05_SECURITY_PRIVACY"]["ENGINE_AUDITOR"]["signature_b64"]="Zm9yZ2Vk"
        self.assertFalse(evaluate(self.engine,self.evidence,reviewer,HEAD)["complete"])
        reviewer=self.signed()
        del self.reviews["G10_INDEPENDENT_SIGNOFF"]["PROFESSIONAL"]
        self.assertFalse(evaluate(self.engine,self.evidence,reviewer,HEAD)["complete"])
        reviewer=self.signed()
        self.evidence["G02_DOMAIN_CAPABILITY"]["artifact_sha256"]="c"*64
        self.assertFalse(evaluate(self.engine,self.evidence,reviewer,HEAD)["complete"])

    def test_untrusted_verifier_and_wrong_commit_never_complete(self):
        self.assertFalse(evaluate(self.engine,self.evidence,None,HEAD)["complete"])
        self.assertFalse(evaluate(self.engine,self.evidence,object(),HEAD)["complete"])
        reviewer=self.signed()
        self.assertFalse(evaluate(self.engine,self.evidence,reviewer,"f"*40)["complete"])

    def test_independent_public_keys_mandatory(self):
        with self.assertRaises(ValueError):
            SignedEngineReviewer({role:self.public["ENGINE_AUDITOR"]
                 for role in self.public},self.reviews)

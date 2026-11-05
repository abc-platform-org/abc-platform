"""A2 external-gate hardening tests. Keys, identities, reports are FAKE fixtures."""
import base64
import copy
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from scripts.a2_external_staging_acceptance import (
    ENGINES,EVIDENCE,ROLES,SCHEMA,canonical,digest,verify)

SHA="9"*40
FP="a"*64


class ExternalStagingAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="a2-fake-provider-")
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.now=datetime.now(timezone.utc)
        self.keys={role:Ed25519PrivateKey.generate() for role in ROLES}
        self.trust={
            "schema":"abc.a2.operator-pinned-reviewer-keys.v1",
            "reviewers":[
                {"role":role,"identity":"fake-qualified-"+role,
                 "ed25519_public_key_b64":base64.b64encode(
                    self.keys[role].public_key().public_bytes(
                        Encoding.Raw,PublicFormat.Raw)).decode()}
                for role in ROLES]}
        evidence={}
        for item in EVIDENCE:
            payload=json.dumps({"synthetic_only":True,
                       "kind":item,"release":False}).encode()
            (self.root/(item+".json")).write_bytes(payload)
            evidence[item]={"file":item+".json",
                  "sha256":hashlib.sha256(payload).hexdigest(),
                  "origin":"INDEPENDENT_TEST_REPORT"}
        self.base={
            "schema":SCHEMA,"head_sha":SHA,
            "environment":"STAGING_PRIVATE_SYNTHETIC_ONLY",
            "customer_release_approved":False,
            "eng06_release_approved":False,
            "automatic_eng05_to_eng06_dispatch":False,
            "provider":{"owner_approved":True,"billing_authorized":True,
                "deployment_authorized":True,
                "workspace_id":"ci-fake-provider-01",
                "region":"fake-1","operator_id":"ci-fake-operator",
                "monthly_cap":0,"currency":"USD",
                "database_product":"EXTERNAL_CONTROLLED_POSTGRES16_PLUS"},
            "workloads":[{"engine_id":eng,"resource_id":"fake-service-"+eng,
                 "principal_uri":"spiffe://abc.internal/staging/"+eng.lower(),
                 "private_only":True,"public_hostname":None,
                 "managed_issuer_verified":True,
                 "certificate_fingerprint_sha256":FP} for eng in ENGINES],
            "database":{key:True for key in (
                 "private_only","tls13","hostssl_clientcert_verify_full",
                 "sslmode_verify_full","server_ca_pinned","forced_rls",
                 "distinct_noinherit_logins","password_only_fallback_denied",
                 "negative_clientcert_tests","pitr_restore_proven")}|{"version":16},
            "network":{key:True for key in (
                "default_deny","no_public_engine_ingress",
                "no_public_database_ingress","cross_service_negative_probe",
                "unauthorized_egress_denied","private_routes_attested")},
            "checks":{key:True for key in (
                "oidc_and_human_identity","cert_revocation_and_rotation",
                "jwt_replay","consent_race","queue_lease_ack_dlq",
                "provider_service_crash","pg_restart_and_backup_restore",
                "monitoring_alerts","incident_rollback")},
            "evidence":evidence}
        self.packet=self.sign(self.base)

    def sign(self,base):
        packet_hash=digest(base)
        approvals=[]
        for role in ROLES:
            row={"role":role,"identity":"fake-qualified-"+role,
                 "decision":"APPROVE_PRIVATE_STAGING_EVIDENCE_ONLY",
                 "head_sha":SHA,"packet_sha256":packet_hash,
                 "issued_at":(self.now-timedelta(minutes=3)).isoformat(),
                 "expires_at":(self.now+timedelta(days=1)).isoformat()}
            row["signature_b64"]=base64.b64encode(
                self.keys[role].sign(canonical(row))).decode()
            approvals.append(row)
        return {**copy.deepcopy(base),"approvals":approvals}

    def ok(self,packet=None,trust=None):
        return verify(packet if packet is not None else self.packet,
             trust if trust is not None else self.trust,
             self.root,SHA,now=self.now)

    def denied(self,needle,packet=None,trust=None):
        with self.assertRaisesRegex(ValueError,needle):
            self.ok(packet,trust)

    def test_01_synthetic_signatures_are_not_real_provider_proof(self):
        result=self.ok()
        self.assertEqual(result["packet_integrity"],"VERIFIED")
        self.assertEqual(result["provider_actuality"],
                         "REQUIRES_SEPARATE_LIVE_PROVIDER_CROSS_CHECK")
        self.assertFalse(result["eng06_release_approved"])
        self.assertFalse(result["a2_operational_closed"])

    def test_02_missing_security_signature_denied(self):
        p=copy.deepcopy(self.packet)
        p["approvals"].pop()
        self.denied("five_distinct_external_approvals",p)

    def test_03_forged_security_signature_denied(self):
        p=copy.deepcopy(self.packet)
        p["approvals"][2]["signature_b64"]=p["approvals"][0]["signature_b64"]
        self.denied("independent_reviewer_signature_invalid",p)

    def test_04_owner_masquerading_as_security_denied(self):
        p=copy.deepcopy(self.packet)
        p["approvals"][2]["identity"]="fake-qualified-owner"
        self.denied("untrusted_or_duplicate_reviewer",p)

    def test_05_modified_provider_log_hash_denied(self):
        (self.root/(EVIDENCE[3]+".json")).write_bytes(b"edited report content")
        self.denied("external_evidence_hash_mismatch")

    def test_06_public_engine_ingress_denied(self):
        p=copy.deepcopy(self.packet)
        p["workloads"][2]["public_hostname"]="abc-fake-public.example"
        self.denied("managed_identity_or_private_network",p)

    def test_07_postgresql_without_client_cert_verification_denied(self):
        p=copy.deepcopy(self.packet)
        p["database"]["hostssl_clientcert_verify_full"]=False
        self.denied("physical_postgres_identity",p)

    def test_08_consent_race_not_attested_denied(self):
        p=copy.deepcopy(self.packet)
        p["checks"]["consent_race"]=False
        self.denied("real_fault_identity",p)

    def test_09_eng06_customer_release_flip_denied(self):
        p=copy.deepcopy(self.packet)
        p["eng06_release_approved"]=True
        self.denied("professional_gate_must_remain_closed",p)

    def test_10_signature_bound_to_exact_head(self):
        p=copy.deepcopy(self.packet)
        p["head_sha"]="8"*40
        self.denied("packet_not_bound_to_exact_head",p)

    def test_11_signature_bound_to_provider_region_and_network(self):
        p=copy.deepcopy(self.packet)
        p["network"]["default_deny"]=False
        self.denied("real_private_network",p)
        p=copy.deepcopy(self.packet)
        p["provider"]["region"]="changed-region"
        self.denied("signature_not_bound_to_exact_staging_packet",p)

    def test_12_expired_reviewer_attestation_denied(self):
        p=copy.deepcopy(self.packet)
        p["approvals"][0]["expires_at"]=(self.now-timedelta(days=1)).isoformat()
        self.denied("expired_or_future_reviewer_attestation",p)

    def test_13_reviewer_trust_root_swap_denied(self):
        t=copy.deepcopy(self.trust)
        t["reviewers"][2]["ed25519_public_key_b64"] = (
            t["reviewers"][1]["ed25519_public_key_b64"])
        self.denied("independent_reviewer_signature_invalid",trust=t)

    def test_14_no_owner_spend_approval_denied(self):
        p=copy.deepcopy(self.packet)
        p["provider"]["billing_authorized"]=False
        self.denied("owner_provider_cost_or_operator_authority_missing",p)

    def test_15_reused_workload_identity_denied(self):
        p=copy.deepcopy(self.packet)
        p["workloads"][1]["principal_uri"]=p["workloads"][0]["principal_uri"]
        self.denied("distinct_managed_workload_principals",p)

    def test_16_evidence_path_escape_denied(self):
        p=copy.deepcopy(self.packet)
        p["evidence"][EVIDENCE[0]]["file"]="../../secrets.json"
        self.denied("evidence_path_escape_denied",p)


if __name__ == "__main__":
    unittest.main()

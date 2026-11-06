"""ABC A2: fail-closed inspection of externally obtained private staging evidence.

Integrity checks only; cannot provision a provider, issue a certificate,
verify human credentials or grant product release. External operator must
cross-check evidence directly against actual provider APIs and audit logs.
All trust roots/attestation files must be operator-held outside this repo.
"""
import argparse
import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import re

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

SCHEMA = "abc.a2.external-staging-acceptance.v1"
ROLES = ("owner", "operator", "security", "sre", "specialist")
ENGINES = ("ENG-01", "ENG-02", "ENG-03", "ENG-04", "ENG-05", "ENG-06", "ENG-14")
EVIDENCE = (
    "provider_resources", "private_ingress_denials", "network_acl_and_egress",
    "managed_workload_issuer", "certificate_rotation_and_revocation",
    "postgres_clientcert_negatives", "human_oidc_attestation",
    "eng14_consent_race", "durable_recovery_and_replay",
    "restore_and_rollback", "monitoring_and_alerting",
)
HEX64 = re.compile(r"^[a-f0-9]{64}$")
HEX40 = re.compile(r"^[a-f0-9]{40}$")


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def require(condition, code):
    if not condition:
        raise ValueError(code)


def dt(value):
    require(isinstance(value, str), "invalid_attestation_time")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid_attestation_time") from exc
    require(parsed.tzinfo is not None, "timezone_required")
    return parsed.astimezone(timezone.utc)


def verify(packet, trust, evidence_dir, head, *, now=None):
    """Check signed provenance, not provider actuality or human accreditation."""
    now = now or datetime.now(timezone.utc)
    require(isinstance(packet, dict) and packet.get("schema") == SCHEMA,
            "schema_not_approved")
    require(isinstance(head, str) and HEX40.fullmatch(head), "full_head_sha_required")
    require(packet.get("head_sha") == head, "packet_not_bound_to_exact_head")
    require(packet.get("environment") == "STAGING_PRIVATE_SYNTHETIC_ONLY",
            "no_private_synthetic_staging")
    require(packet.get("customer_release_approved") is False and
            packet.get("eng06_release_approved") is False and
            packet.get("automatic_eng05_to_eng06_dispatch") is False,
            "professional_gate_must_remain_closed")
    p = packet.get("provider") or {}
    require(p.get("owner_approved") is True and
            p.get("billing_authorized") is True and
            p.get("deployment_authorized") is True and
            type(p.get("monthly_cap")) in (int, float) and p["monthly_cap"] >= 0 and
            p.get("currency") in ("USD", "EUR") and
            isinstance(p.get("workspace_id"), str) and len(p["workspace_id"]) >= 8 and
            isinstance(p.get("region"), str) and len(p["region"]) >= 3 and
            isinstance(p.get("operator_id"), str) and len(p["operator_id"]) >= 5,
            "owner_provider_cost_or_operator_authority_missing")
    require(p.get("database_product") == "EXTERNAL_CONTROLLED_POSTGRES16_PLUS",
            "managed_postgres_cannot_replace_physical_clientcert")
    workloads = packet.get("workloads")
    require(isinstance(workloads, list) and len(workloads) == len(ENGINES),
            "seven_distinct_workloads_required")
    require({w.get("engine_id") for w in workloads if isinstance(w,dict)}
            == set(ENGINES), "canonical_workload_registry_mismatch")
    identities, resources = set(), set()
    for w in workloads:
        eng = w["engine_id"]
        require(isinstance(w.get("resource_id"), str) and len(w["resource_id"]) >= 8 and
                w["resource_id"] not in resources, "unique_service_resource_ids_required")
        resources.add(w["resource_id"])
        identity = w.get("principal_uri")
        require(identity == "spiffe://abc.internal/staging/" + eng.lower() and
                identity not in identities,
                "distinct_managed_workload_principals_required")
        identities.add(identity)
        require(w.get("private_only") is True and w.get("public_hostname") is None and
                w.get("managed_issuer_verified") is True and
                isinstance(w.get("certificate_fingerprint_sha256"), str) and
                HEX64.fullmatch(w["certificate_fingerprint_sha256"]),
                "managed_identity_or_private_network_proof_missing")
    db = packet.get("database") or {}
    require(type(db.get("version")) is int and db["version"] >= 16 and
            all(db.get(k) is True for k in (
              "private_only", "tls13", "hostssl_clientcert_verify_full",
              "sslmode_verify_full", "server_ca_pinned", "forced_rls",
              "distinct_noinherit_logins", "password_only_fallback_denied",
              "negative_clientcert_tests", "pitr_restore_proven")),
            "physical_postgres_identity_or_recovery_incomplete")
    net = packet.get("network") or {}
    require(all(net.get(k) is True for k in (
              "default_deny", "no_public_engine_ingress",
              "no_public_database_ingress", "cross_service_negative_probe",
              "unauthorized_egress_denied", "private_routes_attested")),
            "real_private_network_denial_missing")
    checks = packet.get("checks") or {}
    require(all(checks.get(k) is True for k in (
              "oidc_and_human_identity", "cert_revocation_and_rotation",
              "jwt_replay", "consent_race", "queue_lease_ack_dlq",
              "provider_service_crash", "pg_restart_and_backup_restore",
              "monitoring_alerts", "incident_rollback")),
            "real_fault_identity_or_operations_evidence_missing")
    records = packet.get("evidence")
    require(isinstance(records, dict) and set(records) == set(EVIDENCE),
            "full_external_evidence_inventory_required")
    evidence_dir = Path(evidence_dir).resolve(strict=True)
    for name, record in records.items():
        require(isinstance(record, dict) and isinstance(record.get("file"), str),
                "immutable_evidence_location_missing")
        rel = Path(record["file"])
        require(not rel.is_absolute() and ".." not in rel.parts,
                "evidence_path_escape_denied")
        target = (evidence_dir / rel).resolve(strict=True)
        require(target.is_relative_to(evidence_dir) and target.is_file() and
                not target.is_symlink(),
                "evidence_path_outside_operator_boundary")
        data = target.read_bytes()
        require(16 <= len(data) <= 2000000 and
                hashlib.sha256(data).hexdigest() == record.get("sha256"),
                "external_evidence_hash_mismatch")
        require(record.get("origin") in (
                    "PROVIDER_EXPORT", "OPERATOR_PROBE", "INDEPENDENT_TEST_REPORT"),
                "external_evidence_origin_unverified")
    base = {k:v for k,v in packet.items() if k != "approvals"}
    packet_digest = digest(base)
    require(trust.get("schema") == "abc.a2.operator-pinned-reviewer-keys.v1",
            "trusted_reviewer_roots_missing")
    keys = trust.get("reviewers")
    require(isinstance(keys, list), "trusted_reviewer_list_missing")
    allowed = {}
    for person in keys:
        ident = (person.get("role"), person.get("identity"))
        require(ident not in allowed and ident[0] in ROLES and
                isinstance(ident[1], str) and len(ident[1]) >= 5,
                "duplicate_or_invalid_external_reviewer_registry")
        allowed[ident] = person
    approvals = packet.get("approvals")
    require(isinstance(approvals, list) and len(approvals) == len(ROLES),
            "five_distinct_external_approvals_required")
    seen_roles, reviewers = set(), {}
    for receipt in approvals:
        role, ident = receipt.get("role"), receipt.get("identity")
        require(role in ROLES and role not in seen_roles and
                (role,ident) in allowed, "untrusted_or_duplicate_reviewer")
        seen_roles.add(role)
        reviewers[role] = ident
        signed = {k:v for k,v in receipt.items() if k != "signature_b64"}
        require(receipt.get("decision") == "APPROVE_PRIVATE_STAGING_EVIDENCE_ONLY" and
                receipt.get("head_sha") == head and
                receipt.get("packet_sha256") == packet_digest,
                "signature_not_bound_to_exact_staging_packet")
        issued, expiry = dt(receipt.get("issued_at")), dt(receipt.get("expires_at"))
        require(issued <= now < expiry and
                (expiry-issued).total_seconds() <= 30*86400,
                "expired_or_future_reviewer_attestation")
        try:
            pub_bytes = base64.b64decode(
                allowed[(role,ident)]["ed25519_public_key_b64"],validate=True)
            require(len(pub_bytes) == 32, "invalid_external_reviewer_key")
            Ed25519PublicKey.from_public_bytes(pub_bytes).verify(
                base64.b64decode(receipt["signature_b64"],validate=True),
                canonical(signed))
        except Exception as exc:
            raise ValueError("independent_reviewer_signature_invalid") from exc
    require(len(set(reviewers.values())) == len(ROLES),
            "security_sre_specialist_operator_owner_must_be_independent")
    return {"packet_integrity":"VERIFIED", "head_sha":head,
            "packet_sha256":packet_digest,"reviewer_roles":list(ROLES),
            "provider_actuality":"REQUIRES_SEPARATE_LIVE_PROVIDER_CROSS_CHECK",
            "customer_release_approved":False,
            "eng06_release_approved":False,"a2_operational_closed":False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--packet",required=True)
    p.add_argument("--trust",required=True)
    p.add_argument("--evidence-dir",required=True)
    p.add_argument("--head",required=True)
    args = p.parse_args()
    repo = Path(__file__).resolve().parents[1]
    trust, data = Path(args.trust).resolve(), Path(args.evidence_dir).resolve()
    if trust.is_relative_to(repo) or data.is_relative_to(repo):
        raise SystemExit("BLOCKED: externally trusted keys and provider artifacts must not be committed fixtures")
    try:
        result=verify(json.loads(Path(args.packet).read_text()),
                      json.loads(trust.read_text()),data,args.head)
        print(json.dumps(result,sort_keys=True))
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps({"gate":"A2_EXTERNAL_STAGING","status":"BLOCKED",
                          "reason":str(exc),"eng06_release_approved":False},
                         sort_keys=True))
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()

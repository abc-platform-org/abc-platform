"""Externally pinned Ed25519 public keys verify engine gate attestations.

Private keys, real identities and professional qualifications are NOT issued by
this module. Authorized operators must verify key ownership out of band.
"""
import base64
import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ROLES=("ENGINE_AUDITOR","PROFESSIONAL","SECURITY")
SCOPE="ABC_ENGINE_COMPLETION_V1"


class SignedEngineReviewer:
    def __init__(self,public_keys,proofs):
        if not isinstance(public_keys,dict) or set(public_keys)!=set(ROLES):
            raise ValueError("external_three_role_trust_anchors_required")
        if not isinstance(proofs,dict):
            raise ValueError("signed_proof_manifest_required")
        self.keys={}
        self.proofs=proofs
        unique=set()
        for role in ROLES:
            key=public_keys[role]
            if not isinstance(key,bytes) or len(key)!=32 or key in unique:
                raise ValueError("distinct_external_ed25519_public_keys_required")
            unique.add(key)
            self.keys[role]=Ed25519PublicKey.from_public_bytes(key)

    def verify(self,*,engine_id,commit_sha,manifest_sha256,gate_ids,evidence):
        if set(self.proofs)!=set(gate_ids):
            return False
        final_reviewers=[]
        for gate in gate_ids:
            proofs=self.proofs[gate]
            needed=ROLES if gate=="G10_INDEPENDENT_SIGNOFF" else ROLES[:1]
            if not isinstance(proofs,dict) or set(proofs)!=set(needed):
                return False
            for role in needed:
                proof=proofs[role]
                try:
                    reviewer=proof["reviewer_id"]
                    signature=base64.b64decode(
                        proof["signature_b64"],validate=True)
                    if not isinstance(reviewer,str) or len(reviewer)<5:
                        return False
                    msg=json.dumps({"scope":SCOPE,"engine_id":engine_id,
                        "commit_sha":commit_sha,"manifest_sha256":manifest_sha256,
                        "gate_id":gate,"reviewer_id":reviewer,
                        "role":role,"evidence_ref":evidence[gate]["evidence_ref"]},
                        sort_keys=True,separators=(",",":")).encode()
                    self.keys[role].verify(signature,msg)
                except (KeyError,TypeError,ValueError,Exception) as error:
                    return False
                if gate=="G10_INDEPENDENT_SIGNOFF":
                    final_reviewers.append(reviewer)
        return len(set(final_reviewers))==3

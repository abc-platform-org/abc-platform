"""Authoritative fail-closed Phase04 live readiness assertions, not an issuer.

A CI fixture may never turn physical provider IDs or professional signoff into
a successful release. Actual approval requires independent human verification
of externally provisioned evidence and a separately reviewed release action.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FILE=ROOT/"governance/phase04_readiness.v1.json"
GATE_IDS=tuple("P04-%02d"%i for i in range(1,11))


def validate(manifest):
    assert manifest["schema_version"]=="abc.phase04-readiness.v1"
    assert manifest["scope"]=="PHASE04_INFRASTRUCTURE_AND_CONTROLLED_ENGINE_INTEGRATION"
    assert manifest["status"]=="IN_PROGRESS"
    assert manifest["release_status"]=="BLOCKED"
    assert manifest["managed_private_deployment_verified"] is False
    assert manifest["phase04_complete"] is False
    assert manifest["production_release_approved"] is False
    gates=manifest["required_gates"]
    assert tuple(g["id"] for g in gates)==GATE_IDS
    for g in gates:
        assert g["status"]=="OPEN"
        assert g["evidence_refs"]==[]
        assert g["signed_independent_approvals"]==[]
        assert len(g["exit_criterion"])>=40
        assert len(g["owner"])>=2
    return {"status":"IN_PROGRESS","phase04_complete":False,
            "release_approved":False,"required_gate_count":len(gates),
            "unverified_gate_count":len(gates)}


def main():
    print(json.dumps(validate(json.loads(FILE.read_text())),
                     sort_keys=True))


if __name__=="__main__":
    main()

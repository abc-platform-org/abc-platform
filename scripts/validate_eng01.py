"""Contract drift and least-authority safety checks for ENG-01 runtime artifact."""
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
source=json.loads((root/"contracts/v1/state-machines.json").read_text())
target=json.loads((root/"runtime/phase04/abc_foundation/eng01_consultation_machine.json").read_text())
machine=[x for x in source["machines"] if x["id"]=="CONSULTATION_SESSION"]
assert len(machine)==1
canonical=machine[0]
expected={
    "source_contract_version":source["version"],
    "source_machine_id":canonical["id"],
    "source_initial":canonical["initial"],
    "source_terminal":canonical["terminal"],
    "states":canonical["states"],
    "transitions":canonical["transitions"],
}
assert target==expected, "ENG-01 compiled machine drifted from canonical frozen Phase02"
assert target["source_contract_version"]=="1.0.0-draft"
assert len(target["transitions"])==102 and len(target["states"])==20
assert any(t["from"]=="CREATED" and t["to"]=="PAUSED"
           and t["actor"]=="SPECIALIST"
           and t["guards"]==["authenticated_actor","persist_checkpoint"]
           for t in target["transitions"])
for p in ("runtime/phase04/abc_foundation/eng01_orchestrator.py",):
    impl=(root/p).read_text()
    assert "capability_not_implemented" in impl
    assert "self.store.checkpoint_command(" in impl
    assert "verified_oidc_identity_required" in impl
print("PASS: compiled 102-edge/20-state ENG-01 machine matches canonical Phase02 exactly")

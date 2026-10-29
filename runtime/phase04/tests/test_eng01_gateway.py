"""Internal ENG01 typed-command negative test suite; no external AI API."""
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
import unittest
import uuid

from abc_foundation.eng01_gateway import TypedCheckpointGateway
from abc_foundation.oidc import Principal
from abc_foundation.store import DomainError

ISS="https://identity.example.test/realms/abc"
NOW=datetime(2026,10,29,12,0,0,tzinfo=timezone.utc)


class SyntheticScopedStore:
    def __init__(self):
        self.sid=str(uuid.uuid4())
        self.principal=Principal("spec-1",ISS)
        self.row=dict(session_id=self.sid,tenant_id="tenant-a",branch_id="branch-a",
                      specialist_id="spec-1",state="CREATED",state_version=0)
        self.receipts={}
        self.calls=0

    @staticmethod
    def _key(key):
        if len(key)<8: raise DomainError(400,"invalid_idempotency_key")

    def get(self,principal,sid):
        if sid!=self.sid or principal!=self.principal:
            raise DomainError(404,"not_found")
        return dict(self.row)

    def execute_eng01_pause(self,principal,command):
        import hashlib,json
        digest=hashlib.sha256(json.dumps(command,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        key=command["command_id"]
        if key in self.receipts:
            previous,result=self.receipts[key]
            if previous!=digest:
                raise DomainError(409,"idempotency_payload_conflict")
            return dict(result)
        self.calls+=1
        self.get(principal,command["session_id"])
        if self.row["state"]!="CREATED" or command["expected_state_version"]!=self.row["state_version"]:
            raise DomainError(409,"state_version_conflict")
        self.row["state"],self.row["state_version"]="PAUSED",1
        result={**self.row,"engine_id":"ENG-01","status":"DURABLE_CHECKPOINT_COMMITTED",
                "publication_status":"INTERNAL_SYNTHETIC_ONLY",
                "command_id":key,"correlation_id":command["correlation_id"]}
        self.receipts[key]=(digest,dict(result))
        return result

    def checkpoint_command(self,principal,sid,action,version,key):
        self.calls+=1
        self.get(principal,sid)
        if key in self.receipts:
            return dict(self.receipts[key])
        if self.row["state"]!="CREATED" or version!=0 or action!="pause":
            raise DomainError(409,"state_version_conflict")
        self.row["state"],self.row["state_version"]="PAUSED",1
        self.receipts[key]=dict(self.row)
        return dict(self.row)


class TypedGatewayTests(unittest.TestCase):
    def setUp(self):
        self.store=SyntheticScopedStore()
        self.g=TypedCheckpointGateway(self.store,clock=lambda:NOW)
        self.p=self.store.principal
        cmd_id=str(uuid.uuid4())
        self.cmd=dict(
            command_id=cmd_id,engine_id="ENG-01",contract_version="1.0.0-draft",
            correlation_id=str(uuid.uuid4()),tenant_id="tenant-a",
            branch_id="branch-a",session_id=self.store.sid,
            actor={"user_id":"spec-1","role":"SPECIALIST"},
            input_schema_id="abc.internal.eng01.checkpoint.v0",
            input_ref="checkpoint:pause",idempotency_key=cmd_id,
            requested_at="2026-10-29T12:00:00Z",expected_state_version=0)

    def invoke(self,**changes):
        return self.g.execute(self.p,{**self.cmd,**changes})

    def deny(self,code,**changes):
        with self.assertRaises(DomainError) as exc:
            self.invoke(**changes)
        self.assertEqual(exc.exception.code,code)

    def test_valid_command_is_durable_and_exact_replay(self):
        result=self.invoke()
        self.assertEqual(result["state"],"PAUSED")
        self.assertEqual(result["command_id"],self.cmd["command_id"])
        self.assertEqual(result["correlation_id"],self.cmd["correlation_id"])
        self.assertEqual(self.invoke(),result)
        self.assertEqual(self.store.row["state_version"],1)

    def test_mutation_requires_frozen_command_fields(self):
        for field in self.cmd:
            with self.subTest(field=field),self.assertRaises(DomainError):
                self.g.execute(self.p,{k:v for k,v in self.cmd.items() if k!=field})
        self.deny("invalid_engine_command",invented_proof=True)

    def test_model_or_other_engine_cannot_invoke_internal_gateway(self):
        for change in (
            {"engine_id":"ENG-19"},
            {"input_ref":"checkpoint:resume"},
            {"contract_version":"unapproved"},
            {"input_schema_id":"random-schema"},
        ):
            with self.subTest(change=change):
                self.deny("capability_not_implemented",**change)
        self.assertEqual(self.store.calls,0)

    def test_actor_claim_does_not_grant_privileges(self):
        for actor in (
            {"user_id":"spec-1","role":"ORG_OWNER"},
            {"user_id":"fake-owner","role":"SPECIALIST"},
            {"user_id":"spec-1","role":"SPECIALIST","is_superuser":True},
            "SPECIALIST",None):
            with self.subTest(actor=actor):
                self.deny("verified_actor_mismatch",actor=actor)

    def test_supplied_tenant_branch_cannot_override_trusted_store(self):
        for delta in ({"tenant_id":"other-tenant"},{"branch_id":"other-branch"}):
            with self.subTest(delta=delta):
                self.deny("not_found",**delta)

    def test_missing_or_invalid_principal_rejected(self):
        with self.assertRaises(DomainError):
            self.g.execute(Principal("bad",ISS),self.cmd)
        with self.assertRaises(DomainError):
            self.g.execute(SimpleNamespace(subject="spec-1",issuer="http://bad"),self.cmd)

    def test_deadline_expiration_and_future_clock_fail_closed(self):
        self.deny("command_deadline_expired",deadline_at="2026-10-29T11:00:00Z")
        self.deny("command_from_future",requested_at="2026-10-30T12:00:00Z")
        self.deny("invalid_command_time",requested_at="2026-10-29T12:00:00")
        self.deny("invalid_command_time",deadline_at="tomorrow")

    def test_invalid_uuid_scope_and_version_denied(self):
        self.deny("invalid_command_id",command_id="not-uuid")
        self.deny("invalid_correlation_id",correlation_id="not-uuid")
        self.deny("invalid_session_id",session_id="not-uuid")
        self.deny("invalid_scope",tenant_id="")
        self.deny("invalid_expected_state_version",expected_state_version=True)

    def test_different_command_id_same_idempotency_key_cannot_replay(self):
        self.invoke()
        self.deny("command_idempotency_binding_required",command_id=str(uuid.uuid4()))

    def test_changed_correlation_under_same_command_uuid_rejected(self):
        self.invoke()
        self.deny("idempotency_payload_conflict",correlation_id=str(uuid.uuid4()))

    def test_forged_policy_token_is_not_authorized(self):
        self.deny("policy_gate_not_connected",policy_decision_id="not-verified")

    def test_missing_deadline_is_accepted_for_same_safe_internal_command(self):
        self.assertEqual(self.invoke()["state"],"PAUSED")
        self.assertEqual(self.store.calls,1)

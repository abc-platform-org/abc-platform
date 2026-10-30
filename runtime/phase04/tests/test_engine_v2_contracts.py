"""Consumer-driven strict v2 interface contract and security boundary tests."""
import copy
import json
import unittest
import uuid
from pathlib import Path

from abc_foundation.engine_v2_contracts import (
    VERSION,FILES,envelope_schema,validate_port,validate_error,stub_response)
from abc_foundation.store import DomainError

S="11111111-1111-4111-8111-111111111111"
E="22222222-2222-4222-8222-222222222222"
L="33333333-3333-4333-8333-333333333333"
C="44444444-4444-4444-8444-444444444444"
H="a"*64
T="tenant-test"
B="branch-test"


def request(engine):
    common={"request_id":S,"engine_id":engine,
        "contract_version":VERSION,"consumer_id":"test-worker",
        "tenant_id":T,"branch_id":B,"session_id":E,
        "state_version":2,"correlation_id":C}
    if engine=="ENG-04":
        payload={"service_kind":"HAIR_COLOR",
           "evidence":[{"evidence_id":L,"source_digest":H,
                        "evidence_class":"USER_REPORTED"}],
           "current_media_ref":"synthetic:original-hair",
           "reference_media_refs":["synthetic:reference-one"],
           "edit_regions":["HAIR"],"identity_lock":True,
           "target_intent":"Cooler brown style preview"}
    elif engine=="ENG-05":
        payload={"service_kind":"HAIR_COLOR",
          "recommendation_ref":{"engine_id":"ENG-04","session_id":E,
             "tenant_id":T,"branch_id":B,"digest":H},
          "candidate_looks":[{"look_id":L,"spec_digest":H,
                              "evidence_ids":[L]}],
          "knowledge_sources":[{"source_ref":"synthetic:catalog-entry",
              "version":"draft-v2","digest":H,"review_status":"UNVERIFIED"}],
          "critical_unknowns":["CHEMICAL_HISTORY_UNKNOWN"],
          "policy_gate":{"engine_id":"ENG-14","decision":"BLOCK",
                         "decision_digest":H}}
    else:
        payload={"service_kind":"HAIR_COLOR",
           "selected_look_lock":{"look_id":L,"tenant_id":T,
             "branch_id":B,"session_id":E,"state_version":2,
             "locked_by_specialist_id":"specialist-test",
             "lock_event_id":S},
           "decision_ref":{"engine_id":"ENG-05","tenant_id":T,
             "branch_id":B,"session_id":E,"state_version":2,"digest":H},
           "current_state_evidence_ids":[L],
           "professional_findings":[{"finding_ref":"synthetic:current-evidence",
              "review_status":"UNVERIFIED"}],
           "approved_sop_ref":None,"consent_status":"MISSING"}
    return {**common,"payload":payload}


def response(req):
    engine=req["engine_id"]
    common={k:req[k] for k in (
        "request_id","engine_id","contract_version","consumer_id",
        "tenant_id","branch_id","session_id","state_version","correlation_id")}
    if engine=="ENG-04":
        result={"status":"DRAFT_FOR_SPECIALIST_REVIEW",
          "candidate_looks":[{"look_id":L,"spec_digest":H,
              "evidence_ids":[L],"edit_regions":["HAIR"],
              "feasibility":"NOT_VERIFIED"}],
          "uncertainty":["PROFESSIONAL_FEASIBILITY_UNKNOWN"],
          "visual_qa_status":"NOT_VERIFIED",
          "professional_approval_verified":False}
    elif engine=="ENG-05":
        result={"status":"BLOCKED","eligible_looks":[],
           "excluded_looks":[{"look_id":L,"reason":"CRITICAL_EVIDENCE_MISSING"}],
           "critical_unknowns":["CHEMICAL_HISTORY_UNKNOWN"],
           "specialist_selection_authorized":False,
           "execution_authorized":False}
    else:
        result={"status":"AWAITING_SPECIALIST_INPUT",
          "draft_plan":None,"missing_requirements":["APPROVED_SOP_MISSING"],
          "professional_validation":"NOT_VERIFIED",
          "operational_handoff_authorized":False,
          "execution_authorized":False}
    return {**common,"result":result,"release_approved":False,
            "execution_authorized":False}


class EngineV2PortTests(unittest.TestCase):
    def test_three_draft_contracts_have_separate_roles_and_valid_schemas(self):
        from abc_foundation.engine_v2_contracts import _port
        self.assertEqual(set(FILES),{"ENG-04","ENG-05","ENG-06"})
        roles={_port(engine)["role"] for engine in FILES}
        self.assertEqual(roles,{"RECOMMENDATION_INTELLIGENCE",
              "DECISION_INTELLIGENCE","TECHNICAL_PLANNING_INTELLIGENCE"})
        for engine in FILES:
            self.assertTrue(envelope_schema(engine))
            self.assertTrue(validate_port(request(engine),engine=engine)["valid"])
            self.assertFalse(stub_response(request(engine),
                                           engine=engine)["release_approved"])
            self.assertTrue(validate_port(response(request(engine)),
                                engine=engine,response=True,
                                request=request(engine))["valid"])

    def test_cross_version_wrong_port_and_unscoped_requests_rejected(self):
        for engine in FILES:
            original=request(engine)
            for change in (
                {"contract_version":"abc.internal.engine.synthetic.v1"},
                {"engine_id":"ENG-99"},
                {"tenant_id":""},
                {"branch_id":"other branch"},
                {"state_version":-1},
                {"release_approved":True}
            ):
                msg={**original,**change}
                with self.subTest(engine=engine,change=change),self.assertRaises(DomainError):
                    validate_port(msg,engine=engine)
            with self.assertRaises(DomainError):
                validate_port(original,engine="ENG-01")

    def test_eng04_identity_provenance_region_reference_and_release(self):
        req=request("ENG-04")
        for tweak in ("identity","duplicate","mixed_reference"):
            msg=copy.deepcopy(req)
            if tweak=="identity":msg["payload"]["identity_lock"]=False
            if tweak=="duplicate":msg["payload"]["evidence"]*=2
            if tweak=="mixed_reference":
                msg["payload"]["reference_media_refs"]=[
                    msg["payload"]["current_media_ref"]]
            with self.subTest(tweak=tweak),self.assertRaises(DomainError):
                validate_port(msg,engine="ENG-04")
        for mutate in ("region","invented_evidence","release"):
            out=response(req)
            if mutate=="region":out["result"]["candidate_looks"][0]["edit_regions"]=["SKIN"]
            if mutate=="invented_evidence":
                out["result"]["candidate_looks"][0]["evidence_ids"]=[S]
            if mutate=="release":out["release_approved"]=True
            with self.subTest(mutate=mutate),self.assertRaises(DomainError):
                validate_port(out,engine="ENG-04",response=True,request=req)

    def test_eng05_critical_unknowns_and_eng14_block_defeat_fake_eligibility(self):
        req=request("ENG-05")
        msg=copy.deepcopy(req)
        msg["payload"]["recommendation_ref"]["tenant_id"]="tenant-other"
        with self.assertRaises(DomainError):
            validate_port(msg,engine="ENG-05")
        out=response(req)
        out["result"]["eligible_looks"]=[{"look_id":L,"reason":"looks nice",
                                            "evidence_ids":[L]}]
        with self.assertRaises(DomainError):
            validate_port(out,engine="ENG-05",response=True,request=req)
        out=response(req)
        out["result"]["excluded_looks"][0]["look_id"]=S
        with self.assertRaises(DomainError):
            validate_port(out,engine="ENG-05",response=True,request=req)

    def test_eng06_lock_and_decision_fencing_and_never_handoff(self):
        req=request("ENG-06")
        for field,value in (("session_id",S),("state_version",1),
                            ("branch_id","branch-other")):
            msg=copy.deepcopy(req)
            msg["payload"]["selected_look_lock"][field]=value
            with self.subTest(field=field),self.assertRaises(DomainError):
                validate_port(msg,engine="ENG-06")
        msg=copy.deepcopy(req)
        msg["payload"]["decision_ref"]["state_version"]=3
        with self.assertRaises(DomainError):
            validate_port(msg,engine="ENG-06")
        out=response(req)
        out["result"]["operational_handoff_authorized"]=True
        with self.assertRaises(DomainError):
            validate_port(out,engine="ENG-06",response=True,request=req)

    def test_v2_failure_envelope_is_scoped_and_fail_closed(self):
        for engine in FILES:
            req=request(engine)
            error=stub_response(req,engine=engine)
            self.assertTrue(validate_error(error,engine=engine,request=req))
            self.assertEqual(error["error"]["code"],"NOT_IMPLEMENTED")
            self.assertFalse(error["error"]["retryable"])
            self.assertFalse(error["execution_authorized"])
            self.assertNotIn("result",error)
            self.assertNotIn("payload",error)
            for change in (
                {"tenant_id":"different-tenant"},
                {"contract_version":"abc.internal.engine.synthetic.v1"},
                {"execution_authorized":True},
                {"error":{"code":"NOT_IMPLEMENTED","retryable":True}},
                {"error":{"code":"SOME_UNKNOWN_ERROR","retryable":False}},
            ):
                unsafe={**error,**change}
                with self.subTest(engine=engine,change=change),self.assertRaises(DomainError):
                    validate_error(unsafe,engine=engine,request=req)

    def test_v1_dispatcher_and_contract_are_not_v2_routers(self):
        from abc_foundation import isolated_engine_service
        self.assertEqual(isolated_engine_service.VERSION,
                         "abc.internal.engine.synthetic.v1")
        from jsonschema import Draft202012Validator
        self.assertFalse(isolated_engine_service._INPUT.is_valid(request("ENG-04")))
        root=Path(__file__).resolve().parents[1]
        src=(root/"abc_foundation/isolated_engine_service.py").read_text()
        self.assertNotIn("engine_v2_contracts",src)


if __name__=="__main__":
    unittest.main()

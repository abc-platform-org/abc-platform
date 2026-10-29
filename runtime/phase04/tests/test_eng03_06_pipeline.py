"""Offline synthetic ENG02 -> ENG03 -> ENG04 + ENG05 -> ENG06 golden workflow."""
import tempfile
import unittest
import uuid

from abc_foundation.eng02_consultation import ConsultationEngine,SYNTHETIC_SERVICE
from abc_foundation.eng03_evidence import SyntheticEvidenceEngine
from abc_foundation.eng04_analysis import SyntheticBeautyAnalysis
from abc_foundation.eng05_knowledge import SyntheticKnowledgeEngine
from abc_foundation.eng06_decision import SyntheticDecisionEngine
from abc_foundation.oidc import Principal
from abc_foundation.store import DomainError

ISS="https://identity.example.test/realms/abc"
FIXTURE={
    "kind":"SYNTHETIC_TEST_FIXTURE","source_id":"synthetic:offline-catalog",
    "source_version":"test-v1","validated_by":"TEST_FIXTURE_ONLY",
    "facts":{"synthetic:style-a":True,"synthetic:style-b":False}
}


class ScopedSyntheticSession:
    def __init__(self):
        self.sid=str(uuid.uuid4())
        self.p=Principal("specialist-synthetic",ISS)
        self.tenant="synthetic-tenant"
        self.branch="synthetic-branch"
    def get(self,p,sid):
        if p!=self.p or sid!=self.sid: raise DomainError(404,"not_found")
        return {"session_id":sid,"specialist_id":p.subject,"tenant_id":self.tenant,
                "branch_id":self.branch,"service_id":SYNTHETIC_SERVICE,"state":"CREATED"}


class OfflineVerticalTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.scoped=ScopedSyntheticSession()
        self.session=self.scoped.sid
        self.p=self.scoped.p
        self.e2=ConsultationEngine(self.t.name+"/answers.sqlite",self.scoped)
        self.e3=SyntheticEvidenceEngine(self.e2)
        self.e4=SyntheticBeautyAnalysis()
        self.e5=SyntheticKnowledgeEngine()
        self.e6=SyntheticDecisionEngine()

    def answer(self, val):
        q=self.e2.next(self.p,self.session)["next_question"]
        return self.e2.record(self.p,self.session,question_id=q["question_id"],
                              value=val,source="CLIENT",operation_key="synthetic-"+uuid.uuid4().hex)

    def result(self, *, fixture=FIXTURE):
        evidence=self.e3.collect_non_media(self.p,self.session)
        analysis=self.e4.analyse(session_id=self.session,evidence=evidence)
        knowledge=self.e5.resolve(service_id=SYNTHETIC_SERVICE,fixture=fixture)
        decision=self.e6.decide(analysis=analysis,knowledge=knowledge)
        return evidence,analysis,knowledge,decision

    def test_every_engine_has_distinct_typed_role(self):
        self.assertEqual([x.ENGINE_ID for x in (self.e2,self.e3,self.e4,self.e5,self.e6)],
                         ["ENG-02","ENG-03","ENG-04","ENG-05","ENG-06"])

    def test_missing_data_remains_unknown_and_blocks_all_options(self):
        ev,a,k,d=self.result()
        self.assertEqual(len(ev),4)
        self.assertTrue(all(item["evidence_class"]=="UNKNOWN" for item in ev))
        self.assertEqual(set(a["unknowns"]),
                         {"prior_treatment","sensitivity_flag","goal","maintenance"})
        self.assertEqual(d["candidates"],[])
        self.assertEqual(len(d["excluded_options"]),2)

    def test_complete_synthetic_flow_yields_only_one_conditional_candidate(self):
        for v in ("NO","NO","SUBTLE","LOW"): self.answer(v)
        ev,a,k,d=self.result()
        self.assertEqual(len(a["attributes"]),4)
        self.assertTrue(all(e["evidence_class"]=="USER_REPORTED" for e in ev))
        self.assertTrue(all(x["evidence_class"]=="USER_REPORTED" for x in a["attributes"]))
        self.assertEqual(len(d["candidates"]),1)
        self.assertEqual(d["candidates"][0]["candidate_id"],"synthetic:style-a")
        self.assertEqual(d["candidates"][0]["feasibility_label"],"PROFESSIONAL_CHECK_REQUIRED")
        self.assertEqual(d["candidates"][0]["hard_filter_status"],"CONDITIONALLY_PASSED")
        self.assertEqual(d["excluded_options"][0]["candidate_id"],"synthetic:style-b")
        self.assertNotIn("synthetic:style-b",{x["candidate_id"] for x in d["candidates"]})

    def test_real_knowledge_not_faked_when_no_source(self):
        for v in ("NO","NO","SUBTLE","LOW"): self.answer(v)
        _,_,knowledge,decision=self.result(fixture=None)
        self.assertEqual(knowledge["retrieval_sources"],[])
        self.assertEqual(knowledge["grounded_facts"],[])
        self.assertEqual(knowledge["unknowns"],["SOURCE_UNVERIFIED"])
        self.assertEqual(decision["candidates"],[])

    def test_reported_sensitivity_never_promoted_to_feasibility(self):
        self.answer("NO")
        self.answer("YES")
        _,a,_,d=self.result()
        self.assertIn("REPORTED_SENSITIVITY_REQUIRES_SPECIALIST_REVIEW",a["safety_notes"])
        self.assertEqual(d["candidates"],[])
        self.assertTrue(all(x["reason"]=="CRITICAL_EVIDENCE_OR_SPECIALIST_REVIEW_REQUIRED"
                            for x in d["excluded_options"]))

    def test_unknown_critical_fact_disallows_recommendation(self):
        self.answer("UNKNOWN")
        _,a,_,d=self.result()
        self.assertIn("prior_treatment",a["unknowns"])
        self.assertEqual(d["candidates"],[])

    def test_missing_or_forged_provenance_fail_closed(self):
        ev,_,k,_=self.result()
        tampered=[dict(x) for x in ev]
        tampered[0]["session_id"]=str(uuid.uuid4())
        with self.assertRaises(DomainError):
            self.e4.analyse(session_id=self.session,evidence=tampered)
        tampered=[dict(x) for x in ev]
        tampered[0]["evidence_class"]="OBSERVED"
        with self.assertRaises(DomainError):
            self.e4.analyse(session_id=self.session,evidence=tampered)

    def test_model_fabricated_source_and_released_pack_refused(self):
        with self.assertRaises(DomainError):
            self.e5.resolve(service_id="actual:hair-color",fixture=FIXTURE)
        with self.assertRaises(DomainError):
            self.e5.resolve(service_id=SYNTHETIC_SERVICE,
                             fixture={**FIXTURE,"validated_by":"fake-expert"})

    def test_nonexistent_media_gate_is_not_hidden(self):
        with self.assertRaises(DomainError) as ctx:
            self.e3.validate_media("/tmp/a-real-client-photo.jpg")
        self.assertEqual(ctx.exception.status,501)

    def test_cross_tenant_or_wrong_specialist_cannot_extract_evidence(self):
        with self.assertRaises(DomainError):
            self.e3.collect_non_media(Principal("other",ISS),self.session)

    def test_evidence_bound_to_session_and_no_extra_alternatives(self):
        ev,a,k,d=self.result()
        self.assertEqual(d["session_id"],self.session)
        self.assertEqual({x["source_evidence_id"] for x in a["attributes"]},
                         set(a["evidence_ids"]))
        self.assertEqual(len(d["excluded_options"])+len(d["candidates"]),2)

    def test_malicious_analysis_unknown_to_known_promotion_refused(self):
        ev,a,k,d=self.result()
        a2={**a,"attributes":[dict(x) for x in a["attributes"]]}
        a2["attributes"][0]["value"]="INFERRED_BY_AI"
        with self.assertRaises(DomainError):
            self.e6.decide(analysis=a2,knowledge=k)

    def test_forged_knowledge_source_id_refused(self):
        ev,a,k,_=self.result()
        k2={**k,"retrieval_sources":[{"source_id":"other","source_version":"x",
                                       "validated_by":"TEST_FIXTURE_ONLY"}],
            "grounded_facts":[{"key":"synthetic:style-a","value":True,"source_id":"other"}]}
        with self.assertRaises(DomainError):
            self.e6.decide(analysis=a,knowledge=k2)

    def test_deterministic_source_bound_decision_identity(self):
        for v in ("NO","NO","BOLD","FLEXIBLE"): self.answer(v)
        _,a1,k1,d1=self.result()
        _,a2,k2,d2=self.result()
        self.assertEqual(a1["analysis_id"],a2["analysis_id"])
        self.assertEqual(d1["recommendation_set_id"],d2["recommendation_set_id"])

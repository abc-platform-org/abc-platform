"""Reproducible no-API synthetic ENG02..06 walkthrough; NO production entrypoint."""
import json
import os
import tempfile
import uuid

from abc_foundation.eng02_consultation import ConsultationEngine,SYNTHETIC_SERVICE
from abc_foundation.eng03_evidence import SyntheticEvidenceEngine
from abc_foundation.eng04_analysis import SyntheticBeautyAnalysis
from abc_foundation.eng05_knowledge import SyntheticKnowledgeEngine
from abc_foundation.eng06_decision import SyntheticDecisionEngine
from abc_foundation.oidc import Principal
from abc_foundation.store import DomainError


class SyntheticSessionScope:
    def __init__(self):
        self.sid=str(uuid.uuid4())
        self.principal=Principal("synthetic-engine-demo","https://identity.example.test/abc-fixture")
    def get(self,principal,session_id):
        if principal!=self.principal or session_id!=self.sid:
            raise DomainError(404,"not_found")
        return {"session_id":self.sid,"tenant_id":"synthetic-demo-tenant",
                "branch_id":"synthetic-demo-branch",
                "specialist_id":self.principal.subject,
                "service_id":SYNTHETIC_SERVICE,"state":"CREATED"}


def demo():
    if os.getenv("ABC_ENV")!="LOCAL_INTEGRATION_ONLY" or os.getenv("ABC_DEMO_SYNTHETIC")!="yes":
        raise SystemExit("offline synthetic-only demonstration requires explicit local gate")
    scoped=SyntheticSessionScope()
    with tempfile.TemporaryDirectory(prefix="abc-synthetic-") as folder:
        e2=ConsultationEngine(folder+"/consultation.sqlite",scoped)
        question_ids=[]
        for value in ("NO","NO","SUBTLE","LOW"):
            q=e2.next(scoped.principal,scoped.sid)["next_question"]
            if q is None:
                raise RuntimeError("unexpected_safety_or_question_state")
            question_ids.append(q["question_id"])
            e2.record(scoped.principal,scoped.sid,question_id=q["question_id"],value=value,
                      source="CLIENT",operation_key="synthetic-demo-"+uuid.uuid4().hex)
        profile=e2.profile_snapshot(scoped.principal,scoped.sid)
        evidence=SyntheticEvidenceEngine(e2).collect_non_media(scoped.principal,scoped.sid)
        analysis=SyntheticBeautyAnalysis().analyse(session_id=scoped.sid,evidence=evidence)
        mock_source={"kind":"SYNTHETIC_TEST_FIXTURE",
                     "source_id":"synthetic:offline-catalog",
                     "source_version":"test-v1","validated_by":"TEST_FIXTURE_ONLY",
                     "facts":{"synthetic:style-a":True,"synthetic:style-b":False}}
        knowledge=SyntheticKnowledgeEngine().resolve(service_id=SYNTHETIC_SERVICE,fixture=mock_source)
        decision=SyntheticDecisionEngine().decide(analysis=analysis,knowledge=knowledge)
        assert len(decision["candidates"])==1
        assert all(x["feasibility_label"]=="PROFESSIONAL_CHECK_REQUIRED" for x in decision["candidates"])
        report={
            "simulation":"SYNTHETIC_INTERNAL_ONLY",
            "released_to_customers":False,
            "paid_API_calls":0,
            "engine_chain":["ENG-02","ENG-03","ENG-04","ENG-05","ENG-06"],
            "consultation_readiness":profile["readiness"],
            "question_count":len(question_ids),
            "evidence_source_class":["USER_REPORTED"],
            "analysis_unknowns":analysis["unknowns"],
            "knowledge_review":"TEST_FIXTURE_ONLY_NOT_PROFESSIONALLY_APPROVED",
            "conditionally_listed_test_candidates":[x["candidate_id"] for x in decision["candidates"]],
            "excluded_test_candidates":[x["candidate_id"] for x in decision["excluded_options"]],
            "human_validation":"REQUIRED_BEFORE_REAL_USE"
        }
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return report


if __name__=="__main__":
    demo()

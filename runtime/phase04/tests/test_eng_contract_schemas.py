"""Canonical Phase02 JSON Schema validation of actual offline ENG02..06 artifacts."""
import json
from pathlib import Path
import tempfile
import uuid
import unittest

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from abc_foundation.eng02_consultation import ConsultationEngine,SYNTHETIC_SERVICE
from abc_foundation.eng03_evidence import SyntheticEvidenceEngine
from abc_foundation.eng04_analysis import SyntheticBeautyAnalysis
from abc_foundation.eng05_knowledge import SyntheticKnowledgeEngine
from abc_foundation.eng06_decision import SyntheticDecisionEngine
from abc_foundation.oidc import Principal
from abc_foundation.store import DomainError


SCHEMAS=Path(__file__).resolve().parents[3]/"contracts"/"v1"/"schemas"
common=json.loads((SCHEMAS/"common.schema.json").read_text())
registry=Registry().with_resource(common["$id"],Resource.from_contents(common))


def checked(document, schema):
    target=json.loads((SCHEMAS/(schema+".schema.json")).read_text())
    validator=Draft202012Validator(target,registry=registry,
              format_checker=Draft202012Validator.FORMAT_CHECKER)
    validator.validate(document)


class Scoped:
    def __init__(self):
        self.sid=str(uuid.uuid4())
        self.p=Principal("schema-test-specialist","https://identity.example.test/test")
    def get(self,p,s):
        if p!=self.p or s!=self.sid:
            raise DomainError(404,"not_found")
        return {"session_id":self.sid,"tenant_id":"schema-test-tenant",
                "branch_id":"schema-test-branch",
                "specialist_id":self.p.subject,"state":"CREATED","service_id":SYNTHETIC_SERVICE}


class SchemaEvidenceTests(unittest.TestCase):
    def test_full_offline_chain_matches_frozen_output_shapes(self):
        with tempfile.TemporaryDirectory() as tmp:
            scoped=Scoped()
            c=ConsultationEngine(tmp+"/consultation.sqlite",scoped)
            engine3=SyntheticEvidenceEngine(c)
            step=c.next(scoped.p,scoped.sid)
            checked(step["next_question"],"question")
            checked(c.profile_snapshot(scoped.p,scoped.sid),"consultation-profile")
            for value in ("NO","NO","SUBTLE","LOW"):
                q=c.next(scoped.p,scoped.sid)["next_question"]
                c.record(scoped.p,scoped.sid,question_id=q["question_id"],value=value,
                         source="CLIENT",operation_key="schema-"+uuid.uuid4().hex)
            checked(c.profile_snapshot(scoped.p,scoped.sid),"consultation-profile")
            facts=engine3.collect_non_media(scoped.p,scoped.sid)
            for record in facts: checked(record,"evidence")
            analysis=SyntheticBeautyAnalysis().analyse(session_id=scoped.sid,evidence=facts)
            checked(analysis,"analysis")
            source={"kind":"SYNTHETIC_TEST_FIXTURE","source_id":"synthetic:offline-catalog",
                    "source_version":"test-v1","validated_by":"TEST_FIXTURE_ONLY",
                    "facts":{"synthetic:style-a":True,"synthetic:style-b":False}}
            knowledge=SyntheticKnowledgeEngine().resolve(service_id=SYNTHETIC_SERVICE,fixture=source)
            checked(knowledge,"knowledge")
            recommendation=SyntheticDecisionEngine().decide(analysis=analysis,knowledge=knowledge)
            checked(recommendation,"recommendation")

    def test_unknown_evidence_and_empty_source_are_schema_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            scoped=Scoped()
            c=ConsultationEngine(tmp+"/consultation.sqlite",scoped)
            records=SyntheticEvidenceEngine(c).collect_non_media(scoped.p,scoped.sid)
            for record in records: checked(record,"evidence")
            analysis=SyntheticBeautyAnalysis().analyse(session_id=scoped.sid,evidence=records)
            checked(analysis,"analysis")
            knowledge=SyntheticKnowledgeEngine().resolve(service_id=SYNTHETIC_SERVICE)
            checked(knowledge,"knowledge")
            decision=SyntheticDecisionEngine().decide(analysis=analysis,knowledge=knowledge)
            checked(decision,"recommendation")
            self.assertEqual(decision["candidates"],[])

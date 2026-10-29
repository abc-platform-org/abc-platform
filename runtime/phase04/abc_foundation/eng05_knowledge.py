"""ENG05 versioned knowledge retrieval with explicit unverified-source denial.

No commercial knowledge base is bundled. A synthetic source is accepted only
for the self-contained offline fixture; it does not certify any beauty advice.
"""
from datetime import datetime,timezone
import uuid

from .eng02_consultation import SYNTHETIC_SERVICE
from .store import DomainError


class SyntheticKnowledgeEngine:
    ENGINE_ID="ENG-05"
    ONTOLOGY_VERSION="synthetic-ontology.1"

    def resolve(self, *, service_id, fixture=None):
        if service_id!=SYNTHETIC_SERVICE:
            raise DomainError(403,"unreleased_service")
        sources=[]
        facts=[]
        unknowns=[]
        if fixture is None:
            unknowns=["SOURCE_UNVERIFIED"]
        else:
            # No user/client content is allowed to masquerade as a source.
            if (not isinstance(fixture,dict) or
                fixture.get("kind")!="SYNTHETIC_TEST_FIXTURE" or
                fixture.get("source_id")!="synthetic:offline-catalog" or
                fixture.get("source_version")!="test-v1" or
                fixture.get("validated_by")!="TEST_FIXTURE_ONLY" or
                set(fixture.get("facts",{}))!={"synthetic:style-a","synthetic:style-b"} or
                set(fixture["facts"].values())!={True,False}):
                raise DomainError(422,"unverified_knowledge_source")
            sources=[{"source_id":fixture["source_id"],
                      "source_version":fixture["source_version"],
                      "validated_by":"TEST_FIXTURE_ONLY"}]
            facts=[{"key":key,"value":value,"source_id":fixture["source_id"]}
                   for key,value in sorted(fixture["facts"].items())]
            unknowns=["NO_PROFESSIONAL_SOURCE_REVIEW","SYNTHETIC_FIXTURE_ONLY"]
        return {
            "knowledge_package_id":str(uuid.uuid4()),
            "ontology_version":self.ONTOLOGY_VERSION,
            "service_id":SYNTHETIC_SERVICE,
            "retrieval_sources":sources,"grounded_facts":facts,
            "created_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
            "unknowns":unknowns
        }

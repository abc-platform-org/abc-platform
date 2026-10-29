"""ENG06 bounded hard-filter decision adapter for synthetic offline evidence.

Never yields a released service recommendation, chemical/medical procedure,
scientific probability, third invented option or specialist approval.
"""
from datetime import datetime,timezone
import hashlib
import json
import uuid

from .eng02_consultation import SYNTHETIC_SERVICE
from .store import DomainError


class SyntheticDecisionEngine:
    ENGINE_ID="ENG-06"
    VERSION="eng06.synthetic.1"
    OPTIONS=("synthetic:style-a","synthetic:style-b")

    def decide(self, *, analysis, knowledge):
        if not isinstance(analysis,dict) or not isinstance(knowledge,dict):
            raise DomainError(400,"invalid_decision_inputs")
        if analysis.get("service_id")!=SYNTHETIC_SERVICE or knowledge.get("service_id")!=SYNTHETIC_SERVICE:
            raise DomainError(403,"service_scope_mismatch")
        try:
            sid=str(uuid.UUID(analysis["session_id"]))
        except (KeyError,TypeError,ValueError,AttributeError):
            raise DomainError(400,"invalid_session_id") from None
        attrs=analysis.get("attributes")
        if not isinstance(attrs,list) or len(attrs)!=4:
            raise DomainError(422,"incomplete_analysis")
        observations={}
        for item in attrs:
            if (not isinstance(item,dict) or item.get("key") in observations
                    or item.get("evidence_class") not in ("UNKNOWN","USER_REPORTED")
                    or not isinstance(item.get("source_evidence_id"),str)
                    or not item["source_evidence_id"]):
                raise DomainError(422,"invalid_analysis_provenance")
            observations[item.get("key")]=item
        if set(observations)!={"prior_treatment","sensitivity_flag","goal","maintenance"}:
            raise DomainError(422,"unexpected_analysis_fields")
        analysis_evidence=set(analysis.get("evidence_ids",[]))
        if not analysis_evidence or any(x["source_evidence_id"] not in analysis_evidence for x in observations.values()):
            raise DomainError(422,"unbound_analysis_evidence")
        if any(x["evidence_class"]=="UNKNOWN" and x["value"] is not None for x in observations.values()):
            raise DomainError(422,"unknown_cannot_be_inferred")
        if not isinstance(knowledge.get("retrieval_sources"),list) or not isinstance(knowledge.get("grounded_facts"),list):
            raise DomainError(422,"invalid_knowledge")
        source=knowledge["retrieval_sources"]
        fixtures=(len(source)==1 and source[0].get("source_id")=="synthetic:offline-catalog"
                  and source[0].get("source_version")=="test-v1"
                  and source[0].get("validated_by")=="TEST_FIXTURE_ONLY")
        source_id=source[0]["source_id"] if fixtures else None
        facts={}
        for fact in knowledge["grounded_facts"]:
            if (not isinstance(fact,dict) or fact.get("key") in facts
                    or fact.get("key") not in self.OPTIONS
                    or type(fact.get("value")) is not bool
                    or fact.get("source_id")!=source_id):
                raise DomainError(422,"unverified_decision_fact")
            facts[fact["key"]]=fact["value"]
        if fixtures and set(facts)!=set(self.OPTIONS):
            raise DomainError(422,"incomplete_synthetic_catalog")
        if not fixtures and facts:
            raise DomainError(422,"unverified_decision_source")
        critical_missing=any(observations[key]["value"] in (None,"UNKNOWN")
                             for key in ("prior_treatment","sensitivity_flag"))
        flagged=observations["sensitivity_flag"]["value"]=="YES"
        unsafe=(critical_missing or flagged or observations["goal"]["value"] is None)
        candidates=[]
        exclusions=[]
        for name in self.OPTIONS:
            if not fixtures:
                reason="UNVERIFIED_KNOWLEDGE_SOURCE"
            elif unsafe:
                reason="CRITICAL_EVIDENCE_OR_SPECIALIST_REVIEW_REQUIRED"
            elif not facts.get(name,False):
                reason="SYNTHETIC_CAPABILITY_FILTER_FAILED"
            else:
                candidates.append({
                    "candidate_id":name,
                    "look_spec_id":"synthetic:unreleased-look-spec-"+name.split(":")[-1],
                    "reason":"SYNTHETIC_TEST_ONLY_REQUIRES_PROFESSIONAL_REVIEW",
                    "hard_filter_status":"CONDITIONALLY_PASSED",
                    "feasibility_label":"PROFESSIONAL_CHECK_REQUIRED",
                    "evidence_ids":sorted(analysis_evidence),
                    "maintenance_tradeoffs":["NOT_EVALUATED_IN_REAL_CLIENT_CONTEXT"]
                })
                continue
            exclusions.append({"candidate_id":name,"reason":reason})
        stable_hash=hashlib.sha256(json.dumps([sid,sorted(analysis_evidence),
                                sorted(facts.items()),unsafe],sort_keys=True).encode()).hexdigest()
        return {
            "recommendation_set_id":str(uuid.uuid5(uuid.NAMESPACE_URL,"eng06:"+stable_hash)),
            "session_id":sid,"service_id":SYNTHETIC_SERVICE,
            "candidates":candidates,"excluded_options":exclusions,
            "blocking_evidence_ids":sorted(analysis_evidence) if unsafe else [],
            "decision_engine_version":self.VERSION,
            "created_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
        }

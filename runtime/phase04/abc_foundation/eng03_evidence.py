"""ENG03 synthetic non-media evidence integrity adapter.

No image ingestion or visual QA is claimed. Never elevate client/specialist
responses into OBSERVED facts, validated diagnoses or physical feasibility.
"""
from datetime import datetime, timezone
import uuid

from .eng02_consultation import SYNTHETIC_SERVICE
from .store import DomainError


class SyntheticEvidenceEngine:
    ENGINE_ID="ENG-03"
    def __init__(self, consultation):
        if not callable(getattr(consultation,"_authorized",None)):
            raise ValueError("verified_consultation_source_required")
        self.consultation=consultation

    def collect_non_media(self, principal, session_id):
        scoped=self.consultation._authorized(principal,session_id)
        if scoped.get("service_id")!=SYNTHETIC_SERVICE:
            raise DomainError(403,"synthetic_service_only")
        with self.consultation._connect() as con:
            answers=self.consultation._read_answers(con,scoped)
        fields=[]
        stamp=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
        for question in sorted(self.consultation.questions.values(),key=lambda q:q["field"]):
            answer=answers.get(question["question_id"])
            if answer is None or answer["value"] in ("UNKNOWN","UNSURE"):
                fields.append({
                    "evidence_id":str(uuid.uuid5(uuid.NAMESPACE_URL,scoped["session_id"]+"|"+question["field"]+"|missing")),
                    "session_id":scoped["session_id"],"service_id":SYNTHETIC_SERVICE,
                    "attribute_key":question["field"],"value":None,
                    "evidence_class":"UNKNOWN","source_type":"NOT_AVAILABLE",
                    "captured_at":stamp,
                    "criticality":"EXECUTION_REQUIRED" if question["critical"] else "RECOMMENDATION_REQUIRED",
                    "confidence_label":"UNRATED"
                })
            else:
                # A specialist-entered response is NOT equivalent to physical
                # observation, verified sensitivity or scientific diagnosis.
                fields.append({
                    "evidence_id":answer["answer_id"],
                    "session_id":scoped["session_id"],"service_id":SYNTHETIC_SERVICE,
                    "attribute_key":question["field"],"value":answer["value"],
                    "evidence_class":"USER_REPORTED",
                    "source_type":"CLIENT_ANSWER",
                    "source_id":answer["answer_id"],"captured_at":stamp,
                    "criticality":"EXECUTION_REQUIRED" if question["critical"] else "RECOMMENDATION_REQUIRED",
                    "confidence_label":"UNRATED"
                })
        return fields

    def validate_media(self,*args,**kwargs):
        raise DomainError(501,"real_media_and_consent_gate_not_implemented")

"""Independent ENG14 synthetic QUESTION interceptor; not expert clearance."""
from datetime import datetime, timezone
import uuid
from .store import DomainError

class SyntheticQuestionPolicy:
    ENGINE_ID = "ENG-14"
    VERSION = "eng14.synthetic.1"

    def evaluate(self, *, command_id, tenant_id, session_id, service_id,
                 state, answers, question_id, expected_question, profile_version):
        if not isinstance(answers,dict) or not all(
            isinstance(v,str) and v for v in (command_id,tenant_id,session_id)
        ):
            raise DomainError(503,"policy_context_unavailable")
        reasons=[]
        if service_id!="synthetic:hair-color" or profile_version!="synthetic-1.0.0":
            reasons.append("UNAPPROVED_SERVICE_PROFILE")
        if state!="CREATED":
            reasons.append("SESSION_NOT_ACTIVE")
        if answers.get("synthetic:prior-treatment")=="UNKNOWN":
            reasons.append("CRITICAL_UNKNOWN")
        if answers.get("synthetic:sensitivity") in ("YES","UNKNOWN"):
            reasons.append("SENSITIVITY_REVIEW_REQUIRED")
        if not expected_question or question_id!=expected_question:
            reasons.append("QUESTION_SEQUENCE")
        return {
            "policy_decision_id":str(uuid.uuid5(uuid.NAMESPACE_URL,
                                           "eng14:question:"+command_id)),
            "scope":"QUESTION","decision":"BLOCK" if reasons else "ALLOW",
            "safety_tier":"S0","reason_codes":sorted(set(reasons)) if reasons else ["SYNTHETIC_QUESTION_ONLY"],
            "evaluated_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
            "policy_version":self.VERSION,"session_id":session_id,
            "tenant_id":tenant_id,
            "required_checks":["VERIFIED_DUAL_IDENTITY","ACTIVE_DB_GRANTS",
                               "ASSIGNED_SPECIALIST","CURRENT_STATE_VERSION",
                               "SYNTHETIC_ONLY","QUESTION_ORDER","SAFETY_STOP"]
        }

    def require_allow(self,decision):
        if (not isinstance(decision,dict) or decision.get("scope")!="QUESTION"
            or decision.get("decision")!="ALLOW"
            or decision.get("policy_version")!=self.VERSION
            or decision.get("safety_tier")!="S0"
            or decision.get("reason_codes")!=["SYNTHETIC_QUESTION_ONLY"]):
            raise DomainError(409,"eng14_policy_blocked")

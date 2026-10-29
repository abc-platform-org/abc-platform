"""ENG14 professional-risk evidence gate: conservative REVIEW/BLOCK classifier.

NOT a treatment protocol, qualification verifier, consent issuer or executor.
No S1-S3 state transition is authorized by this module. Qualified professional
signoff, reviewed service SOP and executable transition authorization are absent.
"""
from dataclasses import dataclass
import re

# Proposed conservative policy classification; clinical/professional review pending.
_REQUIREMENTS = {
    "HAIRCUT": ("current_condition","target_look","feasibility_review"),
    "HAIR_COLOR": ("current_condition","chemical_history","sensitivity_screen",
                   "product_compatibility","strand_patch_assessment",
                   "target_look","qualified_specialist_review"),
    "KERATIN": ("current_condition","chemical_history","sensitivity_screen",
                "ingredient_and_ventilation_review","qualified_specialist_review"),
    "SKIN": ("current_condition","contraindication_screen","scope_of_practice",
             "qualified_specialist_review"),
    "NAILS": ("current_condition","sensitivity_screen","material_compatibility",
              "qualified_specialist_review"),
    "BEARD": ("current_condition","target_look","feasibility_review"),
    "MAKEUP": ("current_condition","sensitivity_screen","product_compatibility"),
    "EXTENSIONS": ("current_condition","attachment_suitability",
                   "tension_and_care_review","qualified_specialist_review"),
    "CORRECTIVE": ("current_condition","history_and_prior_failures",
                    "material_compatibility","qualified_specialist_review"),
}
_RISK = {"HAIRCUT":"S1","HAIR_COLOR":"S3","KERATIN":"S3","SKIN":"S3",
         "NAILS":"S2","BEARD":"S1","MAKEUP":"S2",
         "EXTENSIONS":"S2","CORRECTIVE":"S3"}
_DIGEST = re.compile(r"^[a-f0-9]{64}$")


@dataclass(frozen=True)
class ProfessionalGate:
    VERSION = "eng14.professional.review-candidate.1"

    def assess(self, *, service, evidence, tenant_id, session_id, specialist_id,
               state_version, consent_proof=None, sop_approval=None):
        """Return auditable negative / review-readiness result, never ALLOW."""
        if (type(state_version) is not int or state_version < 0
            or not all(isinstance(v,str) and v.strip()
                       for v in (tenant_id,session_id,specialist_id))):
            return self._block("INVALID_SESSION_BINDING", service, "UNREVIEWED", ())
        if service not in _REQUIREMENTS:
            return self._block("SERVICE_PROFILE_NOT_APPROVED", service,"UNREVIEWED",())
        req=_REQUIREMENTS[service]
        if not isinstance(evidence,dict):
            return self._block("EVIDENCE_MISSING",service,_RISK[service],req)
        missing=[];invalid=[]
        for key in req:
            item=evidence.get(key)
            if item is None:
                missing.append(key)
                continue
            if (not isinstance(item,dict)
                or item.get("tenant_id")!=tenant_id
                or item.get("session_id")!=session_id
                or item.get("state_version")!=state_version
                or item.get("review_status")!="RECORDED_NOT_APPROVED"
                or not isinstance(item.get("digest"),str)
                or not _DIGEST.fullmatch(item["digest"])
                or not isinstance(item.get("source_ref"),str)
                or not item["source_ref"].strip()):
                invalid.append(key)
        if invalid:
            return self._block("EVIDENCE_SCOPE_OR_PROVENANCE_INVALID",
                               service,_RISK[service],tuple(invalid))
        if missing:
            return self._block("REQUIRED_EVIDENCE_MISSING",
                               service,_RISK[service],tuple(missing))
        # These fields are explicitly untrusted submissions; a caller cannot
        # manufacture a qualification, consent or signed SOP approval.
        # Independent registries and verified human signoff are not built yet.
        return self._block("AWAITING_INDEPENDENT_PROFESSIONAL_AND_CONSENT_APPROVAL",
                           service,_RISK[service],(),
                           evidence_complete=True)

    def _block(self,reason,service,risk,required,evidence_complete=False):
        return {"engine_id":"ENG-14","version":self.VERSION,
                "decision":"BLOCK","risk_class":risk,
                "service":service if isinstance(service,str) else "UNKNOWN",
                "reason":reason,"required_evidence":list(required),
                "evidence_complete_for_review":evidence_complete,
                "execution_approved":False,
                "state_transition_approved":False,
                "human_approval_verified":False,
                "consent_verified":False,
                "policy_scope":"SYNTHETIC_DESIGN_ONLY"}

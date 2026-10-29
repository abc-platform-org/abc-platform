"""ENG04 source-bounded, non-medical analysis of synthetic non-media inputs.

No computer vision or AI model. Does not infer chemical compatibility from
images or reported facts and never invents confidence percentages.
"""
from datetime import datetime,timezone
import hashlib
import json
import uuid

from .eng02_consultation import SYNTHETIC_SERVICE
from .store import DomainError

FIELDS=frozenset(("prior_treatment","sensitivity_flag","goal","maintenance"))


class SyntheticBeautyAnalysis:
    ENGINE_ID="ENG-04"
    ENGINE_VERSION="eng04.synthetic-evidence.1"

    def analyse(self, *, session_id, evidence):
        try:
            sid=str(uuid.UUID(session_id))
        except (TypeError,ValueError,AttributeError):
            raise DomainError(400,"invalid_session_id") from None
        if not isinstance(evidence,list) or not evidence:
            raise DomainError(422,"missing_evidence")
        attrs=[]
        unknowns=[]
        evidence_ids=set()
        fields=set()
        notes=[]
        for record in evidence:
            if not isinstance(record,dict):
                raise DomainError(400,"invalid_evidence")
            key=record.get("attribute_key")
            eid=record.get("evidence_id")
            if (key not in FIELDS or key in fields or not isinstance(eid,str)
                    or not eid or eid in evidence_ids
                    or record.get("service_id")!=SYNTHETIC_SERVICE
                    or record.get("session_id")!=sid
                    or record.get("evidence_class") not in ("UNKNOWN","USER_REPORTED")):
                raise DomainError(422,"evidence_scope_or_provenance_mismatch")
            fields.add(key);evidence_ids.add(eid)
            if record["evidence_class"]=="UNKNOWN":
                if record.get("source_type")!="NOT_AVAILABLE" or record.get("value") is not None:
                    raise DomainError(422,"unknown_evidence_invalid")
                unknowns.append(key)
                attrs.append({"key":key,"value":None,"evidence_class":"UNKNOWN",
                              "source_evidence_id":eid})
            else:
                if (record.get("source_type")!="CLIENT_ANSWER"
                    or record.get("value") is None
                    or not isinstance(record.get("value"),str)):
                    raise DomainError(422,"unverified_observation_disallowed")
                attrs.append({"key":key,"value":record["value"],
                              "evidence_class":"USER_REPORTED","source_evidence_id":eid})
                if key=="sensitivity_flag" and record["value"]=="YES":
                    notes.append("REPORTED_SENSITIVITY_REQUIRES_SPECIALIST_REVIEW")
        if fields!=FIELDS:
            raise DomainError(422,"incomplete_evidence_profile")
        canonical=[(x["key"],x["value"],x["source_evidence_id"]) for x in attrs]
        h=hashlib.sha256(json.dumps([sid,canonical],sort_keys=True).encode()).hexdigest()
        return {
            "analysis_id":str(uuid.uuid5(uuid.NAMESPACE_URL,"eng04:"+h)),
            "session_id":sid,"service_id":SYNTHETIC_SERVICE,
            "engine_version":self.ENGINE_VERSION,
            "evidence_ids":sorted(evidence_ids),
            "attributes":sorted(attrs,key=lambda x:x["key"]),
            "unknowns":sorted(unknowns),"safety_notes":notes,
            "created_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
            "service_scope":"SYNTHETIC_NON_MEDIA_ONLY"
        }

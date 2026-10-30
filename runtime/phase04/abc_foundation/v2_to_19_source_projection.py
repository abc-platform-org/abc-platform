"""ENG16 bridge only validates source-record bytes, never a specialist."""
from .professional_sources_v2 import ProfessionalSourceRegistry
from .store import DomainError
from .v2_to_19_projection import _emit,_validate_pair

def project_signed_source_to_eng16(*,request,response,registry):
    _validate_pair(request,response,"ENG-06")
    if not isinstance(registry,ProfessionalSourceRegistry):
        raise DomainError(403,"independent_professional_source_registry_required")
    ref=request["payload"]["approved_sop_ref"]
    if ref is None:
        raise DomainError(403,"source_reference_missing")
    try:
        verified=registry.verify(ref=ref,record_type="SOP",
                                 service_kind=request["payload"]["service_kind"])
    except (ValueError,TypeError,KeyError,RuntimeError):
        verified=False
    payload={"source_status":response["result"]["status"],
             "source_ref":ref,"source_record_type":"SOP",
             "signed_source_content_verified":verified is True,
             "independent_specialist_qualification_verified":False,
             "professional_validation_complete":False}
    return _emit(request,response,"A06_SOURCE_TO_16_REVIEW_EVIDENCE",payload)

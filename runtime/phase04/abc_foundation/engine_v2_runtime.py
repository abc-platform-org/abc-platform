"""Bounded v2 engine execution in a local controlled test environment ONLY.

This is three versioned backend implementations, not a general model broker.
No cloud identity, network listener, real client ingestion or release path.
"""
import os
from .engine_v2_contracts import _FIELDS,FILES,VERSION,validate_port
from .eng04_recommendation_v2 import recommend
from .eng05_decision_v2 import decide
from .eng06_technical_plan_v2 import plan
from .store import DomainError


def execute(message,*,engine,evidence_gate=None):
    if os.environ.get("ABC_ENV")!="LOCAL_INTEGRATION_ONLY":
        raise DomainError(403,"v2_unapproved_execution_environment")
    if engine not in FILES:
        raise DomainError(400,"unknown_v2_engine")
    validate_port(message,engine=engine)
    if engine=="ENG-04":
        result=recommend(message)
    elif engine=="ENG-05":
        result=decide(message)
    else:
        result=plan(message,evidence_gate=evidence_gate)
    response={key:message[key] for key in _FIELDS if key!="payload"}
    response.update({"result":result,"release_approved":False,
                     "execution_authorized":False})
    validate_port(response,engine=engine,response=True,request=message)
    return response

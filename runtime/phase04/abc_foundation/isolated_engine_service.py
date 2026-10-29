"""Versioned JSON-line engine service: one independent OS process per engine.

This is a synthetic process boundary and CONTRACT prototype, NOT a cloud service
or a substitute for authenticated mTLS deployment. No network or DB credentials.
"""
import json
from pathlib import Path
from jsonschema import Draft202012Validator,FormatChecker
import sys
import uuid

from .eng02_consultation import SYNTHETIC_SERVICE
from .eng04_analysis import SyntheticBeautyAnalysis
from .eng05_knowledge import SyntheticKnowledgeEngine
from .eng06_decision import SyntheticDecisionEngine
from .store import DomainError

VERSION="abc.internal.engine.synthetic.v1"
_CONTRACTS=json.loads(Path(__file__).with_name("internal_engine_ports.v1.json").read_text())
_INPUT=Draft202012Validator(_CONTRACTS["request"],format_checker=FormatChecker())
_OUTPUT=Draft202012Validator(_CONTRACTS["response"],format_checker=FormatChecker())
Draft202012Validator.check_schema(_CONTRACTS["request"])
Draft202012Validator.check_schema(_CONTRACTS["response"])
ENGINES=("ENG-04","ENG-05","ENG-06")
_ALLOWED={"request_id","engine_id","contract_version","consumer_id","session_id","payload"}


def validate(message,engine_id):
    if (not isinstance(message,dict) or set(message)!=_ALLOWED
        or message.get("engine_id")!=engine_id
        or message.get("contract_version")!=VERSION
        or not isinstance(message.get("consumer_id"),str)
        or not 3<=len(message["consumer_id"])<=96):
        raise DomainError(400,"invalid_engine_service_contract")
    for field in ("request_id","session_id"):
        try:
            if str(uuid.UUID(message[field]))!=message[field]:
                raise ValueError()
        except (ValueError,KeyError,TypeError,AttributeError):
            raise DomainError(400,"invalid_engine_service_identifier") from None
    if not isinstance(message.get("payload"),dict):
        raise DomainError(400,"invalid_engine_payload")
    if not _INPUT.is_valid(message):
        raise DomainError(400,"engine_port_json_schema_rejected")


def dispatch(message,engine_id):
    if engine_id not in ENGINES:
        raise DomainError(501,"unknown_engine_process")
    validate(message,engine_id)
    payload=message["payload"]
    if engine_id=="ENG-04":
        if set(payload)!={"evidence"}:
            raise DomainError(400,"eng04_input_contract")
        result=SyntheticBeautyAnalysis().analyse(
            session_id=message["session_id"],evidence=payload["evidence"])
    elif engine_id=="ENG-05":
        if set(payload)!={"service_id","fixture"} or payload["service_id"]!=SYNTHETIC_SERVICE:
            raise DomainError(400,"eng05_input_contract")
        result=SyntheticKnowledgeEngine().resolve(service_id=payload["service_id"],
                                                     fixture=payload["fixture"])
    else:
        if set(payload)!={"analysis","knowledge"}:
            raise DomainError(400,"eng06_input_contract")
        if payload["analysis"].get("session_id")!=message["session_id"]:
            raise DomainError(403,"cross_session_engine_input")
        result=SyntheticDecisionEngine().decide(
             analysis=payload["analysis"],knowledge=payload["knowledge"])
    if not isinstance(result,dict):
        raise DomainError(500,"engine_result_invalid")
    response={"request_id":message["request_id"],"engine_id":engine_id,
              "contract_version":VERSION,"consumer_id":message["consumer_id"],
              "session_id":message["session_id"],"result":result,
              "release_approved":False}
    if not _OUTPUT.is_valid(response):
        raise DomainError(500,"engine_output_schema_rejected")
    return response


def main():
    if len(sys.argv)!=2 or sys.argv[1] not in ENGINES:
        raise SystemExit(2)
    try:
        raw=sys.stdin.buffer.read(262145)
        if len(raw)>262144 or not raw:
            raise DomainError(413,"oversized_engine_message")
        response=dispatch(json.loads(raw),sys.argv[1])
        sys.stdout.write(json.dumps(response,sort_keys=True,separators=(",",":")))
    except (DomainError,ValueError,TypeError,UnicodeDecodeError,KeyError) as exc:
        code=getattr(exc,"code","invalid_engine_message")
        sys.stdout.write(json.dumps({"error":code,"release_approved":False}))
        raise SystemExit(3)


if __name__=="__main__":
    main()

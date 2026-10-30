"""One request per dedicated ENG04/05/06 OS process, synthetic only.

Use: ABC_ENV=LOCAL_INTEGRATION_ONLY python -m abc_foundation.engine_v2_worker ENG-04
This is a disposable local test harness, NOT a cloud or authorized service.
"""
import json
import sys

from .engine_v2_contracts import FILES
from .engine_v2_runtime import execute
from .store import DomainError


def main():
    if len(sys.argv)!=2 or sys.argv[1] not in FILES:
        raise SystemExit(2)
    engine=sys.argv[1]
    try:
        raw=sys.stdin.buffer.read(131073)
        if not raw or len(raw)>131072:
            raise DomainError(413,"v2_request_size_invalid")
        request=json.loads(raw.decode("utf-8"))
        response=execute(request,engine=engine)
        sys.stdout.write(json.dumps(response,sort_keys=True,
                        separators=(",",":"),allow_nan=False))
    except (DomainError,UnicodeError,ValueError,TypeError,KeyError,
            OverflowError,RecursionError) as exc:
        # Internal exception details, user media, evidence or secrets
        # must never be serialized to a response or process logs.
        sys.stdout.write(json.dumps({"engine_id":engine,
            "error":"CONTROLLED_ENGINE_REQUEST_DENIED",
            "release_approved":False,"execution_authorized":False}))
        raise SystemExit(3)


if __name__=="__main__":
    main()

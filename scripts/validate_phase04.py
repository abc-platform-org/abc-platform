"""Phase-04 frozen API inventory and local foundation authority validator."""
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
api=json.loads((ROOT/"contracts/v1/openapi.json").read_text())
expected={(value["operationId"],verb.upper(),path)
          for path,methods in api["paths"].items()
          for verb,value in methods.items()
          if isinstance(value,dict) and "operationId" in value}
with (ROOT/"docs/04-platform/API_IMPLEMENTATION_MATRIX.csv").open(newline="") as handle:
    rows=list(csv.DictReader(handle))
mapped={(r["operation_id"],r["method"],r["path"]) for r in rows}
assert len(expected)==41 and len(rows)==41 and len(mapped)==41 and expected==mapped
implemented={r["operation_id"] for r in rows if r["implementation"]=="LOCAL_HARNESS_ONLY"}
assert implemented=={"createConsultation","getConsultation"}
assert all(r["release"]=="NOT_RELEASED" for r in rows)
assert all(r["implementation"] in ("NOT_IMPLEMENTED","LOCAL_HARNESS_ONLY") for r in rows)
runtime=(ROOT/"runtime/phase04/abc_foundation/http_api.py").read_text()
assert '"/v1/consultations"' in runtime and "SESSION_RE" in runtime
assert '"/_foundation/v0/' in runtime
assert "capability_not_implemented" in runtime
print("PASS: 41 exact v1 operations; 2 local-harness only; 39 not implemented; no release")

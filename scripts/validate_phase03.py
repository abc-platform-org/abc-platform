"""Checks referential integrity, not UX or runtime certification."""
import csv,json,pathlib,re
ROOT=pathlib.Path(__file__).resolve().parents[1]
D=ROOT/'docs/03-design/phase-03'
api=json.loads((ROOT/'contracts/v1/openapi.json').read_text())
ops={v['operationId']:p for p,x in api['paths'].items() for v in x.values() if isinstance(v,dict) and 'operationId'in v}
machines=json.loads((ROOT/'contracts/v1/state-machines.json').read_text())
states=set(machines['machines'][0]['states'])
rows=json.loads((D/'SCREEN_CONTRACT_MAP.json').read_text())
assert len(rows)==15 and len({r['screen_id']for r in rows})==15
for row in rows:
 assert row['state']in states
 for op in row['api_operations']:assert ops[op['operation_id']]==op['path']
source=list(csv.DictReader((ROOT/'docs/01-product/phase-01/FEATURE_RELEASE_MATRIX.csv').open()))
coverage=list(csv.DictReader((D/'REQUIREMENT_COVERAGE.csv').open()))
assert len(coverage)==64 and {r['id']for r in source}=={r['requirement_id']for r in coverage}
assert all(r['runtime_status']=='NOT_IMPLEMENTED' for r in coverage)
add=json.loads((ROOT/'contracts/phase03/revision-transition-addendum.json').read_text())
assert add['to']in states and set(add['from'])<=states
assert not set(add['from'])&set(add['forbidden_from'])
html=(ROOT/'prototypes/phase03/index.html').read_text()
assert 'lang="fa"'in html and 'dir="rtl"'in html and 'aria-live="polite"'in html
js=(ROOT/'prototypes/phase03/app.mjs').read_text()
assert not re.search(r'fetch\(|XMLHttpRequest|getUserMedia|localStorage',js)
print('PASS: 15 screen contracts; 64 requirement dispositions; additive revision proposal; no live data APIs.')

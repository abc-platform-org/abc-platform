#!/usr/bin/env python3
"""WP-000-02 *documentation integrity* checks, not runtime tests."""
from pathlib import Path
import csv,re
root=Path(__file__).resolve().parents[1]
base=root/'docs/00-governance/phase-00/wp-000-02'
required=['README.md','SOURCE_RECOVERY_LOG.md','SOURCE_EXCEPTIONS.md','AUTHORITY_RESOLUTION.md','LEGACY_AGENT_TO_ENGINE_MAP.md','ADR_REVIEW_PACKAGE.md','INTERFACE_GOVERNANCE.md','MIGRATION_DISPOSITION.csv','DECISION_REGISTER.csv','BLOCKER_ACTION_REGISTER.csv','QA_EVIDENCE_REQUIREMENTS.md','REVIEW_AND_SIGNOFF.md','GATE_00_REASSESSMENT.md']
assert all((base/p).exists() for p in required), 'Missing WP-000-02 artifact'
with (base/'MIGRATION_DISPOSITION.csv').open(newline='',encoding='utf-8') as f:migs=list(csv.DictReader(f))
assert {r['migration_id'] for r in migs}=={f'MIG-{i:02d}' for i in range(1,21)}
assert not any(r['wp00002_state'] in {'IMPLEMENTED','ACCEPTED','PASSED'} for r in migs)
with (base/'DECISION_REGISTER.csv').open(newline='',encoding='utf-8') as f:dec=list(csv.DictReader(f))
assert len(dec)==13 and len({r['decision_id'] for r in dec})==13
assert all(r['status'] not in {'APPROVED','ACCEPTED'} for r in dec)
with (base/'BLOCKER_ACTION_REGISTER.csv').open(newline='',encoding='utf-8') as f:blockers=list(csv.DictReader(f))
assert len(blockers)==14 and len({r['blocker_id'] for r in blockers})==14
r=(base/'AUTHORITY_RESOLUTION.md').read_text(encoding='utf-8')
assert len(re.findall(r'^\| RES-\d{2} \|',r,re.M))==13
m=(base/'LEGACY_AGENT_TO_ENGINE_MAP.md').read_text(encoding='utf-8')
assert len(re.findall(r'^\| AG-\d{2} ',m,re.M))==10
for i in [1,2,8,9,10]:
 t=(root/f'docs/00-governance/adrs/ADR-{i:03d}.md').read_text(encoding='utf-8')
 assert 'PROPOSED_FOR_REVIEW' in t and 'WP-000-02' in t
for doc in ['GATE_00_REASSESSMENT.md','SOURCE_EXCEPTIONS.md','REVIEW_AND_SIGNOFF.md']:
 text=(base/doc).read_text(encoding='utf-8')
 assert 'APPROVAL' in text.upper() or 'PENDING' in text.upper()
assert 'BLOCKED_FOR_FORMAL_APPROVAL' in (base/'GATE_00_REASSESSMENT.md').read_text()
for p in base.glob('*.md'):
 txt=p.read_text(encoding='utf-8')
 for link in re.findall(r'(?<!!)\[[^]]+\]\(([^)]+)\)',txt):
  if link.startswith(('https://','http://','#')):continue
  assert (p.parent/link).exists(),f'{p}: bad relative link {link}'
print('WP00002 DOCUMENT INTEGRITY PASS:',len(required),'required artifacts,',len(migs),'migrations,',len(dec),'decisions,',len(blockers),'blockers, 13 resolution rows, 10 legacy AG mappings; Gate-00 NOT PASSED')

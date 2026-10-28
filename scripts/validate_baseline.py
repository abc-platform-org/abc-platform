#!/usr/bin/env python3
"""Stdlib-only validation for this documentation baseline; NOT a runtime or AI test."""
from pathlib import Path
import re, sys, hashlib, json
root = Path(__file__).resolve().parents[1]
required = [
    'README.md', 'docs/00-governance/PROJECT_CHARTER.md', 'docs/01-product/PRD.md',
    'docs/01-product/FEATURE_INVENTORY.md', 'docs/02-architecture/SYSTEM_ARCHITECTURE.md',
    'docs/02-architecture/ENGINE_REGISTRY.md', 'docs/03-ai-studio/AI_STUDIO_SPEC.md',
    'docs/03-ai-studio/ADAPTIVE_QUESTIONING.md', 'docs/03-ai-studio/VISUAL_PIPELINE.md',
    'docs/03-ai-studio/TECHNICAL_PLANNING.md', 'docs/05-delivery/MASTER_ROADMAP_16_PHASES.md',
    'docs/05-delivery/REQUIREMENTS_TRACEABILITY.md', 'docs/06-quality/TEST_STRATEGY.md',
]
problems=[]
for p in required:
    if not (root/p).is_file(): problems.append('Missing '+p)
for i in range(1,20):
    if not (root/f'docs/02-architecture/engines/ENG-{i:02}.md').is_file(): problems.append('Missing engine contract '+str(i))
for i in range(1,11):
    if not (root/f'docs/00-governance/adrs/ADR-{i:03}.md').is_file(): problems.append('Missing ADR '+str(i))
fi=(root/'docs/01-product/FEATURE_INVENTORY.md').read_text(encoding='utf-8')
pr=(root/'docs/01-product/PRD.md').read_text(encoding='utf-8')
for i in range(1,19):
    if f'ABC-F{i:02}' not in fi: problems.append('Feature missing ABC-F%02d'%i)
for i in range(1,27):
    if f'AIS-{i:03}' not in fi: problems.append('Studio feature missing AIS-%03d'%i)
for i in range(1,21):
    if f'PRD-{i:03}' not in pr: problems.append('PRD missing PRD-%03d'%i)
roadmap=(root/'docs/05-delivery/MASTER_ROADMAP_16_PHASES.md').read_text(encoding='utf-8')
for i in range(16):
    if f'Phase {i:02}' not in roadmap: problems.append('Phase missing %02d'%i)
# Original 70-file ZIP README cannot replace pre-existing repository root README.
# Treat the byte-exact copy as an immutable ARCHIVAL source, not as an active
# Markdown page: its original root-relative links are not valid at archival path.
archive_rel = 'docs/00-governance/original-package/README.2026-10-28.md'
archive = root / archive_rel
if archive.exists():
    manifest = json.loads((root/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    expected = manifest['files']['README.md']
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if expected != actual: problems.append('Original ZIP README archival SHA256 mismatch')
for md in root.rglob('*.md'):
    if md == archive:
        continue  # verified byte-identical archival original; see integration audit

    text=md.read_text(encoding='utf-8')
    for target in re.findall(r'(?<!\!)\[[^]]+\]\(([^)]+)\)',text):
        if target.startswith(('https://','http://','#','mailto:')):continue
        loc=target.split('#')[0].split('?')[0]
        if loc and not (md.parent/loc).exists(): problems.append(f'Broken relative link: {md.relative_to(root)} -> {target}')
print('DOC_INTEGRITY:', 'PASS' if not problems else 'FAIL')
print('CHECKED: 18 feature IDs, 26 AIS IDs, 20 PRD IDs, 19 engine docs, 10 ADRs, 16 phases, relative links')
for p in problems:print(' -',p)
sys.exit(1 if problems else 0)

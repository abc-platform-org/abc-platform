# ENG05 — reconcile sibling 0029 migration drafts

**1 November 2026.** Draft engineering reconciliation; Issue #70 remains OPEN. `main` and public deployment untouched.

## Confirmed facts
- PR #74 head `6f8dac14eedbdfb763d17e97714a96b28051c852`: Foundation CI run 41234218009 SUCCESS; Documentation Integrity 41234218085 SUCCESS. Actual BGW-hosted 2023 TRGS530 PDF: 741,429 bytes, 15 pages, SHA-256 `356fc7d7ef4d4dc56ae687c72dfbf00d156b65ae494553f15f0060d7b46b5628`; verified in ephemeral CI, **not a publisher signature**.
- Sibling PR #76 head `01410e4f56533d4e6631ee6583defd61cdaf8ec0`: another migration named 0029 with a different table. Both Draft PRs descend from #72; neither is merged into main.
- PR #75 also carries an independently developed 0029 migration and must not be blindly stacked or merged.

## Non-destructive implementation
1. Keep PR #74's `0029_eng05_official_pdf_byte_receipts.sql` byte-for-byte. This is technical actual-source-byte provenance, NOT a right to commercial use or professional advice.
2. Carry forward PR #76's **distinct table-only** untrusted offline observation feature as `0030_eng05_trgs530_byte_observations.sql`. Never overwrite migration 0029 or revise historical checksum receipts.
3. Existing PR #74 `scripts/eng05_trgs530_pdf_byte_probe.py --input-file` already validates local input with a strict PDF parser; duplicating the weaker header/EOF-only observation CLI from #76 is unnecessary. PR #76 itself remains an unmerged draft and its historical claims of inaccessible PDF bytes must not override the later verified CI receipt.
4. The migration manifest, count, RLS smoke test and negative unit/PostgreSQL tests are updated. No ENG05 review worker is connected to either ledger.

## Mandatory external blockers
- BAuA official register and publisher edition currentness independently confirmed at sign-off; issuer-signed file provenance if required.
- German commercial use and text-ingestion rights, including `UrhG §5`, with independent competent legal review.
- Independent credential issuer, public-key trust, expiry/revocation, conflict-of-interest separation; qualified professional signatures (two distinct signers for safety-critical claims) and conflict adjudication.
- Ratified ADR-ENG-003/004, managed service identity and private operational acceptance.

**Fixed disposition:** `professionally_released_facts=[]`; `ENG05→ENG06=BLOCKED_PENDING_AUTHORITY`; customer release false. No operator claim or observed hash may flip these states. No production or paid-API work.

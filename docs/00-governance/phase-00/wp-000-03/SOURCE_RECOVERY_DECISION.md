# WP-000-03 — Provenance, Source Recovery and Bounded Exception Decisions

**As of 2026-10-29:** `DOC-001 v1.2.0`, `DOC-005 v1.1.0` and `ABC-CCR-001 v1.1.0` remain **referenced but unrecovered**. Source mentions do not create source authority.

## Version-specific treatment

| Missing reference | Verified nearby version or source | May be used for | May NOT be used for | Unresolved action |
|---|---|---|---|---|
| `DOC-001 v1.2.0` | Notion canonical `ABC-DOC-001 v1.1.0`; user-confirmed Oct 2026 scope | Legacy scope that is actually written; independently confirmed current product direction | Asserting unrecovered v1.2 clauses or automatic supersession | [#2](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/2), source or signed `SRC-EXC-001` |
| `DOC-005 v1.1.0` | Notion DOC-005 `v1.0.2`, ten **logical** GPT agents | Historic agent semantics and migration reference | Claiming v1.1 or independent service implementations | [#2](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/2), source or signed `SRC-EXC-002` |
| `ABC-CCR-001 v1.1.0` | Productization DOC-007 v1.1.0 directly written candidate rules | Bounded candidate interpretation of its own written text | Quoting missing CCR content, treating it as approved change record | [#2](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/2), source or signed `SRC-EXC-003` |

## Required disposition for each item

**Route A: Recovery.** Record exact canonical URL/file, version, complete relevant text, SHA-256 when raw bytes exist, retrieval date, reviewer, alignment/conflict with target ADRs. After review mark `SOURCE_VERIFIED`.

**Route B: Exception.** Sign exception individually, with reviewer name/role, reviewed decision artifact SHA, scope, authority fallback, rule exclusions, risk owner, expiry/revisit trigger, test and migration obligations. Mark `EXCEPTION_ACCEPTED` **only after** human evidence.

**Route C: Neither.** Keep `UNRECOVERED_PENDING_DECISION`; freeze only independently user-established scope, not inherited unverified contract semantics. Gate-00 remains blocked.

## Source snapshot caveat

Notion page fetch responses may represent historical Aug 2026 snapshots. Without current export/time-verified evidence, do not assert that Notion contains the latest copy. These historical sources remain read-only; this policy does not alter their canonical labels.

## Source evidence checklist

- [ ] DOC-001 1.2 original OR SRC-EXC-001 signed
- [ ] DOC-005 1.1 original OR SRC-EXC-002 signed
- [ ] CCR-001 1.1 original OR SRC-EXC-003 signed
- [ ] Source-to-target `AUTH-*` → `MIG-*` → `ADR-*` crosswalk reviewed
- [ ] Latest-source metadata limitation disposed with named risk owner
- [ ] Review decision recorded in `APPROVAL_LEDGER.csv` with evidence link

**No check is claimed complete at this time.**

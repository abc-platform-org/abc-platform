# WP-000-01 — Feature Coverage and Traceability Audit

**Coverage:** 18 / 18 ABC-F; 26 / 26 AIS; 20 / 20 PRD. **64/64 ID rows have phase and role/gate coverage.**

This is **design traceability**, not code or behavioral coverage. The authoritative row-by-row companion is [PHASE_00_TRACEABILITY.csv](./PHASE_00_TRACEABILITY.csv).

## Summary by scope

| Scope | Planned IDs | Mapped role/phase/gate | Executable schema / API linked | Runtime test evidence |
|---|---:|---|---|---|
| ABC-F | 18 | Yes | Partial (concept only) | No |
| AIS | 26 | Yes | Partial (concept only) | No |
| PRD | 20 | Yes | Tests planned, no runnable cases linked | No |

## Critical mapping examples

| Feature | Source | Owner | Contract target | Planned test | Blocker |
|---|---|---|---|---|---|
| ABC-F15 | USER_UI+OCT2026+GITHUB_FEATURE_INVENTORY; USER-UI, OCT2026 | ENG-18/19 | BusinessActionProposal | BUS-01 SEC-03 | Schema, code, data fixture and reviewer evidence missing |
| AIS-004 | USER_UI+DOC-001/008/009/014+GITHUB_STUDIO; DOC-008; DOC-001; LIB-DOC-007 | ENG-02 | QuestionProfile / ConsultationProfile | PQ-01, PQ-02, PQ-03 | Schema, code, data fixture and reviewer evidence missing |
| AIS-009 | USER_UI+DOC-001/008/009/014+GITHUB_STUDIO; DOC-009/010 historical | ENG-08..11 | EditCommand / Mask / LookSpec | VIS-01 VIS-02 | Schema, code, data fixture and reviewer evidence missing |
| AIS-010 | USER_UI+DOC-001/008/009/014+GITHUB_STUDIO; DOC-009/010 historical | ENG-08..11 | ReferenceFeature / TryOnSpec | VIS-03 VIS-04 | Schema, code, data fixture and reviewer evidence missing |
| AIS-015 | USER_UI+DOC-001/008/009/014+GITHUB_STUDIO; DOC-009/010, UI | ENG-07/09/10/12 | LookVersion DAG / AcceptedState | VIS-04 VIS-05 | Schema, code, data fixture and reviewer evidence missing |
| AIS-020 | USER_UI+DOC-001/008/009/014+GITHUB_STUDIO; DOC-010/015/018 | ENG-11 | VisualQAReport | VIS-01 VIS-02 VIS-03 | Schema, code, data fixture and reviewer evidence missing |
| AIS-023 | USER_UI+DOC-001/008/009/014+GITHUB_STUDIO; USER-TECHNICAL-PLAN, KB-010/011 | ENG-15 | SOPVersion / EvidenceDependencyGraph / PlanDraft | TEC-01 TEC-02 TEC-03 | Schema, code, data fixture and reviewer evidence missing |
| AIS-024 | USER_UI+DOC-001/008/009/014+GITHUB_STUDIO; USER-TECHNICAL-PLAN, LIB-DOC-007 | ENG-16 | ValidationRecord / SpecialistID | TEC-04 TEC-05 | Schema, code, data fixture and reviewer evidence missing |
| AIS-025 | USER_UI+DOC-001/008/009/014+GITHUB_STUDIO; DOC-014 | ENG-17 | OutputEnvelope / OperationalHandoff | INT-01 | Schema, code, data fixture and reviewer evidence missing |
| AIS-026 | USER_UI+DOC-001/008/009/014+GITHUB_STUDIO; DOC-008 | ENG-01/12 | SessionCheckpoint / RevisionNumber | SES-01 | Schema, code, data fixture and reviewer evidence missing |

## Required Phase-01/02 build before engineering freeze

For all 64 IDs add `issue_url`, `actual_person`, `schema_path`, `api_path`, `test_file`, `run_url`, `reviewer`, `release_state`. Current CSV deliberately shows placeholders rather than fabricated links.

For current QA type, no `PASS` entries; the 120 `ABC-TC-*` are authored historical scenarios, not automatically linked to new platform contracts.

## Crosscheck

Mapping generated from the 70-file baseline in PR #1; no IDs added/renumbered. `ABC-F` / `AIS` / `PRD` IDs are proposals until formally adopted.

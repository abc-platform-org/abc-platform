# WP-000-01 — Migration Matrix

Historical documentation remains unchanged; each row is a **design migration obligation**, not a completed implementation.

| ID | Source | Legacy behavior | Target behavior | Required migration | Target owner/contract | Accountable role (unassigned person) | State | Authority refs |
|---|---|---|---|---|---|---|---|---|
| MIG-01 | DOC-000/001/900 | Per-salon Custom GPT delivery | Independent shared-screen platform | Retire as target runtime; preserve legacy spec | ADR-001/002, PRD | Architecture-owner | OPEN_REVIEW | AUTH-01,AUTH-05 |
| MIG-02 | DOC-005/006 | 10 logical agents in GPT | 19 contract-defined engine responsibilities; modular deployment | Port input/output/boundaries; no fake agent-to-service equivalence | ENG-01..19 | Platform architect | OPEN_CONTRACTS | AUTH-05 |
| MIG-03 | DOC-008, DOC-002 | Progressive questions in GPT dialogue | Service QuestionProfileRegistry + persisted evidence and decision impact | Preserve one useful question; interruption; no repeats | ENG-02 / AIS-004 | Consultation owner | OPEN_CONTRACTS | AUTH-08 |
| MIG-04 | DOC-003/004 & KB | 39 service and 45 attribute IDs | Versioned service/attribute ontology | Preserve IDs, map controlled service types and restrictions | ENG-05 / ABC-F08 | Knowledge owner | OPEN_EXPORT | AUTH-06,AUTH-14 |
| MIG-05 | DOC-007 v1.0 → Library v1.1 | Qualitative ranking, filters | Maintenance-aware fit, salon capability; fixed-choice state | No invented numeric confidence; defer professional approval | ENG-06 / AIS-007 | Decision owner | OPEN_PARENT_CHAIN | AUTH-07 |
| MIG-06 | DOC-009 / DOC-016A | Native GPT image best effort; external visual deferred | Mask-aware region pipeline / deterministic compositing | Protect outside mask; do not promise inside-region fidelity | ENG-08..11 | Vision owner | OPEN_BENCHMARK | AUTH-09 |
| MIG-07 | DOC-010 / DOC-015 | Legacy image QA without empirical thresholds | Automated+human Visual QA with per-service profiles | Set thresholds only after representative benchmark | ENG-11 / VIS suite | QA owner | OPEN_CALIBRATION | AUTH-09,AUTH-12 |
| MIG-08 | DOC-008 context limitations | Stateless conversation fallbacks | Persistent session, durable job, versioned event state | State recoverable; stale async completions rejected | ENG-01/12 / AIS-026 | Runtime owner | OPEN_CONTRACTS | AUTH-08 |
| MIG-09 | DOC-014 | 17 output envelopes and client-ready remote delivery | Shared-screen outputs + specialist-only handoff | Maintain OUT IDs; remote client send non-default/out of scope | ENG-17 / AIS-025 | Output owner | OPEN_SCHEMA | AUTH-11 |
| MIG-10 | DOC-012 | Safety in GPT instructions | Non-bypassable policy interception + specialist checks | S0–S3 rules maintained; medical boundary | ENG-14 / AIS-021 | Safety reviewer | OPEN_REVIEW | AUTH-10 |
| MIG-11 | DOC-013 | One GPT instance per salon | Tenant+branch isolation, RBAC, real config validation | No cross-salon leakage; backend enforcement | ABC-F17/18 | Security owner | OPEN_SECURITY_TEST | AUTH-05 |
| MIG-12 | User technical-plan decision | Only high-level process guidance | SOP-grounded plan, evidence gate, signed specialist review | Draft != validated; material version change invalidates | ENG-13/15/16 | Professional planning owner | NEW_SCOPE_SOP_MISSING | AUTH-03 |
| MIG-13 | User shared-session decision | Client may use remote GPT / sent preview | In-salon shared display; specialist operates | No standalone at-home app; role-protected drawers | AIS-001..026 | UX owner | NEW_SCOPE_UX | AUTH-01 |
| MIG-14 | Six UI images | Mock KPI widgets and menus | Real business OS, data-linked metrics and authorization | Display sample values only in demo/fixture mode | ABC-F01..18 | Business owner | NEW_SCOPE_DATA | AUTH-02 |
| MIG-15 | DOC-018 v1.0 & Library v1.2 | 120 authored golden tests | Preserve IDs with overlays, automation and expert evaluation | No 120/120 pass claim until executed | QA / G-08 | QA owner | OPEN_EXECUTION | AUTH-12 |
| MIG-16 | DOC-016 GPT build & BUILD-005 | Build-ready GPT spec; checklist unchecked | Actual platform source, CI and runtime tests | No transplant of Build Ready as implementation proof | Platform base | Delivery owner | OPEN_RUNTIME | AUTH-05 |
| MIG-17 | DOC-017/019 and DOC-016A | Not started/deferred placeholders | Platform-specific readiness and pilot gates | New contracts required, historical pointers preserved | G-08/09 | Release owner | OPEN_DOCUMENTS | AUTH-15 |
| MIG-18 | Library productization upstream links | DOC-001 1.2, DOC-005 1.1, CCR-001 1.1 references | Controlled new authority chain with explicit source status | Recover source before approval or record exception | G-00 | Product authority | SOURCE_BLOCKED | AUTH-07 |
| MIG-19 | User AI Studio modes | GPT best effort/unsupported mode differences | Mode-specific image contracts Transform/TryOn/Compare/Inspiration | Service × transform type × mode compatibility matrix | AIS-009..019 | AI Studio owner | OPEN_SPECS | AUTH-02 |
| MIG-20 | Product phase map | UI and runtime in docs not code | Phased 00..15 with owners, tests, sign-offs | Feature-to-engine-to-test-to-gate matrix | WBS / 18 F / 26 AIS | Program owner | OPEN_ISSUES | AUTH-13 |

## Migration acceptance protocol

Each `MIG-*` may close only when (1) source lineage documented, (2) target API/schema signed, (3) tests assigned, (4) working implementation independently verified and (5) ADR or documented approval linked. Notion pages are read-only.

**Gate-00 blocker subset:** MIG-01, MIG-02 authority approval, MIG-05/MIG-18 source lineage, MIG-12 specialist/SOP authority, MIG-15 release-evidence classification; other rows may become downstream phase obligations once explicitly accepted with assigned owners.

# WP-000-02 — Authority Precedence & Conflict-by-Conflict Resolution

**Status:** `PROPOSED_RESOLUTION`. Current user instructions establish *product intent*; the precise implementation contract becomes normative ONLY after reviewed ADR/PRD/contract freeze. Do not edit or relabel legacy Notion records.

## Precedence algorithm for conflicting assertions

1. First identify **decision domain**: target product, legacy product, service safety, software architecture, privacy, output semantics, data schema, or test evidence. A statement can be authoritative for one domain and historical for another.
2. Explicit product-owner directives govern **current target product purpose/scope** unless inconsistent with non-negotiable safety/law; they are not an automatic approval of unreviewed technology, exact SLA or clinical SOP.
3. Approved **current platform** ADR/PRD/schema govern implementation within their approved scope. Draft branch documents are proposed, not automatically operative.
4. Source-verifiable productization clauses may be imported **clause by clause** after lineage review; references to absent parent records cannot supply missing content.
5. Compatible older DOC/KB contracts are reusable for semantics, service IDs and safety. Historical GPT-only infrastructure prohibitions govern historical V1 only.
6. A safety contradiction fails closed; cannot be waived by commercial rules, client preference, specialist role label alone, or prompts.
7. Test authoring/knowledge freeze status does not substitute for runtime or pilot evidence; no invented thresholds.

## Conflict register and bounded disposition

| ID | Conflict | Evidence | Proposed ruling | Preserved rule | New contract / tests | Decision status |
|---|---|---|---|---|---|---|
| RES-01 | GPT-only V1 vs independent salon platform | DOC-000/001/005/016/900 vs current scope | Platform is target; old V1 archived for history | service/safety/decision semantics | ADR-001; platform runtime/contract harness | REVIEW_REQUIRED |
| RES-02 | Client-mode remote usage vs same-screen specialist operation | DOC-001/002 and current directive | Single shared local screen; specialist operates; no client at-home portal | client participation and understandable explanations | ADR-002; UX, RABC and session tests | REVIEW_REQUIRED |
| RES-03 | Client-ready output/remote sharing vs internal handoff | DOC-014 OUT-01..17 | Preserve legacy OUT IDs, add target scoped outputs; no automatic customer delivery | transparent explanation, no false result | OUT registry migration, ENG-17; SEC/OUT tests | REVIEW_REQUIRED |
| RES-04 | 10 GPT logical agents vs 19 target engines | DOC-005/006 and ENG-01..19 | 19 are roles, not pre-existing services; map semantics, avoid fake one-to-one match | semantic input/output and safety boundaries | ADR-001/009, engine contracts, contract tests | REVIEW_REQUIRED |
| RES-05 | GPT-native Preview vs deterministic mask compositor | DOC-009/010, DOC-016A deferred | Target a modular CV pipeline as hypothesis; mandatory visual POC and QA before guarantees | decision-preview disclaimer, source identity roles | ADR-004/005; VIS suites, model benchmark | REVIEW_REQUIRED |
| RES-06 | Text-prompt session memory vs durable platform state | DOC-008, new UI | Backend session/event state, idempotent jobs, replay and stale-result rejection | progressive question and interruption semantics | ADR-009, ENG-01/12; SES/OBS tests | REVIEW_REQUIRED |
| RES-07 | GPT per salon vs multi-tenant backend | DOC-013 vs current target | Backend-scoped tenant/branch, no cross-tenant lookups or assets | capability/price truthfulness per salon | ADR-010; SEC/TEN suites | REVIEW_REQUIRED |
| RES-08 | Visual suitability vs professional execution | DOC-007 and current technical plan | Selected Look != FZ-3 != service authorization; bounded specialist approval | qualitative ranking, missing evidence/constraints | ADR-007/008, ENG-13..16; TEC tests | REVIEW_REQUIRED |
| RES-09 | High-risk chemical and specialist outputs | DOC-012, KB-010..014 | Use versioned source-approved SOP and evidence gates; lack of SOP => non-executable advisory only | S0–S3 and chemical/medical limits | ADR-008/010; safety test suite | REVIEW_REQUIRED |
| RES-10 | 120 authored tests reported as 'passed' | DOC-015/018 and Library DOC-018 v1.2 | Keep authoring status, leave execution NOT_RUN | canonical test IDs; productization assertions pending review | QA evidence pack, test registry | REVIEW_REQUIRED |
| RES-11 | Missing DOC-001/005/CCR newer parent versions | Library DOC-007 v1.1 | Unrecovered; no inferred supersession; signed exception or true recovery | verifiable individual clauses and older sources | SRC-EXC-001..003, ADR review | SOURCE_BLOCKED |
| RES-12 | KB-900 frozen derivative interpreted as platform ready | KB-900 and DOC-016 | Preserve 16-file historical freeze, but actual bytes/hashes and platform retrieval must be checked | 39 service IDs, 45 attribute IDs, evidence classes | knowledge import tests | REVIEW_REQUIRED |
| RES-13 | Mock metrics & Ask ABC business actions | six reference UIs and product inventory | Values are illustrative until data lineage; READ/RECOMMEND/EXECUTE permissions separate | salon business functions in target scope | Business action policies and ledger tests | REVIEW_REQUIRED |

## Rules for exceptions

- A `RES-*` row reaches `APPROVED` only if reviewer identity, review date, exact approved contract/ADR version, impact assessment, and explicit test obligations are recorded.
- `SOURCE_BLOCKED` remains until a signed `SRC-EXC-*` exception OR verifiable source recovery.
- A proposal may become a normative new platform contract on its own authority; it must never be mislabeled a recovered Notion version.

## Exit for this document

Every conflict row has a target ADR/contract, treatment and reviewer; none is automatically signed. Downstream Gate-00 decision is kept open pending Product/Architecture/Security/Specialist/QA signoffs and review of source exceptions.

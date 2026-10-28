# WP-000-01 — Authority Matrix

Status: **PROPOSED FOR ARCHITECTURE REVIEW**. Precedence here is an explicit **audit recommendation**, not a retroactive rewrite of Notion CANONICAL statuses.

## Proposed effective precedence

1. Explicit user-confirmed 2026 salon-controlled product requirements (scope).
2. Current formally approved GitHub ADR/PRD and security policy **after approval** (implementation).
3. Verified newer productization contracts with complete parent lineage.
4. Compatible canonical legacy Notion behavior and knowledge IDs.
5. Legacy GPTs-only deployment prescriptions as historical implementation records.

## Decisions and collisions

| ID | Evidence / authority | Relevant rule | Scope | Source status | Resolution proposal | Affected IDs | Conflict |
|---|---|---|---|---|---|---|---|
| AUTH-01 | Current user product directives | Shared physical salon screen, specialist operates, client participates, no at-home app or automatic client delivery | Product scope / acceptance | USER_CONFIRMED | Retain as accepted **intent**, detail in ADR-002/PRD pending review | ABC-F05, AIS-001..026 | DOC-001 legacy Client Mode and DOC-014 client-ready send flows |
| AUTH-02 | Current user product directives | AI Studio is highest value, all advanced services in target scope | Product priorities | USER_CONFIRMED | MVP activation subject to service Gate, no implicit live capability | ABC-F05, AIS-005..020 | Legacy GPT scope and salon management expansion |
| AUTH-03 | Current user product directives | Technical Execution Roadmap after selected look; specialist determines execution | Execution planning | USER_CONFIRMED | Plan Draft and human signoff; SOP provenance mandatory | ABC-F06, AIS-021..025 | DOC-014 Handoff and DOC-007 feasibility |
| AUTH-04 | Current user product directives | GitHub abc-platform as engineering source-of-truth; use reviewed PRs | Engineering change records | USER_CONFIRMED | No Notion edits / do not modify main in Phase 00 | ABC-MEP-01.1 | Notion legacy master registry |
| AUTH-05 | Notion DOC-000/001/005/006/009/010/012/013/016/900 | GPTs-only V1 runtime, no proprietary API, per-salon GPT | Historical legacy deployment | LEGACY_CANONICAL_FOR_LEGACY_V1 | Retain history; NOT target runtime for platform | ENG-01..19 | AUTH-01..04 / proposed ADR-001 |
| AUTH-06 | Notion DOC-003/004 and KB-900 | 39 service IDs, 45 attributes, controlled IDs; evidence classes | Ontologies and crosswalk | LEGACY_CANONICAL_COMPATIBILITY | Preserve IDs; require export and ID crosswalk | ENG-03..07,13..15 | No actual independent platform KB tested |
| AUTH-07 | Notion DOC-007 v1.0 vs Library DOC-007 v1.1 | Hard filter, qualitative cascade, preference and maintenance; specialist cannot self-confirm | Decision semantics | PRODUCTIZATION_CANDIDATE_NEWER | Prefer latest *verified provisions* conditionally; no automatic supersession while parents missing | ENG-06,13,16 | DOC-001 v1.2, DOC-005 v1.1, CCR-001 missing |
| AUTH-08 | Notion DOC-008 | Targeted one-question loop, interruptions and state recovery | Questioning behavior | LEGACY_CANONICAL_COMPATIBILITY | Migrate mechanics; backend owns persistent session | ENG-02/01 | Text-only pseudo-state in legacy |
| AUTH-09 | Notion DOC-009/010 | External segmentation/compositing historically specified then deferred for GPT V1 | Visual mechanism | HISTORICAL_TECH_DIRECTION | Propose revival; validate feasible identity/geometry and quality with experiments | ENG-08..12 | Do not claim deterministic face fidelity |
| AUTH-10 | Notion DOC-012 / KB-011 | Safety tiers S0–S3, professional checks | Safety behavior | LEGACY_CANONICAL_COMPATIBILITY | Enforce backend policy, human escalation | ENG-14/13/15 | Prompt-only interceptor not sufficient |
| AUTH-11 | Notion DOC-014 | 17 canonical OUT-01…17 types | Outputs / Handoff | LEGACY_CANONICAL_COMPATIBILITY | Typed outputs & role/visibility rules; remove remote client send as default | ENG-17 | Client-ready remote path incompatible with in-salon-only |
| AUTH-12 | Notion DOC-015, DOC-018 & Library DOC-018 v1.2 | 17 QA dimensions; 120 authored canonical tests with salon overlays | Evaluation | AUTHORING_APPROVED_NOT_EXECUTED | Retain test IDs, add platform runtime assertions; calibrate results | G-02…09 | No run evidence, thresholds OPEN |
| AUTH-13 | GitHub 70-file baseline PR#1 | 18 ABC-F + 26 AIS + 20 PRD + 19 ENG + 16 phases | Future engineering target | PROPOSED_NOT_MERGED | Use as migration proposal; approve ADRs before contract freeze | All | No code/runtime verification |
| AUTH-14 | Notion KB-900 | 16 derived runtime KB files frozen | Knowledge derivative | FROZEN_GPT_KNOWLEDGE_ONLY | Rehash derivatives before extraction and migration | ENG-05 | Not identical to 15 source KB pages |
| AUTH-15 | Notion DOC-016A/017/019 | Future visual runtime, pilot, readiness placeholders | Planning history | NOT_STARTED | Create platform-specific contracts in later phases | G-01,G-08 | Legacy dependency graph obsolete |

## Approval boundaries

- Current user intent is accepted as direction, but detailed ADR and PRD amendments remain subject to review.
- Productization contracts do not override unlocated parent documents by inference.
- Historical documentation gates with `PASSED` are **authoring approvals** only; live runtime gates remain NOT_RUN.
- No one may assert the original `ABC-DOC-900` is revised in Notion; GitHub carries migration overlays.

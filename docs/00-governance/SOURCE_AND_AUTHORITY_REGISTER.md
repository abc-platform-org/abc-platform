# Source, Authority, and Migration Register

Document `ABC-SRC-001` | status: `PROPOSED` / audit incomplete

## Evidence inventory

| Source | Known content | Evidence status |
|---|---|---|
| [ABC-DOC-000 Product Charter](https://app.notion.com/p/3b76f520f93e81e5a7b0e7b4062991ea) | Product mission; 2026-08-17 GPTs-only amendment | Historical baseline; supersession requires explicit ADR |
| [ABC-DOC-001 Product Specification](https://app.notion.com/p/3b76f520f93e814b89b6d2b4b250361d) | Modes, intents, consultation, visual/output principles | Legacy v1.1.0; productization v1.2.0 referenced elsewhere; unverified |
| [ABC-DOC-005 Intelligence Architecture](https://app.notion.com/p/3be6f520f93e8145be7bf3cc9f836c4b) | Ten logical GPT agents; object chain, progressive questioning | Legacy v1.0.x, NOT independent software engines |
| [ABC-DOC-007 Decision](https://app.notion.com/p/3be6f520f93e81878b88eb3c8975e316) | Candidate/filter/cascade/recommendation | Legacy canonical v1.0.0 |
| Library: ABC_DOC_007_Decision_Recommendation_Engine_v1.1.0_PRODUCTIZATION.md | Salon-controlled authority, qualitative decision and evidence classes | 2026-08-22 proposed productization baseline; newer than Notion version |
| [ABC-DOC-008 Conversation OS](https://app.notion.com/p/3be6f520f93e815eb572f57922485355) | Adaptive question loop, interruption, revision | Legacy contract to migrate |
| [ABC-DOC-009 Visual Preview](https://app.notion.com/p/3be6f520f93e81e28b93e3b181a4ded6) | Segmentation / generation / deterministic compositing / QA; later deferred for GPTs V1 | Historical platform technical direction to revive and validate |
| [ABC-DOC-012 Safety](https://app.notion.com/p/3be6f520f93e81ae8675ff1c05c5741a) | S0–S3, professional and medical boundaries | Legacy rules; implement outside GPT in policy runtime |
| [ABC-DOC-014 Output & Handoff](https://app.notion.com/p/3be6f520f93e8173954dd509eead549f) | 17 output contract categories | Translate into typed outputs and permissions |
| [ABC-DOC-015 QA](https://app.notion.com/p/3be6f520f93e81d3b1aff184314666d3) | 17 evaluation dimensions, severity, release policy | Test design, not executed results |
| [ABC-DOC-018 Golden Dataset](https://app.notion.com/p/3be6f520f93e8165bb8ddaf27a19e415) | 120 authored cases | Authored != executed / passed |
| Library: ABC_DOC_018_Golden_Test_Dataset_Red_Team_Baseline_v1.2.0_PRODUCTIZATION.md | Same 120 canonical IDs plus productization assertions | Execution claim NONE; empirical thresholds OPEN |
| [ABC-DOC-013 Salon Config](https://app.notion.com/p/3be6f520f93e8124b988c7f9d64cf068) | White-label configuration and service availability | Migrate into config/permissions with tenant isolation |
| [ABC-KB-900 freeze](https://app.notion.com/p/3bf6f520f93e81dba5dce61e7b2a6eca) | 16 runtime KB files, 39 service IDs, 45 attribute IDs | Document-level inventory, not live software proof |
| Six user-supplied UI reference images | Dashboard & AI Studio, salon and barbershop, EN/FA | Visual design input; do not treat illustrative KPI values as real |
| User-confirmed product decisions (Oct 2026) | Shared screen, professional control, expanded services, technical roadmap, GitHub canonical engineering workflow | Current product directive; translate to controlled ADRs |

## Authority order to confirm at Phase 00

1. Explicit current user product decisions.
2. Formally approved current ADR and PRD (once reviewed).
3. Newer documented productization contracts whose upstream sources are verified.
4. Preserved legacy Notion contracts for compatible product behavior.
5. Historical GPTs-only implementation amendments (not target deployment).

**Open conflicts:** parent references `ABC-DOC-001 v1.2.0`, `ABC-DOC-005 v1.1.0`, `ABC-CCR-001 v1.1.0` in later productization docs have NOT been conclusively recovered in this package. Preserve the references as `UNVERIFIED_SOURCE`; do not invent them. The original Notion remains unchanged.

## Migration policy

Preserve existing IDs, knowledge service mapping, and 120 golden test IDs. Introduce new `ABC-F`, `AIS`, `ENG`, `PRD` identities as **proposal**, not silent substitutions for canonical legacy IDs. Every migrated contract requires source, new owner, implementation test, and review.


## Phase 00 audit overlay (2026-10-29; PR #1 — proposed)

[WP-000-01 audit index](phase-00/README.md) provides source-by-source evidence and distinguishes legacy Notion document authority from target platform authority. Gate-00 is **BLOCKED_FOR_APPROVAL**; missing parent sources and human ADR approvals remain open. The archive itself was not retroactively rewritten.

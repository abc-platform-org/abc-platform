# WP-000-02 — Legacy AG-01..10 to Platform ENG-01..19 Crosswalk

**Provenance:** [Notion DOC-006](https://app.notion.com/p/3be6f520f93e810fb8a0eaef1ce03856); these are *logical Custom GPT agents*, not deployed services. Target ENG allocations are design roles, not verified production components.

| Legacy agent / role | Preserved semantic responsibility | Target engines/modules | Material new responsibilities | Migration evidence |
|---|---|---|---|---|
| AG-01 Orchestrator | intent/mode routing and coordinated steps | ENG-01 + durable Workflow Runtime | checkpoint persistence, concurrency, outbox, retries, stale-job rejection | Session schema, SES-01, OBS-01 |
| AG-02 Consultation | guided intake, one useful question, interruption | ENG-02 + ENG-03 | per-service QuestionProfile, evidence provenance, stop policy | PQ-01..03, contract tests |
| AG-03 Beauty Analysis | analysis attributes relevant to selected service | ENG-03 + ENG-04 + ENG-05 | multi-view/image QA, versioned ontology, uncertainty | INP-01/02, ANA-01 |
| AG-04 Recommendation | candidates, filters, trade-offs, feasibility caveat | ENG-06 + ENG-13 | typed ranking + capability checks, no unauthorized FZ-3 | DEC-01, TEC-02 |
| AG-05 Visual Preview | decision preview, reference separated from subject | ENG-07..12 | LookSpec, masks, controlled edit, compositing, independent QA, version DAG | VIS-01..06, expert review |
| AG-06 Service Intelligence | service/process knowledge, complementary advice | ENG-05 + ENG-13 + ENG-15 | SOP versioning, dependency graph, materials, conditional plans | KB-ID-MAP, TEC-01..03 |
| AG-07 Specialist Assistant | specialist context and handoff assistance | ENG-15 + ENG-16 + ENG-17 | specialist identity, signed approval, plan invalidation | TEC-04/05, SEC-03 |
| AG-08 Safety | clinical/chemical/role boundary and risk tiers | ENG-14 + policy interceptors across all modules | fail-closed backend policy, non-bypassable transaction guard | SAF-01..03, SEC-01 |
| AG-09 Sales | salon-appropriate commercial output, not biasing beauty fit | ENG-17 + ENG-18 + ENG-19 | real ledger KPI, authorized actions, idempotent business commands | BUS-01/02, INT-01 |
| AG-10 Output | typed client/specialist output, errors | ENG-17 + permission middleware | shared-screen/private visibility, internal operational handoff | OUT tests, SEC-02 |

## Target engines not represented one-to-one

- ENG-07–12 deliberately split the monolithic AG-05 image intent into LookSpec / segmentation / generation / compositing / QA / version state.
- ENG-15/16 exist because the user explicitly requires a **technical execution roadmap after Look selection**, with a separate specialist approval authority. A model-written checklist is not execution clearance.
- ENG-18/19 cover a wider Salon Business OS than historical AG-09 sales text.

## Mapping invariant

`Original AG contract` + `source version` + `target ENG contract` + `service scope` + `test IDs` + `reviewed decision` are required before assigning a platform engine the status IMPLEMENTED. A passing documentation validator cannot satisfy this invariant.

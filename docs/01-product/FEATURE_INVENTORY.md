# Feature Inventory — ABC-F01..F18 and AIS-001..026

Status: ALL ITEMS `PROPOSED_TARGET` unless explicitly evidenced by implementation. Names and IDs are newly proposed; legacy Notion IDs are not replaced.

## Cross-product functions

| ID | Feature | Required functions | Owner | Phases | Gate |
|---|---|---|---|---|---|
| ABC-F01 | Home Dashboard | Business Pulse, Today timeline, AI Studio preview, AI opportunities, salon pulse, quick actions | Salon OS / ENG-18 | 10 | G-07 |
| ABC-F02 | Global Search | Permission-scoped clients, appointments, services, sessions, looks, team and campaigns | Search + RBAC | 04,10 | G-07 |
| ABC-F03 | Calendar | Day/week/team scheduling, status transitions, conflict handling, capacity | Scheduling | 10 | G-07 |
| ABC-F04 | Clients | Client profile, consent, service history, preference, visit and authorized AI record | CRM / Consent | 04,10 | G-06 |
| ABC-F05 | AI Studio | Shared session, consult, previews, comparison, revisions, selection | ENG-02..12 | 05..08 | G-03,G-06 |
| ABC-F06 | Technical Roadmap | SOP-grounded plan of selected look with specialist review | ENG-13..16 | 09 | G-05 |
| ABC-F07 | Team | Staff, qualifications, shifts, privileges, specialist availability | Team / Auth | 04,10 | G-07 |
| ABC-F08 | Services | Catalog, status, pricing source, duration, SOP, visual capability | Service Registry | 02,06,10 | G-04,G-07 |
| ABC-F09 | Sales/POS | Quotes, invoices, line items, payment status and reconciliation | POS | 10,14 | G-07 |
| ABC-F10 | Inventory | Stock ledger, materials, alerts, reorder and consumption | Inventory | 10,14 | G-07 |
| ABC-F11 | Marketing | Segmentation, campaigns, follow-up consent, triggers | Campaigns | 10,14 | G-07 |
| ABC-F12 | Analytics | Provenance-linked financial/operational/AI metrics, filters, drill-down | Analytics / ENG-18 | 04,10,14 | G-07 |
| ABC-F13 | Automations | Authorized scheduled/event actions, idempotency, audit | ENG-19 | 10,14 | G-07 |
| ABC-F14 | Reviews | Feedback intake and structured follow-up | Feedback | 10,14 | G-07 |
| ABC-F15 | Ask ABC | Read/recommend/execute tiers, grounded business copilot, approvals | ENG-18/19 | 10,14 | G-07 |
| ABC-F16 | Notifications | Appointments, jobs, inventory, payment, validation, alerts | Notifications | 04,10 | G-07 |
| ABC-F17 | Multi-Branch | Branch scoping, isolation, staff/service contexts | Tenant/Branch | 04,15 | G-09 |
| ABC-F18 | Settings/Governance | Brand, localization, privacy, roles, versions, feature flags | Config/Policy | 04,10,15 | G-09 |

## AI Studio functional registry

| ID | Function | Owning engine/domain | Phase | Gate |
|---|---|---|---|---|
| AIS-001 | Session initialization | ENG-01 | 04 | G-06 |
| AIS-002 | Image intake / consent | ENG-03 | 04,07 | G-02 |
| AIS-003 | Input quality gate | ENG-03 | 07 | G-02 |
| AIS-004 | Consultation / adaptive questioning | ENG-02 | 05 | G-02 |
| AIS-005 | Service-aware controls | ENG-05/07 | 03,06 | G-04 |
| AIS-006 | Reference interpretation | ENG-03/04 | 06 | G-02 |
| AIS-007 | Grounded recommendation | ENG-06 | 06 | G-04 |
| AIS-008 | Look specification | ENG-07 | 06 | G-04 |
| AIS-009 | Transform | ENG-08..11 | 07 | G-03 |
| AIS-010 | Try On | ENG-08..11 | 07,08 | G-03 |
| AIS-011 | Multiple valid generated looks | ENG-06/09 | 07 | G-03 |
| AIS-012 | Before / After viewer | Frontend/ENG-12 | 03,08 | G-03 |
| AIS-013 | Compare workspace | Frontend/ENG-12 | 08 | G-03 |
| AIS-014 | Region locking | ENG-08/10 | 07 | G-03 |
| AIS-015 | Iterative refinement | ENG-07/09/10/12 | 08 | G-03 |
| AIS-016 | Version history | ENG-12 | 08 | G-03 |
| AIS-017 | Favorites / shortlist | ENG-12 | 08 | G-04 |
| AIS-018 | Inspiration | ENG-05/06 | 06,08 | G-04 |
| AIS-019 | Palette intelligence | ENG-05/07 | 06,08 | G-04 |
| AIS-020 | Visual QA | ENG-11 | 07,12 | G-03 |
| AIS-021 | Feasibility review | ENG-13/14 | 09 | G-05 |
| AIS-022 | Selected look lock | ENG-07/12 | 08 | G-05 |
| AIS-023 | Technical plan generation | ENG-15 | 09 | G-05 |
| AIS-024 | Specialist review | ENG-16 | 09 | G-05 |
| AIS-025 | Operational handoff | ENG-17 | 11 | G-07 |
| AIS-026 | Recovery & resume | ENG-01/12 | 04,11 | G-06 |

## Visual work modes

- **Transform:** controlled change to specific requested attributes, without rewriting unrelated identity or accepted state.
- **Try On:** apply reference style/features to the client image, never copy reference identity.
- **Compare:** same source/consistent frame, readable tradeoffs, no false numerical probability.
- **Inspiration:** evidence-based diverse style directions; no unrelated randomly generated alternatives.
- **Technical Plan:** post-selection, specialist-gated mode; not a fifth generative picture mode.

## Additional must-have Studio UI (beyond reference screenshots)

Session status; input quality; editable region overlay; locked regions; edit history; Undo/Redo; selected look comparisons; visual QA status; evidence and unknowns; Technical Plan; specialist validation; crash recovery; multi-view assets; role-protected drawers. Shared/privileged separation must be enforced beyond visual presentation.

## Definition of feature completion

Each feature requires a feature-to-PRD-to-component-to-engine-to-schema-to-API-to-test-to-evidence-to-gate mapping. Feature presence in this index **does not** indicate engineering completion.

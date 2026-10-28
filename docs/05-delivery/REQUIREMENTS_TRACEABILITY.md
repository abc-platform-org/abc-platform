# Master Traceability Matrix — proposed, not implemented

Requirement/feature → phase → owner → tests → gate. `TEST_IDS` are **planned** names unless a real execution result is linked. No PASS claims.

## 18 business/platform features

| Feature | Owner | Phase(s) | Gate | Status |
|---|---|---|---|---|
| ABC-F01 Home Dashboard | Salon OS / ENG-18 | 10 | G-07 | SPECIFIED |
| ABC-F02 Global Search | Search + RBAC | 04,10 | G-07 | SPECIFIED |
| ABC-F03 Calendar | Scheduling | 10 | G-07 | SPECIFIED |
| ABC-F04 Clients | CRM / Consent | 04,10 | G-06 | SPECIFIED |
| ABC-F05 AI Studio | ENG-02..12 | 05..08 | G-03,G-06 | SPECIFIED |
| ABC-F06 Technical Roadmap | ENG-13..16 | 09 | G-05 | SPECIFIED |
| ABC-F07 Team | Team / Auth | 04,10 | G-07 | SPECIFIED |
| ABC-F08 Services | Service Registry | 02,06,10 | G-04,G-07 | SPECIFIED |
| ABC-F09 Sales/POS | POS | 10,14 | G-07 | SPECIFIED |
| ABC-F10 Inventory | Inventory | 10,14 | G-07 | SPECIFIED |
| ABC-F11 Marketing | Campaigns | 10,14 | G-07 | SPECIFIED |
| ABC-F12 Analytics | Analytics / ENG-18 | 04,10,14 | G-07 | SPECIFIED |
| ABC-F13 Automations | ENG-19 | 10,14 | G-07 | SPECIFIED |
| ABC-F14 Reviews | Feedback | 10,14 | G-07 | SPECIFIED |
| ABC-F15 Ask ABC | ENG-18/19 | 10,14 | G-07 | SPECIFIED |
| ABC-F16 Notifications | Notifications | 04,10 | G-07 | SPECIFIED |
| ABC-F17 Multi-Branch | Tenant/Branch | 04,15 | G-09 | SPECIFIED |
| ABC-F18 Settings/Governance | Config/Policy | 04,10,15 | G-09 | SPECIFIED |

## 26 AI Studio capabilities

| ID | Capability | Owner | Phase(s) | Gate | Status |
|---|---|---|---|---|---|
| AIS-001 | Session initialization | ENG-01 | 04 | G-06 | SPECIFIED |
| AIS-002 | Image intake / consent | ENG-03 | 04,07 | G-02 | SPECIFIED |
| AIS-003 | Input quality gate | ENG-03 | 07 | G-02 | SPECIFIED |
| AIS-004 | Consultation / adaptive questioning | ENG-02 | 05 | G-02 | SPECIFIED |
| AIS-005 | Service-aware controls | ENG-05/07 | 03,06 | G-04 | SPECIFIED |
| AIS-006 | Reference interpretation | ENG-03/04 | 06 | G-02 | SPECIFIED |
| AIS-007 | Grounded recommendation | ENG-06 | 06 | G-04 | SPECIFIED |
| AIS-008 | Look specification | ENG-07 | 06 | G-04 | SPECIFIED |
| AIS-009 | Transform | ENG-08..11 | 07 | G-03 | SPECIFIED |
| AIS-010 | Try On | ENG-08..11 | 07,08 | G-03 | SPECIFIED |
| AIS-011 | Multiple valid generated looks | ENG-06/09 | 07 | G-03 | SPECIFIED |
| AIS-012 | Before / After viewer | Frontend/ENG-12 | 03,08 | G-03 | SPECIFIED |
| AIS-013 | Compare workspace | Frontend/ENG-12 | 08 | G-03 | SPECIFIED |
| AIS-014 | Region locking | ENG-08/10 | 07 | G-03 | SPECIFIED |
| AIS-015 | Iterative refinement | ENG-07/09/10/12 | 08 | G-03 | SPECIFIED |
| AIS-016 | Version history | ENG-12 | 08 | G-03 | SPECIFIED |
| AIS-017 | Favorites / shortlist | ENG-12 | 08 | G-04 | SPECIFIED |
| AIS-018 | Inspiration | ENG-05/06 | 06,08 | G-04 | SPECIFIED |
| AIS-019 | Palette intelligence | ENG-05/07 | 06,08 | G-04 | SPECIFIED |
| AIS-020 | Visual QA | ENG-11 | 07,12 | G-03 | SPECIFIED |
| AIS-021 | Feasibility review | ENG-13/14 | 09 | G-05 | SPECIFIED |
| AIS-022 | Selected look lock | ENG-07/12 | 08 | G-05 | SPECIFIED |
| AIS-023 | Technical plan generation | ENG-15 | 09 | G-05 | SPECIFIED |
| AIS-024 | Specialist review | ENG-16 | 09 | G-05 | SPECIFIED |
| AIS-025 | Operational handoff | ENG-17 | 11 | G-07 | SPECIFIED |
| AIS-026 | Recovery & resume | ENG-01/12 | 04,11 | G-06 | SPECIFIED |

## 20 PRD acceptance contracts

| ID | Owner | Test ID | State |
|---|---|---|---|
| PRD-001 | ENG-01 | SES-01 | NOT_EXECUTED |
| PRD-002 | Consent | SEC-02 | NOT_EXECUTED |
| PRD-003 | ENG-03 | INP-01 | NOT_EXECUTED |
| PRD-004 | ENG-03 | INP-02 | NOT_EXECUTED |
| PRD-005 | ENG-04 | ANA-01 | NOT_EXECUTED |
| PRD-006 | ENG-06/14 | DEC-01 | NOT_EXECUTED |
| PRD-007 | ENG-07 | LOOK-01 | NOT_EXECUTED |
| PRD-008 | ENG-10 | VIS-02 | NOT_EXECUTED |
| PRD-009 | ENG-11 | VIS-01 | NOT_EXECUTED |
| PRD-010 | ENG-12 | VIS-04 | NOT_EXECUTED |
| PRD-011 | ENG-12 | VIS-05 | NOT_EXECUTED |
| PRD-012 | ENG-07/12 | TEC-01 | NOT_EXECUTED |
| PRD-013 | ENG-13 | TEC-02 | NOT_EXECUTED |
| PRD-014 | ENG-15 | TEC-03 | NOT_EXECUTED |
| PRD-015 | ENG-16 | TEC-04 | NOT_EXECUTED |
| PRD-016 | ENG-16 | TEC-05 | NOT_EXECUTED |
| PRD-017 | ENG-17 | INT-01 | NOT_EXECUTED |
| PRD-018 | ENG-18/19 | BUS-01 | NOT_EXECUTED |
| PRD-019 | Auth | SEC-01 | NOT_EXECUTED |
| PRD-020 | Platform | OBS-01 | NOT_EXECUTED |

## Traceability rule

No feature may be reported IMPLEMENTED unless code/PR exists. No TESTED/PASSED without pipeline and human-review evidence as required. Before an implementation sprint, create issue IDs, API/schema refs, unit/E2E test refs, actual owner, reviewer, commit and gate evidence. Required missing items block contract freeze.

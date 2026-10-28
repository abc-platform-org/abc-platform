# WP-000-03 — Accountable Roles, RACI and Review Independence

**State:** `ROLE_RACI_PROPOSED / REAL_PEOPLE_UNASSIGNED`. Role mapping is not human appointment or acceptance.
**Action:** [GitHub owner assignment issue #4](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/4).

## Review authorities — each requires real identity and explicit acceptance

| Authority ID | Proposed accountable role | Minimum authority/responsibility | Current person | Decision status | Issue |
|---|---|---|---|---|---|
| GOV-A01 | Product Authority | Product scope, user-priority precedence and feature freeze | UNASSIGNED | PENDING | #3 |
| GOV-A02 | Architecture Authority | All ADR technical decisions, engine interfaces and migration topology | UNASSIGNED | PENDING | #3 |
| GOV-A03 | Qualified Domain & Safety Authority | Service-specific SOPs, safety tiers, chemical/clinical boundary | UNASSIGNED | PENDING | #6 |
| GOV-A04 | Security & Privacy Authority | RBAC, tenant, shared-screen, images, consent/retention and legal counsel where appropriate | UNASSIGNED | PENDING | #5 |
| GOV-A05 | QA/Evaluation Authority | Golden test classification, independent QA and release gate evidence | UNASSIGNED | PENDING | #7 |
| GOV-A06 | Delivery/Program Authority | Cross-domain owners, branch governance, PR policy, Gate signoff routing | UNASSIGNED | PENDING | #4 |

A = accountable approval role; R = execution owner role; C = consulted; I = informed. **A role is not a person**; a named individual and consent/acceptance are required before signoff.

## 19 engine workstream ownership proposal

| Engine | Accountable role (A) | Responsible delivery (R) | Required reviewers (C) | Phase |
|---|---|---|---|---|
| ENG-01 | Architecture Authority | Runtime Platform Lead | Security, QA | 02/04/11 |
| ENG-02 | Product Authority | Consultation/Conversation Lead | Domain Specialist, QA | 05 |
| ENG-03 | Architecture Authority | Input & Evidence Lead | Security/Privacy, QA | 04/07 |
| ENG-04 | Product Authority | Beauty Analysis/CV Lead | Domain Specialist, QA | 06 |
| ENG-05 | Architecture Authority | Knowledge/Ontology Lead | Domain Specialist, QA | 01/06 |
| ENG-06 | Product Authority | Decision Intelligence Lead | Domain Specialist, Safety, QA | 06 |
| ENG-07 | Architecture Authority | Look Model Lead | Visual/Technical Planning, QA | 06/08 |
| ENG-08 | Architecture Authority | Segmentation/CV Lead | Visual QA, Security | 07 |
| ENG-09 | Architecture Authority | Generative Image Lead | Visual QA, Safety | 07 |
| ENG-10 | Architecture Authority | Image Compositing Lead | Visual QA | 07 |
| ENG-11 | QA/Evaluation Authority | Independent Visual QA Lead | CV/Domain Specialist | 07/12 |
| ENG-12 | Architecture Authority | Session/Visual State Lead | Runtime, QA | 04/08 |
| ENG-13 | Domain & Safety Authority | Professional Feasibility Lead | Safety, QA | 09 |
| ENG-14 | Domain & Safety Authority | Safety Policy Lead | Security, Domain Specialist | 04/09 |
| ENG-15 | Domain & Safety Authority | Technical Planning Lead | SOP Author, Domain Specialist, QA | 09 |
| ENG-16 | Domain & Safety Authority | Human Validation/Identity Lead | Security, Domain Specialist | 09 |
| ENG-17 | Delivery/Program Authority | Output/Operations Integration Lead | Security, Product, QA | 11 |
| ENG-18 | Product Authority | Data & Analytics Lead | Finance/Operations, QA | 10/14 |
| ENG-19 | Product Authority | Business Automation Lead | Security, Operations, QA | 10/14 |

**Separation of duties:** ENG-09 author must not be sole approver of ENG-11 generated-image quality. Specialist plan generation (ENG-15) cannot self-approve (ENG-16). Business action author cannot independently bypass authorization or mutate billing. Security design reviewer should independently attest negative access tests. If one person fills multiple roles in a small team, conflict-of-interest/compensating controls require recorded reviewer approval.

## 18 product modules — accountable group

| Modules | Proposed accountable group | Integration owners (R) |
|---|---|---|
| ABC-F01, F12, F15 | Product Authority | Business Analytics / ENG-18 / Business Automation |
| ABC-F02, F16 | Architecture Authority | Search / Notification Backend |
| ABC-F03, F07, F08 | Delivery/Program Authority | Scheduling / Team / Services Domains |
| ABC-F04 | Security & Privacy Authority | CRM / Consent |
| ABC-F05 | Product + Architecture Authorities | AI Studio / ENG-02..12 |
| ABC-F06 | Domain & Safety Authority | ENG-13..16 |
| ABC-F09, F10 | Delivery/Program Authority | POS / Inventory transaction owners |
| ABC-F11, F13, F14 | Product Authority | Marketing / Automation / Reviews |
| ABC-F17, F18 | Security & Privacy Authority | Identity / Tenant / Configuration |

## RACI operational rules

1. Each `ENG-*` and `ABC-F*` must gain **one named accountable individual** and a designated execution lead before its phase Gate; consult roles can include multiple reviewers. Governance signoffs remain separately listed.
2. Actual reviewer record requires GitHub username OR real name, verified organizational role, acceptance date, reviewed artifact SHA and evidence link; avoid publishing confidential contact details.
3. G-00 requires named human representatives for **GOV-A01..A06**, or formally approved split of authority, and independent domain/security/QA decisions on sensitive matters. No inferred review from ChatGPT conversation.
4. Product Authority may be the project decision-maker only when they explicitly confirm the governance role; legal/safety/professional qualifications are not inferred.
5. When a required approver is unavailable: record `BLOCKED`, responsible escalation owner, proposed delegate and written delegation evidence. No automatic waiver or timeout-based approval.
6. Every assigned owner has an onboarding action: read WP-000-01/02/03; accept RACI; review the associated ADRs and exception decisions; link GitHub evidence to [issue #4](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/4).

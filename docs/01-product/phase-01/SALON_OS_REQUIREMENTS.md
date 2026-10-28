# Salon Business OS — 18 Product Modules: Functional Requirements

**All modules in target scope; not all in MVP.** Design image KPI numbers are illustrative and must not be emitted as live real metrics. Global single accountable owner: `saleheebrahimi2029-hub`; specialized financial/privacy controls still require qualified review as applicable.

| ID | Module | Essential user actions | Data of record | Primary security/control | Phase |
|---|---|---|---|---|---|
| ABC-F01 | Home | Real KPIs, today's schedule, studio shortcut, Business Pulse, opportunities and quick actions | transactional appointments/sales/job events | label data freshness; no placeholder KPI as live | 10 |
| ABC-F02 | Global Search | Search clients, bookings, staff, looks, sessions, services | tenant-scoped indexes | no cross-salon data, per-role field projection | 04/10 |
| ABC-F03 | Calendar | Create/move/confirm/reschedule appointments, team/day/week, capacity/blocked states | immutable scheduling events, actual staff shifts | conflict avoidance and authorized override audit | 10 |
| ABC-F04 | Clients | Profile, visits, service history, image consent and permitted session records | CRM/consent DB | privacy, retention, identity disambiguation | 04/10 |
| ABC-F05 | AI Studio | Open/resume consult and visual iteration/plan | Session/Look/Preview/Validation | specialist privileged operations | 04–09 |
| ABC-F06 | Technical Roadmap | Draft/check/validate SOP-bound plan | plan/SOP/look/evidence | professional approval never client selection | 09 |
| ABC-F07 | Team | Profiles, shifts, skills/qualifications, availability and roles | staff registry and authorization | privilege escalation controlled | 04/10 |
| ABC-F08 | Services | Catalog, pricing, capability, duration and available/disabled states | ServicePack/SOP and price history | unsupported service not promised | 02/06/10 |
| ABC-F09 | POS | Quote, invoice, line items, payment state/refund, reconciliation | financial transactions | no AI text direct booking charge | 10/14 |
| ABC-F10 | Inventory | Stock balance, material allocation, reorder alerts, movement | inventory ledger | idempotent reservation and stock audit | 10/14 |
| ABC-F11 | Marketing | Campaigns, consent-gated follow-up/rebook | campaign and contact preferences | human-approved outreach and marketing consent | 10/14 |
| ABC-F12 | Analytics | Revenue, booking, utilization, retention, Studio conversion and QA reports | analytic views from transactions/events | lineage, no fabricated scores/trends | 04/10/14 |
| ABC-F13 | Automations | Authorized reminders, task triggers, internal operations | event/automation job log | scopes, retries, idempotency and approvals | 10/14 |
| ABC-F14 | Reviews | Collect post-service feedback, link to service/visit, triage | review log | customer data rights | 10/14 |
| ABC-F15 | Ask ABC | Query metrics, recommend an action, prepare an authorized action | scoped business queries/actions | READ/RECOMMEND/EXECUTE explicit permission | 10/14 |
| ABC-F16 | Notifications | Arrivals, validation, payment, stock, job failure, assignments | notification events | correct role/tenant; deduplication | 04/10 |
| ABC-F17 | Multi-Branch | Select branch, isolated capacity/user/service contexts | organization/tenant/branch | tenant filtering at backend/object data layer | 04/15 |
| ABC-F18 | Settings | Branding, roles, service capabilities, AI policies, language, config versions | versioned configuration | restricted changes and audit | 04/10/15 |

## Source-backed Ask ABC action model

- **READ**: retrieve permitted live (timestamped) values from reliable domain APIs with provenance.
- **RECOMMEND**: explain implications and propose actions without reporting execution as success.
- **EXECUTE**: require authorization, target scope, idempotency and confirmation for sensitive actions; record actual source-system result or failure.
- Example home quick prompts — fill empty slots, high-risk return clients, rebooking, campaigns — must not invent customer identity or a booking.

## Scheduling and handoff contracts (product-level)

Before a Look's Operational Handoff: verify selected LookVersion, specialist's qualified plan-validation state, actual service availability, appointment scope, staff qualifications, estimated duration basis and inventory/material prerequisites where material. These are **business validations**, not claims that the generated preview can be executed physically.

## Revenue and KPI integrity

`Revenue Today` = sum of settled applicable transactions minus applicable refunds/adjustments with defined business timezone and currency handling. `Utilization` needs staffed service capacity definition and valid appointment occupancy; `Available Opportunity` is only a disclosed modeled estimate based on actual slots, not booked revenue. Never hardcode reference screenshot numbers. Define formulas and dataset boundaries before implementations.

## Operational exceptions

Cancel/rebook conflict, double-book prevention, failed charge, negative stock, stale branch switch, no response from model, partial handoff and consent withdrawal all must have explicit outcome, retry and review path. Core pilot can use limited operational endpoints but cannot fake financial records.

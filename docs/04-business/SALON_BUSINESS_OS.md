# ABC Salon Business OS — Functional Architecture

This business application is coupled to AI Studio by **validated records**, not raw model-generated instructions. Mock screens may be built before data feeds; no mock KPI shown as production truth.

## Modules

| Module | Capabilities / acceptance |
|---|---|
| Home | Overview, Business Pulse, today's appointment timeline, AI Studio card, opportunities, operational status, quick actions; all tiles source to actual queries |
| Search | Tenant- and permission-scoped search for client, appointment, staff, service, session and look; no cross-tenant suggestions |
| Calendar | Day/week/team grid, booking states, collision detection, duration, staff skills and availability; atomic update |
| Clients | Consent, customer profiles, visits, consultation versions and requested privacy operations |
| Team | Role/skill profile, scheduling and professional validation eligibility |
| Services | Price, duration, status, required SOP, service pack capability and qualified specialists |
| POS | Transactions, quotes, invoices, open payments, refunds, reconciliation; ledger and permissioned write actions |
| Inventory | Ledger, material batches as required, low-stock, approved reservation/consumption/reorder; no model-direct stock mutation |
| Analytics | Definitions, currency, branch timezone, data source, denominator, period, drill-down, quality of data |
| Marketing | Campaign construction, segmentation, opt-in and review/approval workflows |
| Automations | Event-driven approved triggers, safeguards, de-duplication and audit |
| Reviews | Structured feedback, response workflow, no fabricated positive review |
| Notifications | Arrival, wait, payment, low stock, plan pending, model jobs complete, approval required; correct audience |
| Ask ABC | `READ → RECOMMEND → EXECUTE_AFTER_AUTHORIZATION` tiers; tool calls logged and validated |
| Settings | Branches, currency/locales, roles, salon branding, feature flags, SOP and image retention policies |

## Required core integration

`consultation → selected look → professionally validated plan → service requirement → specialist skill check → appointment/work order → materials check → quote/invoice`.

If plan is rejected, booking/payment/status must not be silently confirmed. Payments and inventory are governed by domain services, transaction boundaries, and reversible workflows where possible.

## Analytics provenance

Appointments booked, utilization, average ticket, rebooking, revenue and opportunity metrics each require a calculation definition, source query, time window, status treatment, timezone, currency and filter. Example UI screenshots and percentage claims are demonstration content, NOT evidence of business value.

## Rollout

Pilot: minimal client/service/staff/calendar integration with truthful status. V2: full POS, inventory and richer analytics. V3: many tenants/branches, advanced actions and localization. Design contracts and tenant boundaries at Phase 02/04 even when UI releases later.

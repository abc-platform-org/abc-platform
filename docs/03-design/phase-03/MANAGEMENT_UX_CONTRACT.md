# ABC Phase 03 — Salon OS management UX contract

**Scope:** synthetic review implementation in \`prototypes/phase03/management.html\` and standalone \`review-management.html\`; source model \`management-model.mjs\`. No actual identity, client record or transactional API.

## Role policies

| Persona | May review in management prototype | Denied / limited |
|---|---|---|
| Client | none | all management modules; same-screen participation occurs only in Studio |
| Specialist | Studio/Technical Plan routes only | CRM, finance, role config; Manager title is not professional qualification |
| Reception | home, search, calendar, clients, services, notifications and POS preview | Team qualification management; finance execution requires separate production role |
| SalonManager | operational dashboard, staff, service catalog, commercial proposals | No technical plan validation without independent specialist qualification |
| OrganizationOwner | owner-scoped management and synthetic branch change | No default access to private customer image/technical SOP |
| PlatformOperator | none | infrastructure admin is not customer-data access |

Each visible role may change in a **synthetic test selector**; this must never become a trust grant in a real frontend. Production MUST authorize all requests with server side tenant, branch, role and purpose scopes. Permission-safe projection is applied **before** rendering (not CSS hiding).

## Module-specific acceptance responsibilities

| Module | Interactive design evidence | Runtime truth |
|---|---|---|
| F01 Home | no-data KPI and source/date expectations | no hardcoded revenue or live occupancy |
| F02 Search | authorized synthetic results and empty state | no cross-tenant search or PII |
| F03 Calendar | fixture collision vs tentative draft; receipt is impossible without backend | no actual appointment created |
| F04 Clients | consent absent, no images or identifiable profile data | private photos require explicit purpose-scoped consent |
| F05 Studio | link to separate synthetic shared-session flow | not a trained model service |
| F06 Technical Plan | separate specialist-only route and authority text | no SOP or real specialist validation |
| F07 Team | synthetic staff with qualification NOT_VERIFIED | titles cannot authorize procedures |
| F08 Services | all fixture services NOT_RELEASED | do not promise unreleased chemical/service packs |
| F09 POS | proposal/forbidden action surface | never report a charge or invoice without receipt |
| F10 Inventory | no-op/empty state | no stock mutation without ledger authorization |
| F11 Marketing | draft campaign only, no send | consent, human approval and delivery receipt mandatory |
| F12 Analytics | no-data/source-trace requirements | no fabricated historical KPI |
| F13 Automations | no-operation state | future execution requires event and idempotency |
| F14 Reviews | empty and permission projection | data rights and moderated source records |
| F15 Ask ABC | READ/RECOMMEND/EXECUTE boundary design | zero natural-language direct mutations |
| F16 Notifications | synthetic notification only | requires scoped events/dedupe |
| F17 Multi-Branch | owner-only synthetic branch switch invalidates draft | real switch needs backend reauth/tenant policy |
| F18 Settings | role-gated no-op configuration projection | authorizations audited and versioned |

## Required negative behavior

- A client and a platform operator cannot see management data.
- A specialist cannot request or see CRM/POS/role-config; a manager cannot validate a specialist plan by job title.
- Two bookings for the same staff and slot cannot both succeed, even in the fixture.
- A draft is never a confirmed booking; the prototype intentionally has no API receipt path.
- A branch change resets outstanding draft/search state so no pending action is applied in another branch.
- Unreleased services always expose an honest disabled/release message.
- A proposal of a campaign is not an approval or a send.

## UX accessibility and display contract

Native button/select/input; 44px minimum controls, visible focus, Persian RTL with responsive navigation, no external fonts or images, no concealed privileged DOM on unauthorized view. Status messages are live-announced as text and meaningful errors include next action. All data and computations displayed are explicitly synthetic, including tenant and staff IDs. A real user/qualified tester must still validate accessible interaction on physical devices before final UX exit.

## Tests

\`node --test tests/phase03/management.test.mjs\` and the Chromium cases in \`tests/phase03/browser.spec.mjs\`, including role denial, staff/receipt guards, responsive layout and branch change. Automated outcomes must be tied to an exact PR SHA.

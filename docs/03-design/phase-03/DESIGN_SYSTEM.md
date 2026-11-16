# ABC-DS-03 v0.1 — Component and interaction specification

## Direction
Quiet professional workbench: ivory surfaces, forest primary actions, restrained typography and readable Persian. Client decision takes priority over decorative KPIs. Persistent synthetic banner distinguishes the UX prototype from a functioning beauty-analysis product.

## Tokens

| Token | Value | Usage |
|---|---|---|
| ink | #20362f | Primary text |
| muted | #586860 | Supporting text on light surfaces |
| paper | #f4f3ed | Workspace |
| surface | #fffef9 | Cards/forms |
| line | #d8ded4 | Non-semantic separators |
| accent | #275d47 | Primary action with white text |
| accent-soft | #e4eee4 | Information surface |
| warning | #855319 | Warning text/edge; explicit explanatory copy |
| danger | #9b3737 | Blocking/error semantics |
| focus | #95620d | 3px focus outline with 3px offset |
| spacing | 4, 8, 12, 16, 24, 32, 48 | Grid and internal rhythm |
| radii | 8, 12, 16, 18, 30 | Controls/cards/dialog/status |
| typography | Tahoma, Arial, sans-serif | Locally available Persian fallback |
| display | Georgia | Brand and nonessential English decorative numerals |

## Responsive composition

Above 1200px: navigation + three-zone Studio (controls / aligned original-preview / version decisions). 1001–1200px: gallery moves below canvas. At <=1000px: horizontal current-step navigation, canvas before controls and gallery; stacked cards, full-width primary action. No overflow hiding to mask inaccessible content. Desktop is the main in-salon surface, phone is a review/support surface. Direction is independently switchable RTL/LTR; it is not an English translation claim.

## Components

| Component | State/behavior | Keyboard and accessible contract |
|---|---|---|
| Session header | Synthetic branch/session; role indicator | Text label; role never color-only |
| Progress navigator | Current/past/future; not a permission-skipping shortcut | aria-current=step, noninteractive future steps |
| Consent controls | Separate image and text-only choices; withdrawal always visible in scenario panel | Native checkbox, persistent label |
| Service selector | Only MVP candidates progress; unavailable option explains blocking | Native select; no fake availability |
| Consultation form | Goal and maintenance retained; required unknowns block | Label-associated native controls |
| Evidence cards | Observed vs stated vs unknown | Source text visible; no numeric confidence fabrication |
| Preview canvas | Canonical framing; before/after clip | Labeled native range; same viewport for both versions |
| Look card | Version, quality fixture status, favorite, selection | Separate buttons and aria-pressed favorite |
| Version history | Append-only stored fixture objects | Parent lineage retained; production DAG contract required |
| Technical workspace | Private-only SOP/eligibility fields | Native dialog, Escape closes, no hidden privileged DOM in shared mode |
| Privacy step-up dialog | Explicit private handling check; simulated authorization | Form, dialog semantics, error text; production server session required |
| Alert/status | Reason and recovery action | aria-live polite; no silent failure |
| Processing | Pending job, stale results discarded | Disabled duplicate generation; readable status |
| Internal handoff | Awaiting receipt vs received | Close blocked without receipt; no auto-send |
| End state | With selection, no-selection, cancelled | No invented transaction; reset explicit |

## Required detailed product behavior (implementation handoff)

Transform edits allowed semantic attributes only. Try On has separately labeled reference provenance; it never transfers identity. Compare selects two immutable version IDs in a canonical frame. Inspiration is a proposal, not a recommendation or consent event. Hair palette is an experimental semantic control, not permission for chemical service. The fixture implements length variation, mode-specific reference/inspiration prompts, comparison of selected version lengths, favorites, active history pointer, undo/redo and branching. Actual AI image operations are not implemented.

Undo/redo changes the active review pointer without mutating accepted objects. Branching must name its parent and preserve locks. A selected LookVersion is immutable; revising it invalidates downstream plans/validations and requires an accepted state transition (see CONTRACT_FINDINGS.md). The isolated Phase03 addendum demonstrates the proposed transition and explicit invalidation; backend adoption requires contract review.

## Salon Business OS surfaces

Dashboard: source-dated data or honest empty state, no fake revenue. Search: authorized results and empty/forbidden states. Calendar: availability tentative until receipt. Clients: consent-bound record, no open PII in shared display. Team: role and qualification scope. Services: per-pack release badge. POS, inventory, marketing, analytics, automations, reviews, Ask ABC, notifications, settings and subscriptions follow the Phase-01 release matrix; this phase supplies design mapping, not business execution. Management surfaces must require a separate authorized projection; specialist privileges do not imply management privileges.

## Accessibility acceptance target

Text contrast target 4.5:1 normal / 3:1 large, meaningful controls 3:1; calculate before signoff. Touch controls minimum 44x44 CSS pixels. Keyboard order follows visual task order; no inaccessible pointer-only required action. Labels and errors remain visible at 200% zoom. Announce pending/failure; move focus to the new heading after stage changes without disrupting input changes. Screen-reader and actual iOS/Android device verification remain required evidence before G03 PASS. Reduced-motion preference respected; no flashing or autoplay.

## Content and error policy

Use Persian explanatory text and short actionable labels. No “approved” without an explicit approval type. QA failure: retry or keep last accepted version. Unavailable capability: explain scope, no fabricated alternatives. Offline: deny mutations, preserve visible session. Consent withdrawal: cancel pending jobs, remove images and prevent new processing. Unauthorized view: safe screen plus reauth request; private data never sent to shared API projection. Empty-state close is a valid outcome.

## Phase-03 v0.2 implementation reconciliation

The Phase-03 branch now contains two distinct synthetic, responsive review experiences: shared in-salon Studio and role-projected Salon OS management. The management model references all 18 ABC-F IDs; sensitive transactions are not performed. Privileged data is removed from shared-mode DOM rather than only hidden with CSS. Selected appearance, specialist feasibility, human validation, and backend receipt remain separate transitions.

Studio LookSpec fixture controls now record service, mode, palette, target region, front-view provenance and locked-region policy. Side/back requests without evidence do not produce an accepted preview. This is semantic interface behavior only, not actual model inference or image generation.

Measured token contrast pairs: body text 11.59:1, supporting text 5.84:1, primary white-on-forest 7.66:1, warning 5.62:1, danger 6.94:1. Automated checks cover defined token pairs, not every rendered UI state. Device/assistive-technology audits remain unexecuted.

Build and compare the exact self-contained Studio and Salon OS files with `python scripts/build_phase03_review.py --check`; browser E2E checks and screenshots are in GitHub CI. These review artifacts are not production applications.

# AI Studio — Professional Workspace Specification

Document: `ABC-AIS-001` | product critical path | `PROPOSED`

## UX composition

Desktop / touch, three-column studio: (left) client/session/service and service-aware controls; (center) before/after visual canvas, zoom, fit, mask overlay, safe fullscreen, QA/version status; (right) generated look gallery, favorites, filters, inspiration, selected detail, professional status. Header: Hair, Color, Makeup, Skin, Nails, Beard, Grooming, Style; Modes: Transform, Try On, Compare, Inspiration and post-selection Technical Plan. Footer: version, autosave/session state, protected specialist action.

## Shared-screen behavior

Specialist owns keyboard and authentication; client chooses in a shared presenter view, optionally taps assisted controls. Financial, personal history, diagnosis-like claims and expert-only protocols must not be publicly exposed via accidental modal/drilldown. A specialist unlock is required for privileged actions. All images displayed are scoped to the active client and branch.

## Functional matrix

`AIS-001..026` are the normative inventory in `../01-product/FEATURE_INVENTORY.md`. Supported visual modes:

- **Transform:** apply known requested change to authorized service-specific region and desired style attributes.
- **Try On:** transfer style direction from reference without copying identity.
- **Compare:** pairwise or multi-look common-base visual + explanation table, aligned crop/lighting where possible.
- **Inspiration:** generate distinct valid grounded directions and cite look constraints; do not generate artificial third option.
- **Technical Plan:** downstream conditional professional review, not an image-generation shortcut.

## Service-aware controls

| Service | Controls |
|---|---|
| Haircut | silhouette, sections/length zones, layers, texture, fringe, volume |
| Hair color | depth, tone, warmth, dimension, highlight placement, intensity |
| Beard | shape, beard volume appearance, line and length style, taper |
| Makeup | eye/lip/cheek/brow region, intensity, finish, palette, occasion |
| Nails | shape, length, surface finish, color, art pattern |
| Skin beauty | appearance/finish and makeup prep only, no medical inference |
| Extensions | desired visual length, volume, distribution |
| Bridal | multiple independent masks and separately accepted sub-looks |

A UI slider changes `LookSpec` semantics, not an invented physical service parameter. Each service has its own capability profile and mask restrictions.

## UX state coverage

`NO_CLIENT`, `CONSENT_REQUIRED`, `INPUT_MISSING`, `INPUT_INSUFFICIENT`, `ASKING`, `ANALYZING`, `GENERATING`, `QA_FAILED`, `LOOKS_READY`, `REFINING`, `SELECTED`, `PLAN_IN_REVIEW`, `VALIDATED`, `FAILED_RECOVERABLE`, `COMPLETED`. Empty/loading/error states must have explicit action and non-disruptive guidance.

## Design fidelity to supplied references

Preserve navigation groups (Home, Calendar, AI Studio, Clients, POS, Team, Services, Marketing, Inventory, Analytics, Automations, Reviews, Settings), visual before/after slider, look gallery, palettes, top global search and salon dashboard. **Do not copy fabricated sales/rebooking KPIs, +32/+28/+41 outcomes or promotional proof labels** from visual concepts.

## Outbound actions

UI `Download/Share` and `Book This Look` are rewritten to `Internal Record / Hand off / Select Look / Continue to Technical Plan`. No remote customer preview mailing or at-home self-service.

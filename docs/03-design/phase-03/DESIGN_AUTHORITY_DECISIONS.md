# ABC Phase 03 — Delegated design decisions and provenance exceptions

As-of: 2026-10-29. Authority: delegated **engineering/design** decision-making only. This record is not a specialist, independent accessibility, security, legal/privacy or product-release signature.

## DAD-03-001 — Canonical design reference disposition

- Six historical user-supplied interface references for the dashboard and AI Studio are mentioned in the baseline source register, but **their underlying image files / reliable exact visual identities were not recovered** in the PR or available file search.
- Decision: use the canonical **behavioral** PRD, 64 requirement IDs, 32 role rules, state contracts and three-zone desktop UX as non-negotiable sources; retain the existing restrained ivory/forest token direction as an **explicit provisional design system** for synthetic demonstration.
- Pixel-by-pixel matching to six unseen images is **NOT_VERIFIED**. Do not assert such fidelity and do not fabricate original screenshots or source attributions.
- Provenance risk: external brand/visual identity signoff and later comparison remain outstanding if these references are supplied or re-discovered. The Phase-03 experience must continue functioning independently of historical art.

## DAD-03-002 — Selected-look revision after specialist handoff planning

- Accept \`ABC-CR-03-001\` **for Phase-03 synthetic UX only**, with immutable selected parent, invalidation of downstream feasibility/plan/validation, expected-state-version and idempotency in future backend contract.
- No v1 state-machine/OpenAPI/event/schema mutation in this PR. Product runtime adaptation requires an explicit compatible contract version, tests for conflicts/replay/outbox/consent, and separate implementation acceptance.
- Irreversible business receipt must not be reversed by editing an image; require an independent compensating operation.

## DAD-03-003 — Management workspace

- Two distinct display surfaces: shared salon consultation (client participatory; specialist-operated), and permission-restricted management workspace. Never treat a role dropdown as authentication.
- All 18 ABC-F module IDs have screen navigation/disposition. Synthetic interactive cases cover booking collision, tentative receipt, scoped search, consent directory, staff qualifications, service release status, branch switch and campaign proposal.
- V2/V3 modules have accountable empty-state/projection design and are explicitly NOT_IMPLEMENTED. No real POS/revenue, booking, campaigns, data APIs, financial ledger or sensitive records.
- A management title cannot validate specialist Technical Plan. Visual selection cannot approve a professional plan.

## DAD-03-004 — Phase exit and visual release are different gates

- \`P03-UX-EXIT\` is a **design phase** decision; \`G-03\` in \`docs/05-delivery/RELEASE_GATES.md\` is the **visual product release** gate.
- Successful synthetic unit/Chromium checks advance Phase-03 design readiness only. No engine release, real customer or salon transaction is allowed.
- The Design Authority may accept design direction, but cannot manufacture iOS/Android/VoiceOver/NVDA evidence or qualified specialist/security signoff.

## Immutable trace pointers

- [Integrated Phase 00–02 design baseline, PR #19](https://github.com/saleheebrahimi2029-hub/abc-platform/pull/19)
- [Phase 03 implementation, PR #21](https://github.com/saleheebrahimi2029-hub/abc-platform/pull/21)
- [P03 issue #20](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/20)
- [Hard real-runtime release blockers, issue #18](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/18)

Decision state: **ACCEPTED_FOR_PROTOTYPE_DESIGN_WITH_DISCLOSED_PROVENANCE_EXCEPTION**; not final pixel-fidelity or operational release approval.

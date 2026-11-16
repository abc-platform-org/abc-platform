# Phase 03 UX verification protocol

## Executed automated suite
Run `node --test tests/phase03/model.test.mjs` on the PR tree. The suite exercises a positive complete fixture journey and negative permission/consent/QA/staleness/offline/recovery/receipt paths. It verifies happy-path session edges against the accepted machine, not merely a duplicate list. No test proves production security or real visual quality.

## Browser walkthrough script
1. Fresh page: next without consent must remain at consent with explanation.
2. Choose image consent; choose haircut; answer goal + maintenance; advance through input/analysis.
3. Generate fixture; confirm clearly synthetic image and version ID.
4. Fail QA or send stale result: last accepted version retained, invalid result not selectable.
5. Favorite: no selection/approval. Select accepted version: goes to LOOK_SELECTED, not validated.
6. Enter private mode without private-screen checkbox: dialog error, no private fields.
7. Confirm private handling; advance to feasibility. Without SOP/evidence: blocked.
8. Check fixture evidence; draft plan. Without qualification: blocked.
9. Qualify fixture, review exact version, handoff. Without receipt: cannot close.
10. Receive fixture receipt, close; no real booking/payment/send.
11. Return to shared: SOP/qualification/validation details absent from rendered DOM.
12. Pause/recover and offline mutation paths; revoke consent during pending generation.

## Additional acceptance matrix (NOT EXECUTED unless evidence recorded)
- 390px, 768px, 1440px viewport; 200% zoom; RTL/LTR.
- Keyboard-only traversal, dialog Escape/focus return, native slider arrows.
- VoiceOver iOS / NVDA: field/error/status and stage changes announced.
- Contrast computation for every functional text/background pair.
- Actual tablet touch behavior and focus/virtual keyboard.
- Expert/client paired salon walkthrough, comprehension of selection vs execution.
- Revision-after-selection once CR-03-001 is resolved.
- Advanced Studio modes and management projections.

Record test ID, input state, steps, observed result, exact source SHA, environment, reviewer and evidence. Unexecuted is not PASS. Human domain review must never be simulated by the assistant.


## Post-interruption Phase-03 execution additions (2026-10-29)

**Executable:** \`tests/phase03/model.test.mjs\` (43 modeled scenarios), \`tests/phase03/management.test.mjs\` (20 modeled scenarios), \`tests/phase03/contrast.test.mjs\` (defined WCAG token contrast pairs), \`tests/phase03/browser.spec.mjs\` (5 Chromium E2E cases). All run through \`.github/workflows/phase03-design-integrity.yml\`. Observed outcomes must always be cited to the exact PR SHA, not inferred from test source.

Chromium coverage:
- 390, 768, 1440 CSS-pixel widths; document-level overflow check; retained screenshots;
- shared salon consultation → synthetic preview → selected Look → protected specialist review → technical plan/receipt → close;
- unauthorized attempt to enter private area without explicit screen handling;
- handoff private projection, return to shared, hide receipt, re-enter specialist;
- dialog Escape and focus return, RTL/LTR change, management Client denial, Reception blocked/allowed booking paths, Manager qualification and OrganizationOwner branch-only scope.

**Still NOT_EXECUTED / independent acceptance:** true 200% user browser zoom (deviceScaleFactor does **not** count), functional contrast across all states, actual physical mobile/tablet orientation+touch+virtual keyboard, VoiceOver iOS, NVDA desktop, independent salon client/specialist observation, historical six-reference image comparison, real backend security and real visual QA. None of these may be marked PASS by a browser screenshot or synthetic unit test.

**Reproduction:** \`python scripts/build_phase03_review.py --check\` guarantees committed standalone review files match source; Chromium CI uploads screenshots as an artifact attached to the exact run. All red-team fixtures are synthetic and non-identifying.

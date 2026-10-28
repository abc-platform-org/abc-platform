# ABC AI Studio — Phase-01 Product Acceptance Specification

**Status:** DOCUMENTED, NOT IMPLEMENTED. This is the heart of the product. Specialist + client jointly work on one *in-salon screen*. The specialist controls privileged actions.

## 1. Layout and command surfaces

- Three-zone desktop/touch UI: **Input/Controls** / **Before-After Canvas** / **Look Gallery & Decisions**; semantic service tabs and four working modes.
- Left: session and client, service/style with service-specific attributes, advanced controls with typed bounds, quality/consent state, Generate.
- Center: canonical client original, selected preview, draggable Before/After, zoom/fit/fullscreen, region overlays and locked-region map, generated state.
- Right: Looks (candidate alternatives, card provenance and tags), favorites, shortlist, previews, iterative edits, Look Details, feasibility preview and next-action.
- After LookSelected, activate **Technical Plan** as a non-generative mode with specialist-only privileged details.
- Footer: versions/history, authorized internal handoff, operation feedback; do not offer auto-remote share to client.

## 2. 26 AIS acceptance requirements

| ID | Acceptance objective | Proof suite |
|---|---|---|
| AIS-001 | Authorized specialist creates tenant/branch-scoped durable consultation with unique ID | SES-01 / SEC-01 |
| AIS-002 | Client and reference images are source-labeled and blocked without valid consent | INP-01 / SEC-02 |
| AIS-003 | Invalid angle/quality/lighting flagged with retake or transparent constrained mode | INP-02 |
| AIS-004 | Service-specific dynamic questions select meaningful unknowns and stop appropriately | PQ-01..03 |
| AIS-005 | Controls change by service and update LookSpec rather than arbitrary image effects | UI-SVC-01 |
| AIS-006 | Reference changes style, not borrowed identity or private unrelated appearance | VIS-REF-01 |
| AIS-007 | Recommendation complies with hard constraints; explanations and unknowns inspectable | DEC-01 |
| AIS-008 | LookSpec persists independently of image/model/provider | LOOK-01 |
| AIS-009 | Transform edits only specified target attributes and marks visually failed results | VIS-TR-01 |
| AIS-010 | Try On transfers allowable features, not reference identity, with per-service QA | VIS-TRY-01 |
| AIS-011 | Generates distinct qualified alternatives, never fabricated surplus candidates | VIS-VAR-01 |
| AIS-012 | Before/After uses same original coordinate identity and explicit revision label | VIS-CANVAS-01 |
| AIS-013 | Compare keeps identical original/base framing, distinct tradeoffs and selected state | VIS-CMP-01 |
| AIS-014 | Locked pixels outside editable region unchanged in canonical frame; boundary QA | VIS-02 |
| AIS-015 | Changing a single attribute retains already accepted unrelated attributes | VIS-04 |
| AIS-016 | Version graph immutable and supports undo/redo, compare, branch and recovery | VIS-05 |
| AIS-017 | Shortlist/favorite creates durable session-scoped preference without implying authorization | DEC-SEL-01 |
| AIS-018 | Inspiration proposals are relevant, distinct and obey user context | DEC-INSP-01 |
| AIS-019 | Palette choices map to service-specific semantic attributes and LookSpec | LOOK-PAL-01 |
| AIS-020 | Failed quality/identity/region output not offered as QA-passed selected preview | VIS-QA-01 |
| AIS-021 | Aesthetic fit, physical feasibility and safety uncertainties remain distinct | TEC-02 |
| AIS-022 | Selected LookVersion immutable snapshot with explicit who/when/session binding | LOOK-LOCK-01 |
| AIS-023 | Technical plan remains draft/blocked unless SOP and essential evidence exist | TEC-03 |
| AIS-024 | Only authenticated qualified salon specialist can validate exact plan/evidence/version | TEC-04/05 |
| AIS-025 | Handoff preserves customer/service/LookVersion/validation state and checks permission | INT-01 |
| AIS-026 | Crash, retry, stale result, disconnect and resume preserve last authorized state | SES-REC-01 |

## 3. Visual Engine policy and service-specific profiles

- `VQ-01` Identity preservation: non-target face/appearance must not be arbitrarily beautified.
- `VQ-02` Region fidelity: hard-locked pixels are preserved via deterministic compositing; editable edges require naturalness review.
- `VQ-03` Accepted state preserved through revisions.
- `VQ-04` Reference identity never transferred.
- `VQ-05` Multi-region version/mask/QA in advanced composite services.
- `VQ-06` Failure transparency for unusable previews and unavailable provider.
- `VQ-07` Visual confidence is distinct from physical execution feasibility.

Mandatory preview stages: client/reference image input → quality gate → service analysis + LookSpec → segmentation / editable regions → controlled generation → deterministic locked-region compositing → visual QA → versioned preview. **A single free-form image generator must not own output release.**

Change types: `COLOR_CHANGE`, `GEOMETRY_LENGTH`, `TEXTURE_CHANGE`, `FACIAL_HAIR_SHAPE`, `MAKEUP_OVERLAY`, `NAIL_DESIGN`, `MULTI_REGION`; one model/QA configuration for all types is insufficient.

Multi-view: preserve original/front/side/back provenance, ask for view relevant to service, and never hallucinate unseen back-of-head hair geometry as observed.

## 4. Interaction states

`SESSION_INITIALIZED → CONSENTED → CONSULTING → ANALYZED → OPTIONS_READY → PREVIEW_REVIEW ↔ REVISION → LOOK_SELECTED → FEASIBILITY_REVIEW → PLAN_DRAFTED → SPECIALIST_REVIEW → HANDOFF → CLOSED`, with `FAILED_RECOVERABLE`, `SAFETY_BLOCKED`, `CANCELLED`, `PAUSED`.

Selection cannot create `PROFESSIONALLY_VALIDATED`. Technical plan cannot be created with fabricated chemical manufacturer timing.

## 5. Visual acceptance test design

For every released service: segmentation dataset versions, identity drift/region lock, accepted-state regression, reference isolation, multi-frame/camera angle consistency, perceptual quality human evaluations, reproducible job metadata, latency and cost/preview. Numeric acceptance thresholds are POC/benchmark-derived rather than invented at PRD time. Failures are explicit, not hidden.

## 6. Specialist view safety

Shared: permitted image and understandable model details. Privileged: hair chemical history, SOP, risk and private professional note. Backend authorizes all data; a hidden panel is insufficient. If a client remains watching the same screen, sensitive data should not be revealed until protected handling is available.

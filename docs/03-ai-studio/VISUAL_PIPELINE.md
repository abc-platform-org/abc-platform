# Visual Intelligence Pipeline — ENG-08..ENG-11

## Five capability classes

1. `COLOR_CHANGE` — precise hair/beard or requested color region.
2. `LENGTH_OR_GEOMETRY_CHANGE` — haircut/extension silhouette; anatomically plausible expansion boundary requires distinct masks and multi-angle checks.
3. `TEXTURE_STYLE_CHANGE` — only authorized hair/beard texture region and geometry.
4. `SURFACE_APPLICATION` — makeup eye/lip/cheek/brow or nail plate separately.
5. `MULTI_REGION_COMPOSITE` — independent masked edits per component with independent QA and rollback.

## Pipeline

`Input QA → service-aware segmentation → LookSpec + constraints → image edit adapter → deterministic compositing → identity/region/target QA → versioned preview publication`.

## Fidelity invariants

- VQ-01 identity preservation prioritized over attractive altered face.
- VQ-02 strict region fidelity: hard-locked pixels untouched, feather boundary defined and tested.
- VQ-03 accepted-state preservation: selected unrelated attributes/regions remain locked across iteration.
- VQ-04 reference style separated from reference person identity.
- VQ-05 multi-region independently masked, generated, tested and revertible.
- VQ-06 QA fail ≠ pass; transparent fallback and retry.
- VQ-07 visual plausibility does not imply physical feasibility.

## Deterministic compositing

`final[p] = original[p]` outside allowed mask and any explicitly defined feather band; blend only inside allowed boundaries. Canonical comparison must use same color space, size, decoding and image representation. Outside-boundary equality is a code invariant; **identity retention inside altered areas is not mathematically guaranteed** by compositing.

## QA dimensions

- Mask boundary leakage, outside-mask pixel difference and accidental beautification.
- Identity continuity and facial geometry (computer vision plus human review).
- Requested transformation fidelity vs `LookSpec` attributes.
- Hairline, hands, ears, glasses, accessories, occlusion and lighting integration.
- Compare across multiple views; avoid presenting a front-view approximation as full 3D accuracy.
- Generation stability across versions and provider changes.

## Policy and failure

No QA-passed label for failed visual jobs. Never replace original image. Return structured `VISUAL_QA_FAILED`, `INPUT_INSUFFICIENT`, `UNSUPPORTED_TRANSFORMATION`, `CONFLICTING_MASK`, or `PROVIDER_UNAVAILABLE` as appropriate. Fallback to a bounded explanation, unmodified image or alternate direction; never claim a preview was generated when it was not.

## Calibration

Thresholds for identity score, masks, geometry realism, latency, and acceptable artifacts remain `OPEN` until actual diverse test images, specialist grading and statistical analysis. Synthetic-only passes are insufficient for release.

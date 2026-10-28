# WP-000-02 — Evidence Classes, Test Claims & Approval Controls

| Claim class | Sufficient evidence | Insufficient evidence | Current verified state |
|---|---|---|---|
| Source exists and content read | Source page/file ID plus actual content and version | Citation from another document | Legacy Notion read; missing three parents remain unrecovered |
| Documentation completeness | Markdown validator/CI run, manifest hashes, reviewer | `PASS` in self-authored text alone | Documentation integrity workflow passed |
| Engine implemented | Source tree, code SHA, running component and contract test | Engine filename or conceptual role | NOT_VERIFIED |
| 120 Golden tests passed | Execution run ID, per-case verdict, artifacts, human review | 120 authored scenarios | NOT_RUN / NO_EVIDENCE |
| Model image identity preserved | calibrated multi-service benchmark and expert sample review | A few good photos or prompt instruction | NOT_VERIFIED |
| Chemical service safe to execute | specialist-validated SOP, material/label checks, client-specific evidence, signed plan | Attractive generated image, freeform plan | NOT_VERIFIED |
| Multi-tenant isolation | negative tests at API/DB/object-storage and audit trail | Frontend hidden controls | NOT_VERIFIED |
| Formal Gate-00 passed | signed authority/exception/ADR review and no blockers | User request to execute audit, CI success | NOT_PASSED |

## No misleading equivalence

- `TEST_AUTHORED` ≠ `TEST_EXECUTED` ≠ `TEST_PASSED`.
- `FEATURE_SPECIFIED` ≠ `API_CONTRACT_SIGNED` ≠ `IMPLEMENTED` ≠ `RELEASED`.
- `RECOMMENDED_LOOK` ≠ `FEASIBLE` ≠ `SPECIALIST_VALIDATED` ≠ `SERVICE_AUTHORIZED`.
- `LEGACY_CANONICAL` ≠ `TARGET_PLATFORM_CONTRACT_APPROVED`.

## Minimum Phase-00 evidence chain

Source item → quoted/paraphrased *bounded* rule → authority row `AUTH-*` → conflict resolution `RES-*` → migration `MIG-*` → target `ADR-*` → test suite / phase → reviewer disposition. New claims lacking an attributable source require their own explicitly proposed platform decision.

## Test sequence for implementation

For each selected MVP service: question/value evaluation; evidence provenance and missing fields; ranking invariants; image mask and reference isolation; iterative versioning; image QA; feasibility/safety; SOP plan and human validation; role and tenant negative tests; session interruption/recovery; business transaction authorizations. Calibration thresholds only after representative test set and expert review.

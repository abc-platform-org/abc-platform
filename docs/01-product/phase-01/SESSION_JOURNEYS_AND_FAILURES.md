# ABC User Flows — In-Person Shared Screen, Full Path + Failures

## 1. 15-stage default journey

| Step | Responsible on-screen party | User-visible behavior | Backend/engine outcome |
|---|---|---|---|
| 1. Welcome | Specialist | Open client or appointment, start visit | `CREATED`, tenant, branch, identity |
| 2. Consent | Specialist + client | Inform of image use, purpose and retention | `CONSENTED` with version/scope |
| 3. Define intent | Both | Hair/beard/makeup/etc., specific or explore | `INTENT_DEFINED` |
| 4. Adaptive questions | ABC with both | Targeted short questions; avoid repeats | `ConsultationProfile` + evidence |
| 5. Capture images | Specialist | Client/reference, angle guide | image roles, quality and permissions |
| 6. Analysis | ABC, reviewed by specialist | explain relevant observed/unknown features | provenance-tagged `AnalysisResult` |
| 7. Recommend | Both | Qualified candidates + reason/tradeoffs | `RecommendationSet` |
| 8. Preview | Both | Before/After, Transform/Try On | QA report per `LookVersion` |
| 9. Refine/Compare | Both | Lock regions, sliders, shortlist, compare | immutable look/preview version graph |
| 10. Select | Client preference + specialist navigation | Choose exact version | `LOOK_SELECTED`, **not** approval |
| 11. Feasibility | Specialist | Inspect real client state/checks | `FZ-1/2/3` and unknowns |
| 12. Plan | ENG-15 under specialist | Draft procedure and conditional checks | `PLAN_DRAFT`, SOP/evidence bound |
| 13. Validate | Qualified specialist | Accept/conditional/revise/reject | signed specialist validation on exact versions |
| 14. Handoff | Authorized salon operator | internal work order/book/POS linkage | event and domain action receipts |
| 15. Close | Specialist | summary, no private data leakage | closed/resumable audit, aftercare when supported |

## 2. Exception paths — mandatory acceptance stories

| Case | Expected behavior | Acceptance suite |
|---|---|---|
| Photo consent absent | no image processing; optional text-only advisory, explicit limitations | SEC-02 |
| Client declines photo use mid-session | revoke future processing, manage cached/derived assets per retention policy | PRIV-01 |
| Low light/cropped reference | retake or limited advisory, no invented details | INP-02 |
| Reference photo contains another person | extract permitted style only, no reference identity transfer | VIS-REF-01 |
| Client says no time for daily styling but chooses high-maintenance look | ask reason/clarify tradeoff; don't silently override preference | PQ-02 |
| Uncertain chemical treatment history | no actionable chemistry plan; professional check needed | TEC-03 |
| Generated preview failed masked region QA | mark failed, no selectable QA-approved output | VIS-02 |
| Long-running image job failed or stale | keep last accepted version; retry with correlation ID | SES-REC-01 |
| Client changes mind after Look locked | new LookVersion; invalidated plan/approval dependencies | TEC-05 |
| Unsupported style/service | transparent `CAPABILITY_UNAVAILABLE`; do not fake three options | DEC-01 |
| Unqualified staff tries approval | deny backend validation; audit attempt | SEC-01 |
| Same screen reveals private note accidentally | fail-closed shared projection and reauth gate | SEC-SH-01 |
| Branch switch during active session | require explicit new branch context and reauthorization | SEC-TEN-01 |
| No material/staff capacity | conditional work order or no booking; never false reservation | BUS-01 |
| Client leaves without choosing | valid closed session `NO_SELECTION`, no fictional look approval | SES-01 |
| Client wants at-home account/send | respond that product flow doesn't provide client portal; permitted internal handoff only | UX-SCOPE-01 |

## 3. Session state model (product intent)

`CREATED → CONSENTED → INTENT_DEFINED → INPUTS_COLLECTING → INPUT_READY → ANALYZED → OPTIONS_READY → PREVIEW_REVIEW ↔ REVISION_REQUESTED → LOOK_SELECTED → FEASIBILITY_REVIEW → PLAN_DRAFTED → SPECIALIST_REVIEW → HANDOFF → CLOSED`.

Side states `PAUSED`, `CANCELLED`, `FAILED_RECOVERABLE`, `SAFETY_BLOCKED` and `CLOSED_NO_SELECTION`. Phase-02 makes transition table executable and event idempotent. Every change must be authoritative on server, tenant-scoped and replay-safe.

## 4. Shared vs private

Shared: image, choices, selected look, intelligible explanations and caveats. Specialist-only: risk checks, protocol, materials, private notes, plan approval. Management-only: finance and organization settings. On SAME device, backend security protects data and privileged step-up auth; merely hiding a drawer is not sufficient.

## 5. Completion evidence

Interactive design prototype of all 15 steps is a Phase-03 prerequisite. Executable end-to-end E2E test is Phase-11, expert pilot Phase-12; neither is claimed as done in Phase-01.

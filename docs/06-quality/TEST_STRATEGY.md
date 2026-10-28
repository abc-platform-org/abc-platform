# Quality, Benchmark & Test Strategy — ABC-QA-001

## Legacy suites

`ABC-TC-001..120`: canonical historical cases authored, **not known executed or passed**. Preserve IDs. 17 legacy evaluation dimensions include intent/state, evidence, analysis, recommendation, tradeoffs, knowledge, safety, capability truthfulness, output, preview, salon config, efficiency, mode, fairness, commercial integrity, failure/recovery, multi-turn consistency.

## New suite registry

| Suite | Target |
|---|---|
| QST-01 | Question relevance, ordering, no repeats and stopping |
| INP-01 | Asset provenance and valid consent |
| INP-02 | Input quality across lighting, angle, occlusion |
| ANA-01 | Service-bounded evidence and no diagnosis |
| DEC-01 | Hard filters, salon availability, deterministic qualitative decisions |
| LOOK-01 | Structured look independent of image |
| VIS-01 | Segmentation coverage and safe boundaries |
| VIS-02 | Hard-locked pixel equality beyond feather zone |
| VIS-03 | Identity continuity, visual realism and no unwanted retouch |
| VIS-04 | Non-destructive selective revision / accepted-state preservation |
| VIS-05 | Version DAG, undo/redo, compare same source, stale job |
| VIS-06 | Multiple regions/multiple views and independent rollback |
| TEC-01 | Plan references exact selected look and SOP |
| TEC-02 | Image pass not confused with feasibility |
| TEC-03 | No unsupported procedural parameters; critical unknowns block |
| TEC-04 | Authenticated professional validation, refusal and override |
| TEC-05 | Material changes invalidate plan approval |
| SES-01 | Disconnect, crash, resume, concurrent edits |
| SES-02 | Shared-screen privacy and authorization boundaries |
| BUS-01 | KPI provenance and real transaction computation |
| INT-01 | Cross-domain handoff and idempotent operation |
| SEC-01 | Tenant/branch & backend permission isolation |
| SEC-02 | Consent expiry, revocation, asset lifecycle |
| OBS-01 | Traces, error diagnosis, replay safety |
| REG-01 | Cross-engine/model/provider regression |

## Visual benchmark stratification

Representative consented images for hair colors/textures/lighting, different hairstyles and facial geometries, head pose, eyewear/occlusion, different skin tones, hair/beard overlap, image resolution, adult clients, multi-view, hand/nail/makeup. Protect personal images and never use them in source-control test fixtures. Label service region masks, unaffected pixels, reference intent, human accept/reject and uncertainties.

## Safety & human review

Professional specialist panel must review representative service cases. Chemical, sensitivity/medical and advanced-service SOP checks are release blockers. Severity taxonomy: SEV-0 catastrophic safety/security, SEV-1 major fidelity/consent/invalid handoff, SEV-2 moderate, SEV-3 minor UX. Severity mapping and sign-off must be approved, no blanket 'all tests passed' without evidence.

## Observability metrics

Time-to-usable-preview, QA pass rate, unwanted-change rate, selective-revision preservation, specialist override rate, professional plan readiness, session completion with honest null outcomes, handoff consistency; monitor by service and version. Benchmark targets are open until representative empirical calibration.

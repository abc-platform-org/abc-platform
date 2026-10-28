# Independent engineering design review — ADR-001…010 (2026-10-29)

**Disposition status:** ENGINEERING_RECOMMENDATION_ONLY. Project owner approval has **not** been recorded. Each original ADR retains its existing Git blob SHA; no historical ADR text is rewritten.

**Review basis:** ten ADR documents under `docs/00-governance/adrs/`, Phase-01 product requirements/role matrix, Phase-02 19-engine draft interface contracts, exact HEAD `164c512a944faf186144fdbb0d88dcabee871ade`, and Gate policy. This is a document/contract review, **not** independent implementation, cybersecurity, legal, image quality or qualified beauty safety validation.

| ID | Recommendation for DESIGN_ONLY | Reason and required closure condition | Runtime/release stop |
|---|---|---|---|
| ADR-001 | CONDITIONALLY_SUPPORT | Standalone modular runtime with typed independent engines avoids GPT-only memory/security faults. Freeze **logical contracts**, not unbenchmarked runtime provider/service topology. POC durable workflow, worker isolation and failure recovery before selecting stack. | G-04 executable service framework |
| ADR-002 | SUPPORT_WITH_HARD_PRIVACY_BOUNDARY | Shared in-salon screen with authenticated specialist is confirmed product intent; client participation must not confer account access. Require server-side field projection and explicit privileged view reauthentication. | G-06 / G-09 before genuine customer data |
| ADR-003 | SUPPORT_WITH_VERSIONED_SCHEMA | LookSpec must be independent of preview bytes; include immutable parent graph and exact version/evidence/SOP pinning. Version migration evidence still required. | G-04 data/contract integration |
| ADR-004 | CONDITIONALLY_SUPPORT | CV segmentation + bounded synthesis + deterministic compositor is auditable, unlike unbounded image regeneration. Exact mask, canonical coordinates, and cross-view geometry not measured. | G-03 visual POC and G-08 real-data benchmark |
| ADR-005 | SUPPORT_WITH_FAIL_CLOSED_QA | Identity, locked region, reference isolation, boundaries and human review evidence must all pass before publishing as accepted visual preview; visual QA is *not* feasibility. | G-03/G-08 calibration, falsification and expert comparison |
| ADR-006 | SUPPORT_WITH_CONCURRENCY_PROOFS | Version DAG plus compare-and-swap and stale job rejection avoids lost edits. Need executable concurrent modification/replay/failure testing. | G-04 worker and database race tests |
| ADR-007 | SUPPORT_WITH_PROFESSIONAL_BOUNDARY | Visual outcome cannot certify hair/skin chemistry or actual physical execution. Professional evidence and service-specific qualified review mandatory. | G-05 service feasibility |
| ADR-008 | CONDITIONALLY_SUPPORT | Draft technical roadmaps must be grounded in reviewed SOP and exact selected Look, with mandatory qualified specialist review; missing evidence/chemical SOP => STOP. No recipe/time/ratio generated absent approved manufacturer protocol. | G-05/G-08 qualified safety approval |
| ADR-009 | CONDITIONALLY_SUPPORT | Durable server-side workflow, transactional outbox, idempotent actions and event deduplication are appropriate. No exactly-once network guarantee; prove replay safety, retries, compensation and stale event rejection before runtime acceptance. | G-04 stateful orchestration stress tests |
| ADR-010 | SUPPORT_WITH_MANDATORY_SECURITY_EVIDENCE | Tenant identity from verified server auth; purpose-bound consent and role projection. Written policy cannot prove penetration/security or lawful processing. | G-06/G-09 independent auth, privacy and legal tests |

## Cross-ADR dependency checks

1. **ADR-002 + ADR-010:** Shared display UI must use **server-generated** client-safe projections. CSS-only hiding is prohibited; reject privileged data at API level.
2. **ADR-003 + ADR-006 + ADR-009:** Selected LookVersion, job/source hash, SOP and professional validation must be atomically checked. Any material change invalidates authorization.
3. **ADR-004 + ADR-005:** A generated image may be *previewable* only on QA PASS, but QA PASS is only an image-quality decision, not service viability.
4. **ADR-007 + ADR-008:** No technician plan receives EXECUTION_APPROVED state from model output; qualified human credentials must be verified server-side.
5. **ADR-001 + ADR-009 + ADR-010:** Durable workflows need tenant boundaries, outbox idempotency, private media object scoping and audit traces by design.
6. **ADR-010 + Phase-01:** All 11 service families start NOT_RELEASED. Even visual-only hair color needs separate QA and safety review; migration from legacy GPTs is not service release.

## Unresolved contract and release evidence (explicitly outside current pass)

- No 19 engines deployed; no hardware/camera/runtime benchmark.
- Event/payload schema fixtures **do not** authenticate a publisher; server outbox principal validation required.
- API contract 401/403 and policy-guard declaration **do not** prove enforcement; backend RBAC/tenant integration and negative tests required.
- Existing reviewer absence remains: qualified hairstylist/barber, SOP manufacturer evidence, privacy/legal jurisdiction and independently evaluated visual QA.
- Three historical parent versions not recovered as independently verifiable bytes; source-exception acceptance is required for design authority freeze.
- Full approval still needs actual owner decision per ADR **on the SHA of the original blob** in `ADR_DECISION_MATRIX.csv`, exact reviewed Phase-01/02 heads, and recorded release constraints.

**Recommendation:** Support all ten architecture directions **conditionally for a DESIGN_ONLY baseline**, with proof obligations assigned to later hard gates. This is independent engineering analysis, **not** an actual owner GitHub review, and should not itself change an ADR status to ACCEPTED or declare G-00/01/02 PASS.

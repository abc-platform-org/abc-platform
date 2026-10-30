# ADR-ENG-004 — Explicit v2-to-19 read-only capability adapters

**Decision state:** engineering review implementation; not owner-signed Architecture Freeze.
**Dependencies:** ADR-ENG-003 (19 canonical logical owners); ADR-ENG-002 (immutable v2); current v1 synthetic interface frozen.
**Customer release:** BLOCKED. **Runtime dispatch:** DISABLED. **Professional acceptance:** NOT VERIFIED.

## Disposition of six explicit projections / five semantic collisions

| Adapter | Frozen producer | Canonical owner | Data actually transferred |
| --- | --- | --- | --- |
| A04_TO_06_DECISION_INPUT | ENG04 v2 recommendation | ENG06 Decision | scoped draft candidate look IDs, evidence digests, uncertainty, QA status |
| A04_TO_07_LOOK_SPEC_INPUT | ENG04 v2 recommendation | ENG07 Look Specification | scoped draft look spec digests and region locks, no rendered visual |
| A05_TO_06_DECISION_EVIDENCE | ENG05 v2 decision | ENG06 Decision | eligible/excluded IDs, unknowns and knowledge source digests; no independently signed approval |
| A06_TO_15_PLAN_CANDIDATE | ENG06 v2 technical plan | ENG15 Technical Planning | selected look ID, plan-template digest and missing evidence; no treatment parameter authorization |
| A04_PIXEL_TO_11_QA_EVIDENCE | ENG04 v2 scoped media | ENG11 Visual QA | real freshly recomputed pixel-mask metrics; no face/identity or source-authorization proof |
| A06_SOURCE_TO_16_REVIEW_EVIDENCE | ENG06 v2 source/SOP | ENG16 Specialist Validation | cryptographic Ed25519 SOP source-byte verification only; no professional-qualification or treatment signoff |

The six projections are *not* a runtime service-mesh implementation. One ENG04 output is split into **two different target capability inputs** without assigning it two canonical owners. The origin protocol and original engine identity must be retained on all receipts. No implicit alias or rewrite of a v1/v2 consumer may be introduced.

## Contract invariants

- Validate both complete v2 source request and source response against unchanged JSON Schema 2020-12, including exact tenant/branch/session/state version/correlation and evidence IDs. Refuse cross-tenant, mismatched correlation, invalid region and forged approval/eligibility.
- Deterministically digest canonical JSON request, response and projected data. Scope includes engine IDs, service kind, consumer correlation; fingerprint is **not a signed provenance proof**.
- Require exact declared adapter ID and source-to-canonical-owner mapping, no unknown payload keys, no customer release or downstream execution flag. The projection schema **never** permits `downstream_dispatch_authorized=true`.
- v2 data cannot be promoted into v3 by placing a source engine ID into a canonical v3 envelope. The separate v3 review contract has its own deliberately unwired 16 handoffs and G01–G10 quality gates.
- In ENG11, recompute metrics from in-memory PNG/JPEG; source-to-media handle binding and mask semantics are **not verified**. A pass only means no forbidden changed pixels under a supplied mask.
- In ENG16, an approved-content signature can prove a signed test-source record, but this **cannot** prove real reviewer qualifications or legal/salon treatment authority.
- All adapters are restricted to `LOCAL_INTEGRATION_ONLY`. In STAGING_PRIVATE / PRODUCTION they refuse to execute. No AI API purchase, no live customer media, no external endpoint.

## Before promotion: mandatory evidence

1. Obtain independently signed architecture approval for ADR-ENG-003 and ADR-ENG-004 and resolve exact source/service ownership of all 19 engines.
2. Introduce true independently deployable producers/consumers with bound mTLS+JWT principal, signed source artifact hashes, distributed JTI replay, ENG14 policy and purpose-specific consent, including revocation.
3. Write a versioned real v3 interface with consumer-driven positive and negative tests, feature flags and complete rollback. No cutover before v1/v2 backwards compatibility and a two-way migration rehearsal.
4. Obtain professional image QA benchmarks for ENG11, expert-curated evidence for ENG06, SOP-specific ENG15 plan authorization and independently verified ENG16 specialist qualifications.
5. Verify managed private deployment, SLOs, fault/recovery, 190 G01–G10 evidence slots and a separate release authority.

**Output:** a safe architecture integration milestone, **not** a production engine completion. PR remains DRAFT and no branch merge is authorized by this ADR.

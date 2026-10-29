# ABC — Roadmap after seven-engine quality gates

**Date:** 2026-10-30. **State:** planned delivery; no customer release.

| Order | Workstream | Exit requirement |
| --- | --- | --- |
| W0 | Seven-engine gates + ADR for ENG04/05/06 ownership | Owner-reviewed architecture and green governance CI |
| W1 | Managed CA, verified PostgreSQL mTLS, private API and three engines | Actual private service IDs, TLS/identity proofs, live synthetic E2E and recovery |
| W2 | ENG01/02/03/14 trusted backbone | Complete approved in-salon consultation, consent, transactional queue, policy transitions and provenance |
| W3 | Genuine ENG04/05/06 product engines | Versioned v2 Recommendation, Decision and Technical Plan ports; independent domain benchmarks |
| W4 | AI Studio visual capability | Image intake QA, transform/try-on, region lock, compare, identity preservation, visual version history, QA |
| W5 | Selected Look → Technical Plan | Evidence and feasibility gate, SOP-based procedure, materials, stop conditions, specialist validation and handoff |
| W6 | Salon Business OS | Clients, calendar, team, services, POS, inventory, marketing, reviews, permissions, multi-branch |
| W7 | BI / intelligence / automation | Reliable KPIs, search, insights, analytics, audited automations and governance |
| W8 | Controlled pilot and release | Real independent professional/security/privacy approval, rollback, monitoring, incident readiness |

## Dependency rules

- AI Studio is central and operates with specialist and client **together at one display**.
- ENG-04 recommendation consumes professional and visual evidence; ENG-05 decision evaluates risk and feasibility; ENG-06 drafts Technical Planning **only after Selected Look Lock**.
- ENG-14 policy, validated consent and qualified SOP review are mandatory before professional treatment execution or operational advice.
- Preserve AI Studio AIS-001..026 and product ABC-F01..F18 feature traceability. Do not claim all features have shipped.
- ENG04/05/06 currently use incompatible synthetic role labels. Resolve **proposed** ADR-ENG-001 with versioned v2 ports; no silent legacy v1 repurposing.
- No paid AI inference API in the present infrastructure workstream. Later model/provider decision follows representative vision-quality benchmark, privacy and cost evaluation.
- A complete engine does not imply a complete product. The product release gate is separate.
- SLOs require an approved benchmark profile and measured p50/p95/p99, capacity, error budget and target hardware; no invented thresholds.

## Immediate delivery sequence

1. Lock the evidence-governed gate registry in CI, with all seven engines IN_PROGRESS.
2. Review ENG04/05/06 architecture mapping ADR and write their typed v2 contracts.
3. Complete ENG01/02/03/14 session/evidence/policy flows and missing API coverage with synthetic tests.
4. Independently provision audited managed CA/PostgreSQL/private networks and prove live synthetic E2E; resolve distributed replay.
5. Build expert-curated knowledge, evidence-grounded recommendations, technical feasibility and professional validation benchmarks.
6. Integrate the in-salon three-column AI Studio (controls / canvas / look workspace), selected look lock and technical roadmap.
7. Finish Salon Business OS and BI, then run controlled salon pilot with independently signed release gate.

**Owner checkpoints:** Architecture owner signs ADR; SRE owns deployed topology and restore; Security owns PKI/RLS/pentest; qualified specialists own service SOP and domain evaluation; Product owns scope and SLO budget; UX owns co-present user-flow acceptance.

**Current decision:** W0 in engineering review; W1 physical infrastructure missing; W2 partial synthetic foundation; W3–W8 not complete; 0/7 engines COMPLETE.

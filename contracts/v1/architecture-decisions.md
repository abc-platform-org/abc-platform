# Phase-02 Proposed Architectural Decisions and Tradeoffs

**Proposal only; earlier ADR-001..010 are not formally human-accepted.**

| Decision proposal | Default | Why | Alternative and why deferred |
|---|---|---|---|
| Service topology | Modular bounded contexts + isolated Visual workers | one-person delivery and deterministic contracts, avoid premature microservice overhead | 19 separately deployed services: high operational cost without proven throughput need |
| Transactional data | PostgreSQL with tenant-scoped rows and transactional outbox | strong session/version and operational consistency | pure document DB: harder multi-domain transaction and audit boundaries |
| Media | immutable private object store with signed scoped URLs | asset lineage and deletion scope | public/CDN-by-default: unacceptable privacy |
| Events | at-least-once + consumer dedup with durable outbox | resilient distributed jobs without claiming exactly-once | exactly-once end-to-end: unsafe promise across services |
| Generation | provider adapter behind ENG-09 and independent ENG-11 QA | model interchange, hard validation | single prompt directly released to UI: uncontrolled edits |
| Workflow | durable recorded state transitions | recover session/async job deterministically | browser-only state and LLM chat memory: not reliable |
| Technical planning | SOP/evidence-bound draft with human validation | minimize risky fabrication | raw LLM chemical instructions: blocked |
| Authorization | verified tenant/auth context from server | cross-tenant isolation and audit | client-supplied tenant claims: rejected |
| Spec media | immutable LookSpec separate from preview bytes | reproducibility across model versions | image-only style truth: lost semantic decisions |
| API version | /v1 with schema version fields and major migrations | explicit client contract | unversioned endpoint: uncontrolled breaking change |

**Choice still open:** TypeScript vs other backend language, orchestration runner (Temporal or DB state + jobs), model provider, visual segmentation architecture, hosted infra, data residency by market, numeric visual threshold/SLO. Select only through actual technical/financial benchmark and approval, not asserted here.

# ABC Platform — Engineering Baseline

**ABC** is a salon-controlled, shared-screen, specialist-operated AI beauty consultation, visual design, professional planning, and business operating platform.

> **Important:** This repository package is a **PROPOSED ARCHITECTURE BASELINE**, not an assertion of implemented software, working AI models, passed tests, actual revenue, or production readiness. All release gates remain unverified. No customer data or secrets are included.

## Start here

1. [Project charter](docs/00-governance/PROJECT_CHARTER.md)
2. [Source & authority register](docs/00-governance/SOURCE_AND_AUTHORITY_REGISTER.md)
3. [Product requirements](docs/01-product/PRD.md) and [complete feature inventory](docs/01-product/FEATURE_INVENTORY.md)
4. [System architecture](docs/02-architecture/SYSTEM_ARCHITECTURE.md), [engine registry](docs/02-architecture/ENGINE_REGISTRY.md), and [contract standards](docs/02-architecture/ENGINE_CONTRACT_STANDARD.md)
5. [AI Studio specification](docs/03-ai-studio/AI_STUDIO_SPEC.md), [questioning](docs/03-ai-studio/ADAPTIVE_QUESTIONING.md), [visual pipeline](docs/03-ai-studio/VISUAL_PIPELINE.md), [technical planning](docs/03-ai-studio/TECHNICAL_PLANNING.md)
6. [16-phase master roadmap](docs/05-delivery/MASTER_ROADMAP_16_PHASES.md), [work breakdown](docs/05-delivery/WORK_BREAKDOWN.md), [traceability](docs/05-delivery/REQUIREMENTS_TRACEABILITY.md)
7. [Phase 00 runbook](docs/05-delivery/PHASE_00_RUNBOOK.md), [release gates](docs/05-delivery/RELEASE_GATES.md), [QA](docs/06-quality/TEST_STRATEGY.md), [security](docs/07-security/SECURITY_PRIVACY.md)
8. [Repository and collaboration protocol](docs/08-operations/REPOSITORY_WORKFLOW.md)

## Product invariant

**Specialist + client, physically together, one shared salon screen.** The specialist controls the session; the client participates in choice. The customer does not use a standalone at-home consultation application or receive previews automatically through a remote delivery channel. Specialist-only technical details must be access-controlled and protected from inadvertent exposure on the shared screen.

## Milestone order

`Source recovery → product/contract freeze → platform foundation → adaptive consultation → evidence/decision → visual pipeline → visual revision → technical planning → business operations → full integration → expert pilot → MVP → V2 → V3`.

The *AI Studio critical path* is prioritized over optional business-platform expansion; the full product scope is retained in the feature inventory.

## Change control

Architecture proposals require an ADR, linked requirement IDs, tests, review, and PR. No direct unreviewed writes to `main`; no automatic production deployment. See [engineering rules](docs/08-operations/REPOSITORY_WORKFLOW.md).

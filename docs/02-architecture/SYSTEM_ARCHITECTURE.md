# System Architecture — ABC-ARCH-001

Status `PROPOSED_NOT_FROZEN`

## C4 — Context

Salon specialist and client share one screen; reception and management use role-protected application views. Third-party providers can supply generation, identity, payments or messaging after approved integrations; their behavior is never assumed to exist.

## Container model

```text
Shared Screen / Specialist UI / Salon OS
    ↓ (HTTPS, auth context)
API Gateway / Backend for Frontend
    ↓ (validated tenant, user, consent)
Application / Domain Runtime (modular, transactional)
    ├── Durable workflow + events + job correlation
    ├── Consultation / Evidence / Knowledge / Decision / Look
    ├── Feasibility / SOP Planning / Human Validation / Handoff
    └── Salon CRM / Calendar / Staff / Services / POS / Inventory / Analytics
    ↓ queued command with idempotency key
AI Processing Workers
    ├── image quality & segmentation
    ├── controlled generation adapter(s)
    ├── deterministic compositing
    └── visual QA + QA result storage
    ↓
PostgreSQL (transactional); object store (encrypted assets); event/outbox; search index
    ↑
Observability / Audit / Evaluation / Safety / Secrets / Tenant isolation
```

## Deployment strategy

Recommend TypeScript/React UI; modular backend with explicit domain modules; Python AI/CV workers where needed; PostgreSQL; object storage; durable workflow engine (candidate Temporal, to be validated), queue, OpenTelemetry, CI/CD. **Technology selection remains an ADR**; do not invent benchmarked capacity/cost.

## Cross-domain rules

1. Orchestrator owns workflow transitions; no LLM direct database writes or payments.
2. Tenant ID is derived from verified authorization context, not trusted from a request body.
3. One immutable original image asset, derived artifacts separate; selective revocation and retention.
4. `LookSpec` expresses the desired style independent of Preview image.
5. `Visual QA PASS` is not `Feasibility PASS`; client selection is not professional approval.
6. Event-driven operations use outbox/at-least-once handling and idempotent consumers.
7. No undeclared synchronous fan-out to heavy visual operations; async jobs with callbacks/status.
8. Each engine bounded context has contracts, monitoring, test suites, version.
9. Infrastructure services (Auth, storage, search) are not confused with AI reasoning engines.
10. Advanced services are activated by per-service validated `ServicePack` gates.

## Failure scenarios

- Queue retry: correlate request ID; stale or superseded results MUST NOT overwrite selected look.
- Model unavailable: explicit unavailable status; recoverable retry or text-only path.
- Consent withdrawn: block further processing, revoke access/delete as required by policy.
- Professional validation outdated: revoke or require new review on material input changes.
- Business operation failed: return structured failure, compensate where appropriate; do not claim success.
- Unauthorized cross-tenant request: deny in query and asset access layers; audit.

## Feature-to-layer allocation

See `docs/01-product/FEATURE_INVENTORY.md` and `docs/05-delivery/REQUIREMENTS_TRACEABILITY.md`.

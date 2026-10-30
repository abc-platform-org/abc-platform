# ABC — ENG01/02/03/14 Security Backbone for v2 Engine Integration

**Date:** 2026-10-30. **Environment:** draft, synthetic-only; no deployed live service, production credentials, external approvals, or paid inference API.

## Responsibility and trust boundaries

| Subsystem | Existing tested authority | Required before v2 live dispatch | Forbidden shortcut |
| --- | --- | --- | --- |
| ENG-01 orchestration | OIDC specialist/session scope + PostgreSQL state version, 20-state/102-edge canonical machine; narrow CREATED→PAUSED S0 gate | Actual authenticated service gateway, versioned v2 state transition policy and atomic look lock | Browser-supplied tenant, role, guard/pass flag or UI click as authority |
| ENG-02 consultation | In-person synthetic questionnaire; PostgreSQL session + consent ledger and purpose gate | Real client-specific CAPTURE/AI_PROCESSING/INTERNAL_HANDOFF proof, revoke/expiry and verified authorized specialist | "consent=true" boolean or inferred preference from a rendered photo |
| ENG-03 evidence | Durable claim/lease/ACK + fenced source event and immutable evidence ledger | Per-consumer real managed workload certificate and delivery/rolling-restart tests, shared replay controls | Generic shared DB password, external evidence inserted from a model, skipping lease ownership |
| ENG-14 policy | 102 transition decisions, 101 blocked; specialist risk candidate classifier blocks real service | Independently reviewed S1-S3 SOP + qualified specialist, ENG05 decision and ENG06 plan/handoff policy with verified consent | Auto-approve because an LLM generated a plausible answer |

## Hard dispatch invariants for new v2 path

1. **Never route v1 to v2 by name alone.** `abc.internal.engine.synthetic.v1` remains the legacy fixture contract, while v2 is `abc.internal.engine.v2.draft`. Explicit version negotiation and separately audited cutover are mandatory.
2. A payload's `tenant_id`, `branch_id`, `session_id`, `state_version` and `consumer_id` are **untrusted correlation claims**. They must match authenticated issuer-bound workload identity, authorized specialist membership and SQL RLS; exact header matching in JSON schemas is necessary but insufficient.
3. Source evidence must come from ENG-03 immutable ledger with digest, session version and claimant authority. ENG-04 can produce only draft looks, no approved customer transformations.
4. ENG-05 must reject unreviewed knowledge, ENG-14 hard BLOCK, missing critical evidence and candidate/evidence substitution. It never asserts service approval.
5. ENG-06 requires selected-look lock, same session and state version, ENG-05 decision provenance, verified-consent digest and approved specialist SOP. Draft plan remains review-only; operational handoff is forbidden until separately signed professional/ENG-14 policy gates and durable orchestrator transition.
6. Every service uses independent private identity and envelope version. Replay, timeout, re-try, idempotency and DLQ require integration and real infrastructure tests.

## Current code evidence

- `scripts/validate_abc_v2_architecture.py` pins unchanged v1 and canonical state-machine Git blob digests and checks ENG01/02/03/14 fail-closed source boundaries, all 3 v2 owner roles, and offline UI CSP.
- `test_v2_backbone_policy_assurance.py` verifies 101 unimplemented ENG-14 canonical edges remain blocked and 9 candidate salon service profiles cannot authorize execution.
- `test_engine_v2_contracts.py` validates strict v2 request/response/error schema, no version downgrade, no cross-tenant/revision/correlation mixing, ENG04 reference isolation, ENG05 ENG14/knowledge hard blocks, ENG06 look lock and consent.
- Disposable CI certificate integration with PostgreSQL 16, independent engine processes and private API TLS still comes from prior stacked PR #41/#42.

## What is not complete

External CA/JWKS and PostgreSQL physical client-cert enrollment; live private deployment of API+ENG04/05/06; server-side v2 contract-version dispatch with a real authenticated identity; true service-specific consent verification and specialist SOP signoff; real image/recommendation/planning engines; production resilience, restore and tenant adversarial penetration tests. This workstream does not issue certificates, acquire paid AI API keys, approve procedures or change the protected main branch.

**Gate:** 0/7 engine COMPLETE, live rollout BLOCKED until real operator evidence and independent signed G01–G10 checks.

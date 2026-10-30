# ABC — ENG-04/05/06 v2 Executable Foundations

**Date:** 2026-10-30 | **Status:** LOCAL CONTROLLED ENGINE IMPLEMENTATION; NOT PRODUCT READY.  
**GitHub:** stacked draft PR #47 → PR #46. **No paid AI API**, **no real customer images**, no unapproved cloud deployment.

## Engineering deliverables

| Engine | Working implementation | Positive bounded evidence | Hard limitations |
| --- | --- | --- | --- |
| ENG-04 Recommendation | `eng04_recommendation_v2.py`: deterministic traceable controlled HAIR_COLOR look specifications, SHA256 of scoped source, stable UUIDv5, region lock, evidence lineage | Repeated identical source state returns identical candidate; changing tenant or evidence fingerprint changes look identity; UNKNOWN/unsupported inputs block | No image understanding, image generation, reference interpretation, identity preservation benchmark or true quality evaluation. `visual_qa_status=NOT_VERIFIED` |
| ENG-05 Decision | `eng05_decision_v2.py`: explainable hard filter, ENG14 policy BLOCK, missing critical data and knowledge-source review checks; requires explicitly injected independent knowledge/policy gate to list reviewable candidates | Rejects ambiguous, missing or unverified source. Controlled test verifier can produce `SPECIALIST_REVIEW_REQUIRED` with authorization flags false | No independent qualified specialist knowledge catalog or real SOP; review flag alone is not proof of knowledge authority; no execution approval |
| ENG-06 Technical Planning | `eng06_technical_plan_v2.py`: intake completeness, SOP/consent/lock preconditions, fail-closed external evidence verification, nonprocedural draft template | Missing evidence returns `AWAITING_SPECIALIST_INPUT`; explicit controlled test verifier can create a DRAFT only with preconditions supplied | No real verified professional approval, chemical formula, tools/material quantities, treatment steps/timings or operational handoff |

The external verification interfaces are dependency-injection boundaries, **not proof that real issuer-signed professional approvals exist**. They must be backed by external, reviewed trusted identity and provenance before any production promotion. The current standalone process worker intentionally supplies neither verifier: therefore ENG-05 remains BLOCKED and ENG-06 remains AWAITING_SPECIALIST_INPUT in its default offline execution.

## Runtime isolation and evidence

`engine_v2_runtime.execute(message,engine=...)` validates versioned v2 input and response schemas, including correlation, tenant, branch, session and expected state version. It only runs when `ABC_ENV=LOCAL_INTEGRATION_ONLY`. Independent single-shot process invocation:

```bash
# Inside runtime/phase04 with required dependencies installed:
ABC_ENV=LOCAL_INTEGRATION_ONLY python -m abc_foundation.engine_v2_worker ENG-04 < synthetic-request.json
ABC_ENV=LOCAL_INTEGRATION_ONLY python -m abc_foundation.engine_v2_worker ENG-05 < synthetic-decision-request.json
ABC_ENV=LOCAL_INTEGRATION_ONLY python -m abc_foundation.engine_v2_worker ENG-06 < synthetic-plan-request.json
```

Each worker accepts **one bounded JSON message up to 128 KiB**, validates the exact engine ID, protocol `abc.internal.engine.v2.draft` and response schema, and terminates. Denied requests produce a sanitized fixed error; no payload, secret, evidence detail, customer media or traceback leaks in the returned JSON. This worker is **not** a private cloud/mTLS microservice, production release or valid external authorization service.

`test_three_process_v2_bounded_e2e.py` starts three separate Python OS processes and transmits a controlled synthetic ENG04→ENG05→ENG06 look/decision chain. This proves local process operation and contract boundaries; it does not establish external independent deployment. No v1 migration or shared runtime state is performed.

## Contract and architectural integrity

- Exact v1 internal engine protocol remains frozen under `isolated_engine_service.py`. Its semantics (ENG04 synthetic analysis / ENG05 knowledge / ENG06 decision) are not silently repurposed. No new v2 call can downgrade to v1.
- ADR-ENG-002 fixes new target roles (ENG04 recommendation, ENG05 decision, ENG06 technical planning); the draft ports remain strict JSON Schema Draft 2020-12.
- ENG04 never claims CV/AI visual success and never edits any actual identity pixel. It emits only source-bound candidate specs with a `NOT_VERIFIED` feasibility label.
- ENG05 denies any ENG14 BLOCK, any reported critical unknown, unreviewed source, and absence of external scoped policy/knowledge verifier.
- ENG06 never approves a technical intervention, cannot pass operational handoff and always marks professional validation `NOT_VERIFIED`. Its drafted template is nonoperational and has stop conditions; no chemical parameters.
- Existing ENG01/02/03/14 governance remains deny-first; no session state mutation or real salon service can occur through the v2 runner.

## Next domain engineering requirements (not silently implied by CI)

1. Introduce secure authenticated ENG03 evidence handles and a real ENG04 image-understanding/vision backend with identity/region/reference preservation. Build a representative expert-scored dataset for VQ01..VQ07 before selecting a paid API or self-hosted model.
2. ENG05: professionally curated versioned knowledge, external provenance signature verification, contradiction constraints and robust decision calibration. Add negative cross-service replay and adversarial source-injection tests.
3. ENG06: consent revocation, qualified SOP catalog per service and immutable signed specialist validation, plus coherent technical parameters, constraints, checkpoints, recovery and safe operational handoff under ENG14. No template can bypass professional review.
4. Complete operator-managed service PKI/JWKS, private PostgreSQL clientcert authentication, dedicated services for all engines, distributed replay ledger, physical failover and operational SLO test runs.
5. Connect the offline three-column AI Studio after real media identity/region QA and consent. Use synthetic no-client fixtures meanwhile; do not claim the current CSS render is a visual model.
6. Obtain **all G01–G10 engine completion** and independent product security/professional release approvals.

**Completion claims:** no ENG04/05/06 engine meets the professional, runtime deployment or external-issuer gates. `0/7 COMPLETE`; product release remains BLOCKED even if the CI suite is green.

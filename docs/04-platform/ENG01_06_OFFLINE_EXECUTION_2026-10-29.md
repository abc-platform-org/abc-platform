# ABC — ENG01 to ENG06 Offline Runtime Evidence and Release Boundaries
Date: 2026-10-29. Draft PR #31 stacked on ENG01 PR #29, stacked on P04 PR #23. Main and frozen Phase02 contracts unchanged.

## Architecture decision
This is an offline, source-scoped modular vertical slice. These are not independent deployed microservices, trained domain experts or real customer workflows. Real model APIs and Render paid resources remain DEFERRED until cost-capped demo readiness. No media/client data is allowed.

## ENG01 — atomic command ledger
Migration 0007 adds a scoped command receipt table with FORCE RLS. Dedicated ENG01PostgresCommandStore executes the strict internal pause command in ONE transaction: authoritative OIDC principal membership, tenant/branch/assigned specialist RLS, locked session, full canonical command hash, exact-key receipt replay, compare-and-swap state update, state audit and command receipt insert. Reusing same command ID with altered correlation, deadline, timestamp or payload yields 409; worker cannot read command receipts. Gateway rejects engine spoofing and user-provided policy approval. Previous ENG01 gateway had incomplete fingerprint binding; this closes that specific bug.

Only CREATED to PAUSED is executable in this new gateway. The canonical other 101 consultation transitions remain inspectable but not enabled. Full service-to-service IAM, ENG14 policy, consent, regulated service actions, transactional multi-engine events, distributed telemetry and external cloud runtime remain unimplemented. The implementation still uses a common abc_app database role, not distinct production engine workload identity.

## ENG02 — persistent synthetic adaptive consultation
Separate ConsultationEngine with explicitly labelled synthetic-only versioned hair question profile, SQLite durable answer ledger and idempotency receipt; upstream specialist/session authentication; deterministic safety-first question ordering; bounded vocabulary; repeat and conflicting-answer rejection; stop on unknown critical fact or reported sensitivity requiring specialist. Restart and concurrent request tests verify behavior. The registry is not approved for real clients. ENG02 writes no canonical PostgreSQL ANSWER_RECORDED outbox event, because local SQLite and Postgres cannot be committed atomically in this current slice.

## ENG03 — evidence quality
SyntheticEvidenceEngine converts only authoritative recorded answers into provenance-bound USER_REPORTED entries, marks unasked/unknown answers UNKNOWN and NOT_AVAILABLE, and refuses media/photos with 501. It does not upgrade specialist-entered user reports into physical observations. Real image QA, privacy/retention and client-origin verified consent are absent.

## ENG04 — Beauty analysis
SyntheticBeautyAnalysis enforces exact session, service, attribute and source-evidence consistency; outputs structured Phase02 analysis data and unknowns with no invented probabilities, diagnostics or observed chemical condition. Reported sensitivity flags trigger professional review. No actual AI model or visual perception has run.

## ENG05 — knowledge
SyntheticKnowledgeEngine fails closed with SOURCE_UNVERIFIED unless a deliberately synthetic two-option fixture of a single exact version is provided. Test-only source markers are NOT professional signoff; there is no released ontology or expert-approved source pack.

## ENG06 — decision
SyntheticDecisionEngine checks source and analysis IDs, missing safety-critical facts, reported sensitivity and test-only candidate applicability; excludes disallowed alternatives and never invents a third choice. Any passing fixture candidate is marked CONDITIONALLY_PASSED and PROFESSIONAL_CHECK_REQUIRED. It is not a real beauty recommendation or a physical feasibility approval.

## Reproducible test
From runtime/phase04, with dependencies installed, run:
ABC_ENV=LOCAL_INTEGRATION_ONLY ABC_DEMO_SYNTHETIC=yes python demo_offline_engines.py

This prints a sanitized synthetic-only JSON summary: 4 questions, no paid API calls, no real customers, 1 conditional fixture candidate and 1 excluded fixture alternative. The CI job runs this demonstration and checks its output. The same workflow executes disposable PostgreSQL16 migration and real command-concurrency tests and Python unit tests. Draft Phase02 JSON Schema 2020-12 validates question, consultation profile, evidence, analysis, knowledge and recommendation artifacts. The source of truth is the frozen contracts/v1 directory.

## Explicit per-engine maturity

| Engine | Executable offline slice | Mandatory next scope |
| --- | --- | --- |
| ENG01 | Atomic scoped pause command and durable full-input receipt | Other 101 transitions; true independent service identity, ENG14, consent and worker orchestration |
| ENG02 | Durable synthetic adaptive questioning and persistence | Reviewed real service profiles, Postgres+outbox atomic answer history, human override |
| ENG03 | Non-media provenance and unknown classification | Real image quality, scoped consent capture and privacy lifecycle |
| ENG04 | Source-bound structured reported-fact analysis | Trained/performance-tested multimodal analysis and expert evaluation |
| ENG05 | Versioned synthetic test source and unverified source denial | Reviewed knowledge packs, service ontology and source conflict governance |
| ENG06 | Source-bound synthetic hard-filter decisions | Real service capability/SOP filters, qualified human validation, true recommendations |

## Governance / risk
All modules remain partial implementations; engine deployments = 0, releases = 0, real customer data = 0, actual AI API invocations = 0. P04 = IN_PROGRESS. ENG01 authenticated per-engine workload identities and policy-driven state transitions remain the immediate critical path. ENG02 real service question profiles and transactional event coupling are next, followed by ENG03 actual input validation and separately governed ENG04/05 domain work, then ENG06 professional decision gating. No purchase or automatic staging deployment is authorized.

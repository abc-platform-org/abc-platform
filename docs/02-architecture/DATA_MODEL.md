# Domain Data Model and Invariants — ABC-DATA-001

## Bounded contexts

- `Organization`: Tenant, Salon, Branch, SalonConfigVersion.
- `Identity`: User, Membership, Role, Permission, SpecialistSkill.
- `Client`: ClientProfile, Consent, RetentionPolicy, optional ServiceHistory.
- `Consultation`: Session, Request, Question, Answer, SessionEvent.
- `Evidence`: ImageAsset, ReferenceAsset, EvidenceRecord, AttributeObservation.
- `Decision`: AnalysisResult, Candidate, RecommendationSet, LookSpec, LookVersion, SelectedLook.
- `Visual`: SegmentationMask, VisualJob, CandidatePreview, CompositedPreview, QAReport.
- `Professional`: FeasibilityAssessment, SOPVersion, ProcedureStep, TechnicalPlan, SpecialistValidation.
- `Operations`: Appointment, ServiceCatalogEntry, WorkOrder, Invoice, Payment, StockLedger, Campaign, Review.
- `Governance`: AuditEvent, PolicyDecision, ExperimentVersion, ReleaseGateEvidence.

## Canonical relationship graph

```text
Tenant → Branch → {Specialist, Client, Appointment, Session}
Session → {Consent, Request, Question/Answer, Evidence, RecommendationSet}
RecommendationSet → LookSpec → LookVersion
LookVersion → {Preview, VisualQA, Feasibility, TechnicalPlan}
TechnicalPlan → SpecialistValidation → Handoff → WorkOrder/Appointment/POS
```

## Required provenance model

Each fact: `{key, value, evidence_class, source_asset_or_actor_id, observed_at, version, service_scope}`. Evidence classes: `KNOWN`, `OBSERVED`, `USER_REPORTED`, `INFERRED`, `UNKNOWN`, `REQUIRES_PROFESSIONAL_CHECK`. Never upgrade an inference into an observation without new evidence.

## Invariants

1. All entities inherit trusted `tenant_id`; cross-tenant references rejected with database policy plus application checks.
2. Session `current_state_version` uses optimistic concurrency; background stale results cannot overwrite current state.
3. Original image is immutable; derived versions and masks are separately stored and revocable.
4. SelectedLookVersion refers to a QA-aware immutable LookVersion; validation binds to exact look, SOP and evidence versions.
5. Changes to service parameters, protocol, critical evidence or selected look invalidate downstream validation.
6. Each operation has correlation ID and auditable actor identity; audit does not include unnecessary personal image bytes.
7. Where client consent is withdrawn, asset access and future jobs must be cancelled/revoked as required by actual policy.
8. Business metrics derive from transactional/operational facts with definition, time window, currency, timezone and provenance.

## Suggested transactional design

PostgreSQL for strongly consistent records, with `tenant_id` indexed or row-level secured; outbox table within same transaction as domain mutations. Object store for pictures with scoped short-lived access, encryption and lifecycle rules. Search must enforce permissions prior to ranking results. Do not persist biometric inferences beyond approved scope.

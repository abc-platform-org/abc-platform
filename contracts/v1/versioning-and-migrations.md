# Phase-02 Contract Versioning / Migration Governance

- Initial draft identifiers: `1.0.0` documents; Gate-02 review before status `CONTRACT_APPROVED`.
- JSON Schema `$id` is stable for a particular **major** namespace. Schemas may be backward-compatible minor additions only when consumers accept new optional fields safely; never silently change required fields, defaults, enum meaning, transition guards or event payload semantics.
- Breaking change: major version, old and new publishers/consumers dual-read period, data migration and rollback strategy, explicit architecture ADR and contract regression.
- Historical source `ABC-DOC-014` OUT-01..OUT-17 remain untouched. New technical plan artifacts use independent `TechnicalPlanDraft` and `SpecialistValidation` contract IDs; no invented OUT-18 as historic fact.
- Persist versions for `QuestionProfile`, `ServicePack`, `SOPVersion`, `LookSpec`, `VisualModel`, `MaskPolicy`, `VisualQAProfile`, `PolicyVersion`, `EventSchemaVersion` and `EngineContractVersion`.
- A LookVersion mutation must create a **new version**, never replace previous accepted variant. Specialist validation binds exact `look_version_id`, `sop_version_id`, `evidence_fingerprint`, `technical_plan_id` and `plan_version`.
- Any material dependency changed triggers `REVIEW_REQUIRED` or `INVALIDATED`; no previous approval remains executable.
- Event replay and audit require original semantic version and schema fingerprints. Unknown future event version routes to DLQ rather than unsafe reinterpretation.
- All migration scripts and fixtures must be approved/tested before production; Phase-02 designs contracts only.

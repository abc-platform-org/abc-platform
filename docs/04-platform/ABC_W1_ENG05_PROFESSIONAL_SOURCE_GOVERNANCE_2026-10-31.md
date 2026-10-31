# ABC W1 — ENG-05 Professional Source Governance v1 (review-only)

**Date:** 2026-10-31  
**Status:** DRAFT ENGINEERING CANDIDATE — no professional issuer connected; no production advice; no ENG-06 release  
**Stack:** Draft PR #68 (independent ENG05 physical review Worker) → this stacked proposal. Protected `main` unchanged.

## Mandate and trust model

ENG-05 owns professional knowledge, provenance and ontology; ENG-06 owns *separate, explainable decision making*. The existing ENG05 synthetic Worker continues returning `grounded_facts=[]`, `retrieval_sources=[]` and `unknowns=["SOURCE_UNVERIFIED"]`. **This PR never connects unqualified candidate material to that Worker or to ENG06.** The ENG05 knowledge governance dossier is nonexecuting and cannot confer customer or clinical/service authority.

### Frozen versioned contracts

- `governance/abc_eng05_professional_source.v1.review.schema.json` and `abc.eng05.professional-source.v1.review`: versioned source identity, publisher and independent submitter, jurisdiction, publication locator, content SHA256, licence reference, scope, publication/expiry timestamps, explicitly evidence-linked claims with per-claim strength, uncertainty and safety-critical designation.
- `governance/abc_eng05_specialist_attestation.v1.review.schema.json` and `abc.eng05.specialist-review.v1.review`: cryptographically detached Ed25519 signature binding the **exact immutable source hash**, reviewer's credential ID, all claim IDs, specialist identity, decision, issue date and conflict-of-interest declaration.
- These contracts validate **identity and structure**; they do **not** establish external factual accuracy, a professional licence, rights to redistribute copyrighted source material, permitted jurisdiction, consent or suitability for an individual client.

### Qualification and specialist gate

- Trust anchors must come from an independently issued, explicitly trusted, scope-and-validity-bounded specialist credential registry. The candidate's self-declared reviewer/publisher metadata cannot serve as an authority. The source submitter or publisher cannot approve their own material. Signature, reviewer scope, issue time, expiry, independent public key and complete claim coverage are independently checked.
- A normal candidate requires at least **one** verified independent specialist review; any safety-critical claim requires **two distinct** signed independent specialist reviews. A rejection or revision request blocks qualification even if another reviewer approves; duplicate reviewer/replay is denied.
- All source versions are evaluated. A new version does not silently supersede earlier conflicting evidence. Candidate claims with incompatible assertions for the same service/topic/applicability are tagged **UNRESOLVED**, and safety-critical conflicts are separately elevated. No automatic weighting or majority vote can produce salon advice.
- Expired, synthetic, unverified, incomplete, conflicting or uncertain evidence generates explicit `unknowns`, preserving explainable reasons. The resulting `abc.eng05.knowledge-dossier.v1.review` always keeps `professionally_released_facts=[]`, `eng05_to_eng06_dispatch_authorized=false` and `customer_release_approved=false`.
- For CI only, disposable Ed25519 keys are generated in test memory to validate gate behavior. **A synthetic test signature is not a credential from a real licencing authority**. No actual professional sources, verified licensing registries, professional signatures, privacy approvals or paid AI APIs are present.

## Append-only PostgreSQL and lifecycle boundary

Migration **0026** creates `eng05_professional_source_candidates`, `eng05_professional_review_attestations` and `eng05_professional_conflict_dossiers`. All three have ENABLE+FORCE RLS, no DML grants to engine/API roles, and deny UPDATE/DELETE through an immutable-snapshot trigger. Mutated content is represented by a new source version and new SHA, never rewriting an attested version.

Database constraints **cannot be changed by a CI reviewer into authorization**: source `trust_state=UNVERIFIED_EXTERNAL_AUTHORITY`, specialist `verification_state=AWAITING_EXTERNAL_CREDENTIAL_ISSUER`, all professional/ENG06 release flags fixed false. The existing 25 Claim/Lease/ACK and legacy review contracts are unchanged; migration **0026** is checksum-locked and reversible through isolated sandbox restoration, not an in-place rewrite.

## Automated acceptance checks

- Positive *synthetic cryptographic* test: valid independent one-review and two-review critical claims produce only `REVIEWED_NON_EXECUTABLE` dossiers.
- Negative review cases: missing trust anchor, tampered source, bad signature, duplicate signer, revoked/out-of-scope/expired credential, self-approval by publisher/submitter, rejection despite another positive review, missing claim coverage.
- Negative epistemic cases: source expiry, simulated source disqualification, insufficient/uncertain evidence, divergent claims and safety-critical conflict, duplicate source version and malformed contract.
- PostgreSQL check: append-only source and review snapshots, exact SHA for bytes, forced RLS, direct ENG05 worker SELECT denied, attempt to set customer/professional release to true rejected; all source material remains candidate-only.
- Regression: original ENG03→ENG04→ENG05 mTLS/JWT path, independent ENG05 Claim/ACK/DLQ, blocked ENG05→ENG06 outbox, existing 19-engine contracts, all 26 migrations and private W1 release-denial gates remain tested.

## Formal non-acceptance

This code adds a **trust evaluation gate**, not real licenced professional content. It does not verify publisher legal rights, source reliability, real practitioners' licence status or external attestations. Those require independent specialist and compliance operators, genuine evidence records and authorized private infrastructure. ADR-ENG-003/004 remain unsigned, private W1 runtime unprovisioned, customer processing off, and all engine G01–G10 acceptance slots OPEN.

**Next after exact-head CI:** establish an externally managed reviewer credential issuer and a curated source-ingestion process with documented licence/scope/expiry; test a real signed, legally redistributable source with independent professional reviewer(s) and specialist conflict resolution. Only after external approval and source acceptance can a separately reviewed ENG05 knowledge consumer be specified. No auto-release of ENG06.
